#!/usr/bin/env python3
"""
delete_index.py
---------------
Delete Elasticsearch index safely

Usage:
    python scripts/delete_index.py \
        --config configs/pipeline_config.yaml \
        --confirm
"""

import argparse
import yaml
import logging
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


def delete_index(host: str, port: int, index_name: str, force: bool = False) -> bool:
    """
    Delete Elasticsearch index
    
    Args:
        host: Elasticsearch host
        port: Elasticsearch port
        index_name: Index name to delete
        force: Skip confirmation
    
    Returns:
        True if successful, False otherwise
    """
    
    try:
        es = Elasticsearch([f"http://{host}:{port}"])
        
        # Check connection
        if not es.ping():
            logger.error("Cannot connect to Elasticsearch")
            return False
        
        logger.info(f"Connected to Elasticsearch at {host}:{port}")
        
        # Check if index exists
        if not es.indices.exists(index=index_name):
            logger.warning(f"Index '{index_name}' does not exist")
            return False
        
        logger.info(f"Index '{index_name}' exists")
        
        # Get index stats
        stats = es.indices.stats(index=index_name)
        doc_count = stats['indices'][index_name]['primaries']['docs']['count']
        store_size = stats['indices'][index_name]['primaries']['store']['size_in_bytes']
        
        logger.info(f"Index statistics:")
        logger.info(f"  Documents: {doc_count:,}")
        logger.info(f"  Store size: {store_size / (1024**3):.2f} GB")
        
        # Confirm deletion
        if not force:
            response = input(f"\nAre you sure you want to delete index '{index_name}'? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Deletion cancelled")
                return False
        
        # Delete index
        logger.info(f"Deleting index '{index_name}'...")
        es.indices.delete(index=index_name)
        logger.info(f"Index '{index_name}' deleted successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"Error deleting index: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Delete Elasticsearch index")
    parser.add_argument(
        "--config",
        required=True,
        help="Pipeline YAML config file"
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
        "--confirm",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config(args.config)
    bm25_config = config.get('bm25', {})
    
    # Get parameters from args or config
    host = args.host or bm25_config.get('elasticsearch_host', 'localhost')
    port = args.port or bm25_config.get('elasticsearch_port', 9200)
    index = args.index or bm25_config.get('index_name', 'medical_docs')
    
    logger.info(f"Configuration:")
    logger.info(f"  Host: {host}")
    logger.info(f"  Port: {port}")
    logger.info(f"  Index: {index}")
    
    success = delete_index(host, port, index, force=args.confirm)
    
    if success:
        logger.info("\n=== Index Deletion Complete ===")
        exit(0)
    else:
        logger.error("\n=== Index Deletion Failed ===")
        exit(1)


if __name__ == "__main__":
    main()
