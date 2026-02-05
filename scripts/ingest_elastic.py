#!/usr/bin/env python3
"""
ingest_elastic.py
-----------------
Ingest PubMed documents into Elasticsearch for BM25 retrieval
(BioASQ Synergy–safe version)

• Snapshot-locked
• Streaming ingest
• Safe index recreation
• Robust date handling
"""

import argparse
import json
import yaml
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk


# -----------------------------
# Config loading
# -----------------------------
def load_config(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


# -----------------------------
# Index creation (SAFE)
# -----------------------------
def create_index(es, index_name, snapshot_date, force=False):
    if es.indices.exists(index=index_name):
        if not force:
            raise RuntimeError(
                f"Index '{index_name}' already exists.\n"
                f"Use --force to recreate it explicitly."
            )
        print(f"[WARN] Deleting existing index '{index_name}'")
        es.indices.delete(index=index_name)

    body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "doc_id": {"type": "keyword"},
                "pmid": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "english"},
                "abstract": {"type": "text", "analyzer": "english"},
                "pub_date": {
                    "type": "date",
                    "format": (
                        "yyyy||yyyy-MM||yyyy-MM-dd||"
                        "MMM yyyy||strict_date_optional_time"
                    )
                },
                "snapshot_date": {"type": "date"},
                "source": {"type": "keyword"}
            }
        }
    }

    es.indices.create(index=index_name, body=body)
    print(f"[OK] Created index '{index_name}' (snapshot {snapshot_date})")


# -----------------------------
# Streaming document generator
# -----------------------------
def generate_actions(docs_path, index_name, snapshot_date):
    with open(docs_path, "r") as f:
        for line in f:
            if not line.strip():
                continue

            doc = json.loads(line)

            # Use pmid as the _id if doc_id is missing
            doc_id = doc.get("doc_id") or doc.get("pmid")

            yield {
                "_index": index_name,
                "_id": doc_id,
                "_source": {
                    **doc,
                    "snapshot_date": snapshot_date,
                    "source": "pubmed"
                }
            }


# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Pipeline YAML config")
    parser.add_argument("--docs", required=True, help="PubMed JSONL corpus")
    parser.add_argument(
        "--snapshot-date",
        required=True,
        help="PubMed snapshot date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recreate index if it exists"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)
    bm25 = config["bm25"]

    # Connect ES
    es = Elasticsearch(
        [f"http://{bm25['elasticsearch_host']}:{bm25['elasticsearch_port']}"]
    )

    print("[OK] Connected to Elasticsearch")

    # Create index
    create_index(
        es,
        bm25["index_name"],
        args.snapshot_date,
        force=args.force
    )

    # Ingest
    print("[INFO] Starting bulk ingest...")
    success, failed = 0, 0

    for ok, result in streaming_bulk(
        es,
        generate_actions(
            args.docs,
            bm25["index_name"],
            args.snapshot_date
        ),
        chunk_size=1000
    ):
        if ok:
            success += 1
        else:
            failed += 1

    print(f"[DONE] Ingested {success} documents")
    if failed:
        print(f"[WARN] {failed} documents failed")


if __name__ == "__main__":
    main()
