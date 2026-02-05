#!/usr/bin/env python3
"""
Run BioASQ Synergy RAG pipeline (Round-aware, snapshot-safe)

This script:
1. Loads official BioASQ testset JSON
2. Streams local PubMed corpus (JSONL) — OOM SAFE
3. Builds BM25 + FAISS indices incrementally
4. Runs RAG pipeline
5. Outputs BioASQ-formatted results

IMPORTANT:
- Uses ONLY local PubMed snapshot
- No online PubMed fetching
- Does NOT load entire corpus into memory
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Iterator

import yaml

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
# Stream PubMed corpus (JSONL) — NO RAM BLOWUP
# ---------------------------------------------------------------------
def stream_pubmed_corpus(jsonl_path: Path) -> Iterator[Dict[str, Any]]:
    logger.info(f"Streaming PubMed corpus from {jsonl_path}")

    with open(jsonl_path, "r") as f:
        for line in f:
            if not line.strip():
                continue

            doc = json.loads(line)

            # Accept BOTH schemas safely
            pmid = doc.get("doc_id") or doc.get("pmid")
            abstract = doc.get("abstract", "")

            if not pmid or not abstract:
                continue

            title = doc.get("title", "")

            yield {
                "doc_id": pmid,
                "title": title,
                "abstract": abstract,
                "text": f"{title}\n\n{abstract}".strip(),
                "metadata": {"pmid": pmid}
            }

# ---------------------------------------------------------------------
# Incremental indexing (CRITICAL FIX)
# ---------------------------------------------------------------------
def index_pubmed_stream(
    pipeline: MedicalRAGPipeline,
    corpus_stream: Iterator[Dict[str, Any]],
    batch_size: int = 5000,
):
    logger.info("Indexing PubMed documents (streaming mode)")
    batch = []
    total = 0

    for doc in corpus_stream:
        batch.append(doc)

        if len(batch) >= batch_size:
            pipeline.index_documents(batch)
            total += len(batch)
            logger.info(f"Indexed {total} documents")
            batch.clear()

    if batch:
        pipeline.index_documents(batch)
        total += len(batch)

    logger.info(f"Finished indexing {total} PubMed documents")

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

    #pipeline = MedicalRAGPipeline(config)

    pipeline = MedicalRAGPipeline(config)
    # STREAM + BATCH INDEXING (FIXES OOM)
    corpus_stream = stream_pubmed_corpus(pubmed_path)
    index_pubmed_stream(pipeline, corpus_stream)

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
    parser.add_argument(
        "--dataset_root",
        type=Path,
        required=True,
        help="Directory containing pubmed_corpus.jsonl"
    )
    parser.add_argument(
        "--testset_root",
        type=Path,
        required=True,
        help="Directory containing BioASQ testsets"
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()

    testset_path = (
        args.testset_root
        / f"round_{args.round}"
        / f"testset_round_{args.round}.json"
    )
    pubmed_path = args.dataset_root / "pubmed_corpus.jsonl"

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
