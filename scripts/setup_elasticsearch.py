#!/usr/bin/env python3
"""
Setup Elasticsearch for the Medical RAG system.
Since Docker may not be available, this script provides alternatives.
"""

import os
import sys
import subprocess
import time
import json
import yaml
from pathlib import Path

def check_elasticsearch_running():
    """Check if Elasticsearch is already running"""
    try:
        from elasticsearch import Elasticsearch
        es = Elasticsearch(["http://localhost:9200"])
        if es.ping():
            print("✓ Elasticsearch is running on localhost:9200")
            return True
    except Exception as e:
        print(f"✗ Elasticsearch not accessible: {e}")
    return False

def start_elasticsearch_docker():
    """Try to start Elasticsearch using Docker Compose"""
    docker_path = Path("docker/compose.yml")
    if not docker_path.exists():
        print(f"✗ Docker compose file not found: {docker_path}")
        return False
    
    try:
        print("Attempting to start Elasticsearch with Docker Compose...")
        result = subprocess.run(
            ["docker", "compose", "-f", "docker/compose.yml", "up", "-d", "elasticsearch"],
            cwd="/home/Jdalton/codespace/medrag",
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ Docker container started. Waiting for Elasticsearch...")
            # Wait for Elasticsearch to be ready
            for i in range(30):
                if check_elasticsearch_running():
                    return True
                time.sleep(1)
            return check_elasticsearch_running()
        else:
            print(f"✗ Docker error: {result.stderr.decode()}")
    except FileNotFoundError:
        print("✗ Docker/docker-compose not found")
    except Exception as e:
        print(f"✗ Error starting Docker: {e}")
    
    return False

def install_elasticsearch_locally():
    """Provide instructions for manual Elasticsearch setup"""
    print("\n" + "="*70)
    print("ELASTICSEARCH SETUP OPTIONS")
    print("="*70)
    
    print("\nOption 1: Install Elasticsearch locally (Linux)")
    print("  wget https://artifacts.elastic.co/downloads/elasticsearch/elasticsearch-8.x.x-linux-x86_64.tar.gz")
    print("  tar -xzf elasticsearch-8.x.x-linux-x86_64.tar.gz")
    print("  cd elasticsearch-8.x.x")
    print("  ./bin/elasticsearch")
    
    print("\nOption 2: Use Python library as fallback")
    print("  pip install opensearchpy  # Alternative search engine")
    print("  (The system can work without Elasticsearch, using only FAISS)")
    
    print("\nOption 3: Cloud-hosted Elasticsearch")
    print("  Use Elastic Cloud (free tier available)")
    print("  Then update configs/pipeline_config.yaml with your cloud credentials")
    
    print("\n" + "="*70)
    print("For now, the pipeline will run with FAISS + fallback BM25\n")

def disable_elasticsearch_requirement():
    """Create a fallback mode without Elasticsearch"""
    config_path = Path("configs/pipeline_config.yaml")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Add fallback mode
    if "fallback" not in config:
        config["fallback"] = {
            "use_elasticsearch": False,
            "use_faiss_only": True
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        
        print("✓ Created fallback configuration (FAISS-only mode)")
        return True
    
    return False

def main():
    print("Setting up Elasticsearch for Medical RAG System...\n")
    
    # Check if already running
    if check_elasticsearch_running():
        print("\n✓ Elasticsearch is ready!")
        return 0
    
    # Try Docker Compose
    print("\n1. Trying Docker Compose...")
    if start_elasticsearch_docker():
        print("✓ Elasticsearch started successfully!")
        return 0
    
    # Provide alternatives
    print("\n2. Docker not available. Here are alternatives:\n")
    install_elasticsearch_locally()
    
    # Create fallback mode
    print("3. Setting up fallback configuration...")
    disable_elasticsearch_requirement()
    
    print("\nℹ️  The pipeline will run in FAISS-only mode (without Elasticsearch BM25)")
    print("ℹ️  To use full hybrid search, set up Elasticsearch and update config\n")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())
