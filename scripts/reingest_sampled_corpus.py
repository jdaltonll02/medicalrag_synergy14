#!/usr/bin/env python3
"""
reingest_sampled_corpus.py
--------------------------
Reingest sampled 400K document corpus into Elasticsearch

This script:
1. Deletes the existing index (optional)
2. Creates a new index with Synergy snapshot metadata
3. Ingests the sampled JSONL corpus with round metadata

Usage:
    python scripts/reingest_sampled_corpus.py \
        --config configs/pipeline_config.yaml \
        --corpus /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_400k.jsonl \
        --snapshot-date 2026-02-19 \
        --delete-existing
"""

import argparse
import json
import yaml
import logging
from pathlib import Path
from datetime import datetime
from typing import Tuple
from tqdm import tqdm
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    """Load YAML configuration"""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def create_index(es: Elasticsearch, index_name: str, snapshot_date: str, force: bool = False) -> bool:
    """
    Create Elasticsearch index with appropriate mappings
    
    Args:
        es: Elasticsearch client
        index_name: Name of index to create
        snapshot_date: Date of PubMed snapshot (YYYY-MM-DD)
        force: Delete existing index if it exists
    
    Returns:
        True if successful
    """
    
    if es.indices.exists(index=index_name):
        if not force:
            logger.error(f"Index '{index_name}' already exists. Use --delete-existing to recreate.")
            return False
        
        logger.info(f"Deleting existing index '{index_name}'...")
        es.indices.delete(index=index_name)
    
    # Index mapping
    body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "english": {
                            "type": "standard",
                            "stopwords": "_english_"
                        }
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "pmid": {
                    "type": "keyword",
                    "index": True
                },
                "title": {
                    "type": "text",
                    "analyzer": "english",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "abstract": {
                    "type": "text",
                    "analyzer": "english"
                },
                "snapshot_round": {
                    "type": "integer",
                    "index": True
                },
                "snapshot_date": {
                    "type": "date",
                    "format": "yyyy-MM-dd"
                },
                "source": {
                    "type": "keyword"
                },
                "ingested_at": {
                    "type": "date"
                }
            }
        }
    }
    
    try:
        es.indices.create(index=index_name, body=body)
        logger.info(f"Created index '{index_name}'")
        return True
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        return False


def generate_actions(docs_path: str, index_name: str, snapshot_date: str):
    """
    Generate Elasticsearch bulk actions from JSONL corpus
    
    Args:
        docs_path: Path to JSONL corpus
        index_name: Elasticsearch index name
        snapshot_date: Snapshot date (YYYY-MM-DD)
    
    Yields:
        Dict for bulk ingestion
    """
    
    ingest_time = datetime.utcnow().isoformat()
    
    with open(docs_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            try:
                doc = json.loads(line)
                
                # Use PMID as document ID
                doc_id = doc.get('pmid')
                if not doc_id:
                    logger.warning(f"Line {line_num}: Missing PMID, skipping")
                    continue
                
                yield {
                    "_index": index_name,
                    "_id": doc_id,
                    "_source": {
                        "pmid": doc_id,
                        "title": doc.get('title', ''),
                        "abstract": doc.get('abstract', ''),
                        "snapshot_round": doc.get('snapshot_round', 0),
                        "snapshot_date": snapshot_date,
                        "source": "pubmed",
                        "ingested_at": ingest_time
                    }
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Line {line_num}: JSON decode error: {e}")
                continue


def ingest_corpus(
    es: Elasticsearch,
    docs_path: str,
    index_name: str,
    snapshot_date: str,
    chunk_size: int = 1000
) -> Tuple[int, int]:
    """
    Ingest corpus into Elasticsearch with progress bar
    
    Args:
        es: Elasticsearch client
        docs_path: Path to JSONL corpus
        index_name: Index name
        snapshot_date: Snapshot date
        chunk_size: Bulk request chunk size
    
    Returns:
        Tuple of (successful, failed) document counts
    """
    
    logger.info(f"Starting bulk ingest from {docs_path}...")
    
    success = 0
    failed = 0
    
    # Progress bar with tqdm
    pbar = tqdm(
        streaming_bulk(
            es,
            generate_actions(docs_path, index_name, snapshot_date),
            chunk_size=chunk_size,
            raise_on_error=False
        ),
        desc="Ingesting documents",
        unit="docs",
        total=300000  # Total documents expected
    )
    
    for ok, result in pbar:
        if ok:
            success += 1
        else:
            failed += 1
            if failed <= 10:  # Log first 10 failures
                error_info = result.get('index', {})
                logger.warning(f"Failed to ingest: {error_info}")
        
        # Update progress bar description with stats
        pbar.set_description(f"Ingesting documents ({success:,} ok, {failed:,} failed)")
    
    pbar.close()
    logger.info(f"Ingest complete: {success:,} successful, {failed:,} failed")
    return success, failed


def main():
    parser = argparse.ArgumentParser(description="Reingest sampled 300K corpus into Elasticsearch")
    parser.add_argument(
        "--config",
        required=True,
        help="Pipeline YAML config file"
    )
    parser.add_argument(
        "--corpus",
        required=True,
        help="Path to sampled JSONL corpus"
    )
    parser.add_argument(
        "--snapshot-date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Snapshot date (YYYY-MM-DD, default today)"
    )
    parser.add_argument(
        "--index",
        help="Index name (overrides config)"
    )
    parser.add_argument(
        "--host",
        help="Elasticsearch host (overrides config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Elasticsearch port (overrides config)"
    )
    parser.add_argument(
        "--delete-existing",
        action="store_true",
        help="Delete existing index before ingesting"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Bulk request chunk size (default 1000)"
    )
    
    args = parser.parse_args()
    
    # Validate corpus exists
    if not Path(args.corpus).exists():
        logger.error(f"Corpus file not found: {args.corpus}")
        exit(1)
    
    # Load config
    config = load_config(args.config)
    bm25_config = config.get('bm25', {})
    
    # Get parameters
    host = args.host or bm25_config.get('elasticsearch_host', 'localhost')
    port = args.port or bm25_config.get('elasticsearch_port', 9200)
    index_name = args.index or bm25_config.get('index_name', 'medical_docs')
    
    logger.info("=== Elasticsearch Ingestion Configuration ===")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Index: {index_name}")
    logger.info(f"Corpus: {args.corpus}")
    logger.info(f"Snapshot date: {args.snapshot_date}")
    logger.info("")
    
    try:
        # Connect to Elasticsearch
        es = Elasticsearch([f"http://{host}:{port}"])
        
        if not es.ping():
            logger.error("Cannot connect to Elasticsearch")
            exit(1)
        
        logger.info("Connected to Elasticsearch")
        
        # Create index
        if not create_index(es, index_name, args.snapshot_date, force=args.delete_existing):
            exit(1)
        
        # Ingest corpus
        success, failed = ingest_corpus(
            es,
            args.corpus,
            index_name,
            args.snapshot_date,
            chunk_size=args.chunk_size
        )
        
        logger.info(f"\n=== Ingestion Complete ===")
        logger.info(f"Successfully ingested: {success:,} documents")
        logger.info(f"Failed: {failed:,} documents")
        logger.info(f"Total: {success + failed:,} documents")
        
        # Get final index stats
        stats = es.indices.stats(index=index_name)
        doc_count = stats['indices'][index_name]['primaries']['docs']['count']
        store_size = stats['indices'][index_name]['primaries']['store']['size_in_bytes']
        
        logger.info(f"\nIndex Statistics:")
        logger.info(f"  Total documents in index: {doc_count:,}")
        logger.info(f"  Store size: {store_size / (1024**3):.2f} GB")
        
        if failed == 0:
            exit(0)
        else:
            exit(1)
        
    except Exception as e:
        logger.error(f"Error during ingestion: {e}")
        exit(1)


if __name__ == "__main__":
    from typing import Tuple
    main()
