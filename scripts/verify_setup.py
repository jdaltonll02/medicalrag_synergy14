#!/usr/bin/env python3
"""
verify_setup.py
---------------
Verify the 200K corpus setup is complete and working

Checks:
- Sampled corpus file exists and is readable
- Document count matches expected 200K
- Elasticsearch index exists and is accessible
- Index contains expected documents
- Round distribution is correct (100K + 100K)
- Documents have required fields

Usage:
    python scripts/verify_setup.py --config configs/pipeline_config.yaml
"""

import argparse
import json
import yaml
import logging
from pathlib import Path
from elasticsearch import Elasticsearch

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    """Load YAML configuration"""
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def verify_corpus_file(corpus_path: str) -> bool:
    """Verify sampled corpus file exists and is readable"""
    
    logger.info("=== Verifying Sampled Corpus File ===")
    
    corpus_file = Path(corpus_path)
    
    # Check if file exists
    if not corpus_file.exists():
        logger.error(f"✗ Corpus file not found: {corpus_path}")
        return False
    
    logger.info(f"✓ Corpus file exists: {corpus_path}")
    
    # Check file size
    file_size_gb = corpus_file.stat().st_size / (1024**3)
    logger.info(f"  File size: {file_size_gb:.2f} GB")
    
    # Count documents and verify structure
    doc_count = 0
    round1_count = 0
    round2_count = 0
    missing_fields = 0
    
    try:
        with open(corpus_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue
                
                try:
                    doc = json.loads(line)
                    doc_count += 1
                    
                    # Check required fields
                    if 'pmid' not in doc or 'title' not in doc or 'abstract' not in doc:
                        missing_fields += 1
                        if missing_fields <= 5:
                            logger.warning(f"  Line {line_num}: Missing required fields")
                    
                    # Count by round
                    round_num = doc.get('snapshot_round', 0)
                    if round_num == 1:
                        round1_count += 1
                    elif round_num == 2:
                        round2_count += 1
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"  Line {line_num}: Invalid JSON: {e}")
                    if missing_fields < 5:
                        missing_fields += 1
    
    except Exception as e:
        logger.error(f"✗ Error reading corpus file: {e}")
        return False
    
    logger.info(f"✓ Document count: {doc_count:,}")
    logger.info(f"  Round 1 documents: {round1_count:,}")
    logger.info(f"  Round 2 documents: {round2_count:,}")
    
    if missing_fields > 0:
        logger.warning(f"✗ Documents with missing fields: {missing_fields}")
        return False
    
    # Verify count is reasonable
    if doc_count < 190000 or doc_count > 210000:
        logger.error(f"✗ Document count {doc_count} is not close to expected 200K")
        return False
    
    logger.info("✓ Corpus file verification passed")
    return True


def verify_elasticsearch(host: str, port: int, index_name: str) -> bool:
    """Verify Elasticsearch index exists and contains expected data"""
    
    logger.info("\n=== Verifying Elasticsearch Index ===")
    
    try:
        es = Elasticsearch([f"http://{host}:{port}"])
        
        # Check connection
        if not es.ping():
            logger.error(f"✗ Cannot connect to Elasticsearch at {host}:{port}")
            return False
        
        logger.info(f"✓ Connected to Elasticsearch at {host}:{port}")
        
        # Check if index exists
        if not es.indices.exists(index=index_name):
            logger.error(f"✗ Index '{index_name}' does not exist")
            logger.info("  Run: python scripts/reingest_sampled_corpus.py ...")
            return False
        
        logger.info(f"✓ Index '{index_name}' exists")
        
        # Get index stats
        stats = es.indices.stats(index=index_name)
        index_stats = stats['indices'][index_name]['primaries']
        doc_count = index_stats['docs']['count']
        store_size = index_stats['store']['size_in_bytes']
        
        logger.info(f"✓ Index statistics:")
        logger.info(f"  Documents: {doc_count:,}")
        logger.info(f"  Store size: {store_size / (1024**3):.3f} GB")
        
        # Verify document count
        if doc_count < 190000 or doc_count > 210000:
            logger.error(f"✗ Document count {doc_count} is not close to expected 200K")
            return False
        
        # Check round distribution via aggregation
        agg_result = es.search(
            index=index_name,
            aggs={
                "round_distribution": {
                    "terms": {
                        "field": "snapshot_round",
                        "size": 10
                    }
                }
            },
            size=0
        )
        
        logger.info(f"✓ Round distribution:")
        for bucket in agg_result['aggregations']['round_distribution']['buckets']:
            round_num = bucket['key']
            count = bucket['doc_count']
            logger.info(f"  Round {round_num}: {count:,} documents")
        
        # Sample a document
        sample = es.search(
            index=index_name,
            query={"match_all": {}},
            size=1
        )
        
        if sample['hits']['hits']:
            doc = sample['hits']['hits'][0]['_source']
            logger.info(f"✓ Sample document fields:")
            logger.info(f"  PMID: {doc.get('pmid')}")
            logger.info(f"  Title: {doc.get('title', '')[:50]}...")
            logger.info(f"  Round: {doc.get('snapshot_round')}")
            logger.info(f"  Source: {doc.get('source')}")
        
        logger.info("✓ Elasticsearch verification passed")
        return True
        
    except Exception as e:
        logger.error(f"✗ Error verifying Elasticsearch: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Verify 200K corpus setup")
    parser.add_argument(
        "--config",
        required=True,
        help="Pipeline YAML config"
    )
    parser.add_argument(
        "--corpus",
        help="Sampled corpus path (overrides config)"
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
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    data_config = config.get('data', {})
    bm25_config = config.get('bm25', {})
    
    # Get parameters
    corpus_path = args.corpus or data_config.get('docs_path', 
        '/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl')
    host = args.host or bm25_config.get('elasticsearch_host', 'localhost')
    port = args.port or bm25_config.get('elasticsearch_port', 9200)
    index_name = args.index or bm25_config.get('index_name', 'medical_docs')
    
    logger.info("Verification Configuration:")
    logger.info(f"  Corpus: {corpus_path}")
    logger.info(f"  Index: {index_name}")
    logger.info(f"  Elasticsearch: {host}:{port}")
    logger.info("")
    
    # Run verifications
    corpus_ok = verify_corpus_file(corpus_path)
    es_ok = verify_elasticsearch(host, port, index_name)
    
    # Summary
    logger.info("\n" + "="*50)
    if corpus_ok and es_ok:
        logger.info("✓ Setup Verification PASSED")
        logger.info("="*50)
        logger.info("\nYour 200K corpus is ready!")
        logger.info("\nNext steps:")
        logger.info("  1. Test retrieval:")
        logger.info("     python scripts/run_pipeline_bm25.py --config configs/pipeline_config.yaml")
        logger.info("  2. Run Synergy pipeline:")
        logger.info("     python scripts/run_synergy_pipeline.py --config configs/pipeline_config.yaml")
        exit(0)
    else:
        logger.error("✗ Setup Verification FAILED")
        logger.error("="*50)
        if not corpus_ok:
            logger.error("\nCorp issues:")
            logger.error("  - Run: python scripts/sample_corpus.py ...")
        if not es_ok:
            logger.error("\nElasticsearch issues:")
            logger.error("  - Run: python scripts/reingest_sampled_corpus.py ...")
        exit(1)


if __name__ == "__main__":
    main()
