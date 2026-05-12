#!/usr/bin/env python3
"""
Run BioASQ Synergy RAG pipeline (Round-aware, snapshot-safe)

This script:
1. Loads official BioASQ testset JSON
2. Streams local PubMed corpus (JSONL) — OOM SAFE
3. Builds BM25 index efficiently (Elasticsearch tuned)
4. Runs RAG pipeline
5. Outputs BioASQ-formatted results
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Iterator

import yaml
from tqdm import tqdm

from src.pipeline.med_rag import MedicalRAGPipeline
from src.core.synergy_formatter import SnippetExtractor

# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("bioasq-pipeline")

# ---------------------------------------------------------------------
# Load BioASQ testset
# ---------------------------------------------------------------------
def load_bioasq_testset(testset_path: Path) -> List[Dict[str, Any]]:
    logger.info(f"Loading BioASQ testset from {testset_path}")
    with open(testset_path, "r") as f:
        data = json.load(f)

    questions = data.get("questions", [])
    logger.info(f"Loaded {len(questions)} BioASQ questions")
    return questions

# ---------------------------------------------------------------------
# Stream PubMed corpus (JSONL) — OOM SAFE
# ---------------------------------------------------------------------
def stream_pubmed_corpus(jsonl_path: Path) -> Iterator[Dict[str, Any]]:
    logger.info(f"Streaming PubMed corpus from {jsonl_path}")

    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip():
                continue

            doc = json.loads(line)

            pmid = doc.get("doc_id") or doc.get("pmid")
            abstract = doc.get("abstract", "")

            if not pmid or not abstract:
                continue

            title = doc.get("title", "")

            yield {
                "doc_id": str(pmid),
                "title": title,
                "abstract": abstract,
                "text": f"{title}\n\n{abstract}".strip(),
                "metadata": {"pmid": pmid}
            }

# ---------------------------------------------------------------------
# High-performance incremental indexing (FIXED)
# ---------------------------------------------------------------------
def index_pubmed_stream(
    pipeline: MedicalRAGPipeline,
    corpus_stream: Iterator[Dict[str, Any]],
    batch_size: int = 5_000,   # Reduced for more frequent progress updates
):
    import sys
    import time
    
    bm25 = pipeline.bm25_retriever
    es = bm25.es if bm25 is not None else None

    logger.info("Preparing Elasticsearch for fast bulk indexing")

    if es is not None:
        try:
            bm25.reset_index()
        except Exception:
            pass

        # Disable refresh & replicas (CRITICAL)
        es.indices.put_settings(
            index=bm25.index_name,
            body={
                "index": {
                    "refresh_interval": "-1",
                    "number_of_replicas": 0
                }
            }
        )
    else:
        logger.warning("Elasticsearch not available; skipping ES tuning for bulk indexing")

    logger.info("Indexing PubMed documents (streaming + bulk mode)")
    batch = []
    total = 0

    for doc in tqdm(corpus_stream, desc="Indexing documents", unit=" docs", unit_scale=True, mininterval=1.0, file=sys.stderr):
        batch.append(doc)

        if len(batch) >= batch_size:
            logger.info(f"Processing batch: {total} -> {total + len(batch)} documents")
            sys.stderr.write(f"[STDERR] About to call index_documents with {len(batch)} docs\n")
            sys.stderr.flush()
            start = time.time()
            # Reduced batch + disabled fallback BM25 indexing during ingestion
            pipeline.index_documents(batch, reset_index=False, index_fallback=False)
            elapsed = time.time() - start
            total += len(batch)
            logger.info(f"Completed batch in {elapsed:.1f}s. Total indexed: {total}")
            sys.stderr.write(f"[STDERR] Batch complete in {elapsed:.1f}s\n")
            sys.stderr.flush()
            batch.clear()

    if batch:
        logger.info(f"Processing final batch: {total} -> {total + len(batch)} documents")
        pipeline.index_documents(batch, reset_index=False, index_fallback=False)
        total += len(batch)
        logger.info(f"Completed final batch. Total indexed: {total}")

    logger.info(f"Finished indexing {total} PubMed documents")

    # Restore ES settings
    if es is not None:
        logger.info("Restoring Elasticsearch refresh & replicas")
        es.indices.put_settings(
            index=bm25.index_name,
            body={
                "index": {
                    "refresh_interval": "1s",
                    "number_of_replicas": 1
                }
            }
        )
        es.indices.refresh(index=bm25.index_name)

# ---------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------
def run_pipeline(
    questions: List[Dict[str, Any]],
    pubmed_path: Path,
    config_path: Path,
) -> List[Dict[str, Any]]:

    logger.info("Loading pipeline configuration")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    pipeline = MedicalRAGPipeline(config)

    # -----------------------------------------------------------------
    # INDEXING (FAST + SAFE)
    # -----------------------------------------------------------------
    corpus_stream = stream_pubmed_corpus(pubmed_path)
    index_pubmed_stream(pipeline, corpus_stream)

    # -----------------------------------------------------------------
    # RAG INFERENCE
    # -----------------------------------------------------------------
    logger.info("Running RAG inference")
    results = []

    for idx, q in enumerate(questions, 1):
        query = q["body"]
        qid = q["id"]
        qtype = q.get("type")

        if idx % 10 == 0:
            logger.info(f"Processing question {idx}/{len(questions)}")

        output = pipeline.process_query(query, question_type=qtype)
        
        # Get documents with full details
        final_docs = output.get("final_documents", [])
        
        # Extract snippets using the Synergy formatter
        # Limit to top 10 documents as per BioASQ regulations
        top_docs = final_docs[:10]
        
        # Limit to top 10 documents as per BioASQ regulations
        top_docs = final_docs[:10]
        
        snippets = SnippetExtractor.extract_snippets(
            query=query,
            documents=top_docs,
            max_snippets=10
        )

        results.append({
            "id": qid,
            "body": query,
            "type": qtype,
            "answer_ready": q.get("answerReady", False),
            "answer": output.get("answer"),
            "documents": [
                d["doc_id"] for d in top_docs
            ],
            "snippets": snippets
        })

    return results

# ---------------------------------------------------------------------
# Save results (BioASQ submission format)
# ---------------------------------------------------------------------
def save_results(results: List[Dict[str, Any]], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    submission = {"questions": []}

    for r in results:
        answer = r.get("answer", "")
        qtype = r.get("type", "")
        answer_ready = r.get("answer_ready", False)
        
        question_entry = {
            "id": r["id"],
            "body": r.get("body", ""),
            "type": qtype,
            "documents": r["documents"],
            "snippets": r["snippets"]
        }
        
        # Generate fallback answer if answer is empty
        if not answer:
            # Generate a minimal valid answer based on question type
            if qtype == "yesno":
                answer = "Unable to determine from available evidence"
            elif qtype == "factoid":
                answer = "Information not available"
            elif qtype == "list":
                answer = "No specific items identified"
            else:  # summary
                answer = "Insufficient evidence to provide a comprehensive answer"
            answer_ready = True  # Force answer generation
        
# Limit ideal answer to 200 words as per BioASQ regulations
        words = answer.split()
        if len(words) > 200:
            ideal_answer = " ".join(words[:200])
        else:
            ideal_answer = answer
        
        if qtype == "yesno":
            # BioASQ: must be "yes" or "no" (no empty string allowed)
            answer_lower = answer.lower()
            if "yes" in answer_lower[:50] and "no" not in answer_lower[:50]:
                exact_ans = "yes"
            elif "no" in answer_lower[:50]:
                exact_ans = "no"
            else:
                # Default: if "unable", "insufficient", or "not available", return "no"
                if any(word in answer_lower for word in ["unable", "insufficient", "not available", "unknown"]):
                    exact_ans = "no"
                else:
                    exact_ans = "yes"
            question_entry["exact_answer"] = exact_ans
            question_entry["ideal_answer"] = ideal_answer
            
        elif qtype == "factoid":
            # BioASQ: List of up to 5 entities, format: [["entity1"], ["entity2"], ...]
            first_sent = answer.split(".")[0].strip()
            
            # Try to extract multiple entities separated by commas/semicolons
            entities = []
            for sep in [",", ";", " and ", " or "]:
                if sep in first_sent:
                    entities = [e.strip() for e in first_sent.split(sep) if e.strip()]
                    break
            
            if not entities or entities == ['']:
                entities = [first_sent] if first_sent else ["Information not available"]
            
            # Limit to 5 entities and wrap each in list
            question_entry["exact_answer"] = [[e[:100]] for e in entities[:5] if e.strip()]
            if not question_entry["exact_answer"]:
                question_entry["exact_answer"] = [["Information not available"]]
            question_entry["ideal_answer"] = ideal_answer
            
        elif qtype == "list":
            # BioASQ: Single list of up to 100 entries, max 100 chars each
            # Format: [["item1"], ["item2"], ...]
            lines = [line.strip() for line in answer.split("\n") if line.strip()]
            items = []
            
            for line in lines:
                # Check if line starts with numbering or bullet
                if line and (line[0].isdigit() or line[0] in "-*•"):
                    # Remove leading numbers, dots, dashes, bullets
                    item = line.lstrip("0123456789.-*• ").strip()
                else:
                    item = line
                
                if item and len(items) < 100:
                    items.append([item[:100]])  # Max 100 chars per item
            
            # Always include exact_answer for list, even if empty (BioASQ requirement)
            question_entry["exact_answer"] = items if items else [["No specific items identified"]]
            question_entry["ideal_answer"] = ideal_answer
        
        else:  # summary
            # BioASQ: Summary questions only have ideal_answer (no exact_answer)
            question_entry["ideal_answer"] = ideal_answer
        
        submission["questions"].append(question_entry)

    with open(output_path, "w") as f:
        json.dump(submission, f, indent=2)

    logger.info(f"Saved BioASQ submission file to {output_path}")

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser("BioASQ Synergy RAG Pipeline")

    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--dataset_root", type=Path, required=True)
    parser.add_argument("--testset_root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    testset_path = (
        args.testset_root
        / f"round_{args.round}"
        / f"testset_round_{args.round}.json"
    )

    pubmed_path = args.dataset_root / "pubmed_round3_corpus.jsonl"

    questions = load_bioasq_testset(testset_path)

    results = run_pipeline(
        questions=questions,
        pubmed_path=pubmed_path,
        config_path=args.config,
    )

    output_file = args.output / f"round_{args.round}_results.json"
    save_results(results, output_file)

if __name__ == "__main__":
    main()
