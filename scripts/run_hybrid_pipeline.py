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

        output = pipeline.process_query(query)

        results.append({
            "id": qid,
            "type": qtype,
            "query": query,
            "answer": output.get("answer"),
            "documents": [
                d["doc_id"] for d in output.get("final_documents", [])
            ],
            "snippets": output.get("snippets", [])
        })

    return results

# ---------------------------------------------------------------------
# Save results (BioASQ submission format)
# ---------------------------------------------------------------------
def save_results(results: List[Dict[str, Any]], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    submission = {"questions": []}

    for r in results:
        submission["questions"].append({
            "id": r["id"],
            "documents": r["documents"],
            "snippets": r["snippets"],
            "exact_answer": r["answer"]
            if r["type"] in {"factoid", "list", "yesno"} else None,
            "ideal_answer": r["answer"]
            if r["type"] == "summary" else None
        })

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

    pubmed_path = args.dataset_root / "pubmed_round2_corpus.jsonl"

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
