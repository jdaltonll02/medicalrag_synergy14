# 200K Document Corpus Setup Guide

## Overview

This guide explains how to set up a 200K document corpus from the full PubMed dataset, with 100K documents from each of the BioASQ Synergy round 1 and round 2 snapshots. This allows testing the pipeline on a manageable subset while maintaining representation from different time periods.

## Quick Start

### One-Command Setup

```bash
cd /home/jgibson2/projects/medrag

# Run the complete setup (requires Elasticsearch running)
./setup_200k_corpus.sh \
    --config configs/pipeline_config.yaml \
    --email your.email@example.com \
    --confirm-delete
```

This will:
1. Sample 200K documents based on BioASQ Synergy snapshot dates
   - Round 1: Documents published on or before 2026-01-09
   - Round 2: Documents published between 2026-01-09 and 2026-01-22
2. Delete existing Elasticsearch index
3. Reingest sampled documents with round metadata

## Component Scripts

### 1. `scripts/sample_corpus.py` - Sampling Documents

**Purpose**: Sample 200K documents from the full 33M document corpus using BioASQ Synergy snapshot dates

**Features**:
- Uses **actual PubMed snapshot dates** for accurate round assignment:
  - Round 1: Documents published on or before **2026-01-09**
  - Round 2: Documents published between **2026-01-09** and **2026-01-22**
- Fetches publication dates from PubMed API for accurate assignment
- Random sampling for balance within each round
- Uses configurable random seed for reproducibility
- Adds `snapshot_round` metadata to each document
- Efficient memory usage for large corpus

**Key Difference from Earlier Version**:
Previously, the script used a naive "first half / second half" approach. Now it properly:
1. Fetches publication dates from PubMed for sampled documents
2. Assigns them to rounds based on BioASQ snapshot dates
3. Balances sampling across the actual temporal distribution

**Usage**:

```bash
python scripts/sample_corpus.py \
    --input /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl \
    --output /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl \
    --sample-size 200000 \
    --round1-size 100000 \
    --round1-date 2026-01-09 \
    --round2-date 2026-01-22 \
    --email your.email@example.com \
    --seed 42
```

**Output**:
```
Keys: ['pmid', 'title', 'abstract', 'snapshot_round']
Example:
{
    "pmid": "244771",
    "title": "In vitro reaction to antibiotics in Klebsiella...",
    "abstract": "According to the antibiotic sensitivity tests...",
    "snapshot_round": 1  // 1 or 2 based on pub_date
}
```

**Command-line Arguments**:
- `--input` (required): Path to full JSONL corpus
- `--output` (required): Path to output sampled corpus
- `--sample-size`: Total documents to sample (default: 200000)
- `--round1-size`: Approximate documents for round 1 (default: 100000)
- `--round1-date`: Round 1 snapshot date YYYY-MM-DD (default: 2026-01-09)
- `--round2-date`: Round 2 snapshot date YYYY-MM-DD (default: 2026-01-22)
- `--email` (required): Email for PubMed API access
- `--api-key`: Optional NCBI API key for faster requests
- `--seed`: Random seed for reproducibility (default: 42)

**Time Complexity**:
- Reading corpus: ~5 minutes (33M lines)
- Sampling: ~2 minutes (random selection)
- Fetching publication dates: **~30-45 minutes** (API calls to PubMed)
- Writing output: ~2 minutes
- **Total: ~40-55 minutes** (longer than before due to PubMed fetches)

**Important Notes**:
- Requires `email` parameter for PubMed API compliance
- Fetching dates requires internet connection to PubMed
- API rate limiting: ~3 requests/second
- Documents without available publication dates are randomly distributed between rounds
- The actual round sizes may vary slightly from requested (e.g., 98K/102K instead of 100K/100K) due to temporal distribution

### 2. `scripts/delete_index.py` - Delete Elasticsearch Index

**Purpose**: Safely delete the current Elasticsearch index before reingestion

**Features**:
- Verifies Elasticsearch connectivity
- Checks if index exists
- Shows index statistics before deletion
- Requires confirmation unless `--confirm` is used
- Handles graceful errors

**Usage**:

```bash
# Interactive (requires confirmation)
python scripts/delete_index.py --config configs/pipeline_config.yaml

# Non-interactive (skip confirmation)
python scripts/delete_index.py --config configs/pipeline_config.yaml --confirm
```

**Example Output**:
```
Connected to Elasticsearch at localhost:9200
Index 'medical_docs' exists
Index statistics:
  Documents: 33,070,065
  Store size: 24.32 GB

Are you sure you want to delete index 'medical_docs'? (yes/no): yes
Index 'medical_docs' deleted successfully
```

**Command-line Arguments**:
- `--config` (required): Pipeline YAML config file
- `--index`: Index name (overrides config)
- `--host`: Elasticsearch host (overrides config)
- `--port`: Elasticsearch port (overrides config)
- `--confirm`: Skip confirmation prompt

### 3. `scripts/reingest_sampled_corpus.py` - Reingest Sampled Corpus

**Purpose**: Ingest the 200K sampled corpus into Elasticsearch

**Features**:
- Creates index with appropriate mappings for Synergy task
- Streams documents for memory efficiency
- Adds Elasticsearch metadata (source, snapshot_date, ingested_at)
- Tracks ingestion progress
- Reports detailed statistics

**Usage**:

```bash
python scripts/reingest_sampled_corpus.py \
    --config configs/pipeline_config.yaml \
    --corpus /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl \
    --snapshot-date 2026-02-04 \
    --delete-existing
```

**Index Mappings**:
```yaml
Index: medical_docs
Shards: 1
Replicas: 0
Properties:
  pmid: keyword (indexed)
  title: text (english analyzer, with keyword subfield)
  abstract: text (english analyzer)
  snapshot_round: integer (indexed) - 1 or 2
  snapshot_date: date (YYYY-MM-DD)
  source: keyword - "pubmed"
  ingested_at: date - ISO timestamp
```

**Command-line Arguments**:
- `--config` (required): Pipeline YAML config
- `--corpus` (required): Path to sampled JSONL corpus
- `--snapshot-date`: Date in YYYY-MM-DD format (default: today)
- `--index`: Index name (overrides config)
- `--host`: Elasticsearch host (overrides config)
- `--port`: Elasticsearch port (overrides config)
- `--delete-existing`: Delete existing index before ingesting
- `--chunk-size`: Bulk request size (default: 1000)

**Example Output**:
```
Connected to Elasticsearch
Created index 'medical_docs'
Starting bulk ingest...
Progress: 10,000 documents processed (10,000 successful, 0 failed)
Progress: 20,000 documents processed (20,000 successful, 0 failed)
...
=== Ingestion Complete ===
Successfully ingested: 200,000 documents
Failed: 0 documents
Total: 200,000 documents

Index Statistics:
  Total documents in index: 200,000
  Store size: 0.15 GB
```

### 4. `setup_200k_corpus.sh` - Master Orchestration Script

**Purpose**: Orchestrate the complete setup process with step-by-step feedback

**Features**:
- Verifies all prerequisites
- Executes all three steps in sequence
- Provides colored output and progress indicators
- Handles errors gracefully
- Generates summary report

**Usage**:

```bash
# Full setup with confirmation
./setup_200k_corpus.sh --config configs/pipeline_config.yaml

# Non-interactive mode (skip deletion confirmation)
./setup_200k_corpus.sh --config configs/pipeline_config.yaml --confirm-delete

# Custom parameters
./setup_200k_corpus.sh \
    --config configs/pipeline_config.yaml \
    --input /path/to/full/corpus.jsonl \
    --output /path/to/sampled/corpus.jsonl \
    --sample-size 200000 \
    --snapshot-date 2026-02-04 \
    --confirm-delete
```

**Output**:
```
========================================
   200K Corpus Setup Orchestration
========================================

[STEP 0] Verifying configuration...
✓ Config file found
✓ Input corpus found

[STEP 1] Sampling 200K documents...
  - Round 1 snapshot: First 100K documents
  - Round 2 snapshot: Next 100K documents
✓ Sampling complete!
  - Size: 150M
  - Documents: 200,000

[STEP 2] Deleting existing Elasticsearch index...
✓ Index deleted

[STEP 3] Reingesting 200K sampled corpus...
✓ Ingestion complete!

========================================
   Setup Complete!
========================================

Summary:
  - Sampled corpus: .../pubmed_corpus_200k.jsonl
  - Documents: 200,000 (100K round 1 + 100K round 2)
  - Ingested into Elasticsearch
```

## Data Structure

### Full Corpus
- **Location**: `/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl`
- **Size**: 49 GB
- **Documents**: 33,070,065
- **Format**: JSONL (one JSON object per line)

### Document Structure
```json
{
    "pmid": "244771",
    "title": "Title text...",
    "abstract": "Abstract text..."
}
```

### Sampled Corpus (200K)
- **Location**: `/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl`
- **Size**: ~150 MB
- **Documents**: 200,000 (100K from first half + 100K from second half)
- **Format**: JSONL with added `snapshot_round` field

### Document Structure (Sampled)
```json
{
    "pmid": "244771",
    "title": "Title text...",
    "abstract": "Abstract text...",
    "snapshot_round": 1
}
```

### Elasticsearch Index
- **Index Name**: `medical_docs`
- **Shard Configuration**: 1 shard, 0 replicas
- **Index Size**: ~150 MB
- **Fields**:
  - `pmid`: Document ID (keyword)
  - `title`: Full text (english analyzer)
  - `abstract`: Full text (english analyzer)
  - `snapshot_round`: 1 or 2 (for tracking which snapshot)
  - `snapshot_date`: ISO date of snapshot
  - `source`: Always "pubmed" (keyword)
  - `ingested_at`: ISO timestamp of ingestion

## Prerequisites

### System Requirements
- Python 3.7+
- Elasticsearch 8.x running on `localhost:9200`
- ~50 GB free disk space (for temporary files during sampling)
- Network access to check Elasticsearch

### Python Dependencies
```
elasticsearch>=8.0.0
pyyaml>=5.1
```

Install with:
```bash
pip install elasticsearch pyyaml
```

### Elasticsearch Setup

If Elasticsearch is not running:

```bash
# Start Elasticsearch (Docker)
docker-compose -f docker/compose.yml up -d

# Or manually from extracted tarball
cd /data/user_data/jgibson2/bioask_pubmed_dataset
./elasticsearch/bin/elasticsearch -d

# Verify connection
curl http://localhost:9200/
```

## Workflow

### Initial Setup (All 33M Documents)

```bash
# Original full corpus ingestion
python scripts/ingest_elastic.py \
    --config configs/pipeline_config.yaml \
    --docs /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl \
    --snapshot-date 2026-02-04 \
    --force
```

### Switching to 200K Subset

```bash
# 1. Sample corpus
python scripts/sample_corpus.py \
    --input /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl \
    --output /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl

# 2. Delete old index
python scripts/delete_index.py \
    --config configs/pipeline_config.yaml \
    --confirm

# 3. Reingest with sampled corpus
python scripts/reingest_sampled_corpus.py \
    --config configs/pipeline_config.yaml \
    --corpus /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl \
    --delete-existing
```

### Or Use Master Script

```bash
./setup_200k_corpus.sh --config configs/pipeline_config.yaml --confirm-delete
```

## Configuration Updates

After ingestion, verify your config points to the sampled corpus:

**File**: `configs/pipeline_config.yaml`

```yaml
data:
  docs_path: /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl
  # ... other settings ...

bm25:
  elasticsearch_host: localhost
  elasticsearch_port: 9200
  index_name: medical_docs
  # ... other settings ...
```

## Querying the Ingested Data

### Test Connection

```bash
curl http://localhost:9200/medical_docs/_count
# Expected output: { "count" : 200000, ... }
```

### Count by Round

```bash
# Count documents from round 1
curl -X POST http://localhost:9200/medical_docs/_count \
  -H 'Content-Type: application/json' \
  -d '{"query": {"term": {"snapshot_round": 1}}}'

# Count documents from round 2
curl -X POST http://localhost:9200/medical_docs/_count \
  -H 'Content-Type: application/json' \
  -d '{"query": {"term": {"snapshot_round": 2}}}'
```

### Sample Search

```bash
curl -X POST http://localhost:9200/medical_docs/_search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "multi_match": {
        "query": "cancer immunotherapy",
        "fields": ["title^2", "abstract"]
      }
    },
    "size": 10
  }'
```

## Troubleshooting

### Issue: "Cannot connect to Elasticsearch"
**Solution**: Start Elasticsearch first
```bash
docker-compose -f docker/compose.yml up -d
# OR manually start it
```

### Issue: "Index already exists" error
**Solution**: Use the `--delete-existing` flag
```bash
python scripts/reingest_sampled_corpus.py \
    --config configs/pipeline_config.yaml \
    --corpus /path/to/corpus.jsonl \
    --delete-existing
```

### Issue: Sampling takes too long
**Solution**: The corpus has 33M documents. Sampling typically takes 15-25 minutes. This is normal.

### Issue: Out of memory during sampling
**Solution**: The scripts use streaming to minimize memory. If you still have issues:
- Free up system memory
- Reduce `--sample-size` parameter
- Check available disk space

### Issue: Ingestion fails midway
**Solution**: 
1. Check Elasticsearch logs
2. Verify disk space
3. Try again with same snapshot - documents with same PMID will overwrite

## Performance Characteristics

### Sampling Performance (33M → 200K)
- **Time**: 15-25 minutes
- **Memory**: ~500 MB
- **Disk I/O**: Sequential read from corpus file

### Ingestion Performance (200K documents)
- **Time**: 2-5 minutes
- **Memory**: ~1 GB
- **Disk I/O**: Sequential write to Elasticsearch
- **Index Size**: ~150 MB

### Total Setup Time
- **Total**: ~20-30 minutes (first run)
- **Subsequent runs**: ~10-20 minutes (skip Elasticsearch startup)

## Next Steps

After setting up the 200K corpus:

1. **Test Retrieval**:
   ```bash
   python scripts/run_pipeline_bm25.py \
       --config configs/pipeline_config.yaml \
       --query "What is the role of HIF-1α in cancer?"
   ```

2. **Run Full Synergy Pipeline**:
   ```bash
   python scripts/run_synergy_pipeline.py \
       --config configs/pipeline_config.yaml
   ```

3. **Evaluate Results**:
   ```bash
   python evaluation/evaluation_QA_system/evaluation_pipeline.ipynb
   ```

## References

- **BioASQ Synergy Task**: https://participants-area.bioasq.org/Tasks/synergy/
- **Elasticsearch Documentation**: https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html
- **PubMed Dataset**: https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/
