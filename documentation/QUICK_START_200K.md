# Quick Reference - 200K Corpus Setup

## TL;DR - One Command

```bash
cd /home/jgibson2/projects/medrag
./setup_200k_corpus.sh \
    --config configs/pipeline_config.yaml \
    --email your.email@example.com \
    --confirm-delete
```

This takes ~50-60 minutes and does everything:
1. Samples 200K docs based on **BioASQ Synergy snapshot dates**
   - Round 1 (published ≤ 2026-01-09): ~100K documents
   - Round 2 (published 2026-01-09 to 2026-01-22): ~100K documents
2. Deletes old Elasticsearch index
3. Ingests sampled corpus with round metadata

## Individual Commands (if needed)

### Step 1: Sample Corpus (40-55 min)
**Requires:** Email for PubMed API, Internet connection
```bash
python scripts/sample_corpus.py \
    --input /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl \
    --output /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl \
    --round1-date 2026-01-09 \
    --round2-date 2026-01-22 \
    --email your.email@example.com
```

### Step 2: Delete Old Index (< 1 min)
```bash
python scripts/delete_index.py --config configs/pipeline_config.yaml --confirm
```

### Step 3: Reingest Sampled Corpus (2-5 min)
```bash
python scripts/reingest_sampled_corpus.py \
    --config configs/pipeline_config.yaml \
    --corpus /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl \
    --delete-existing
```

## Verify Setup

```bash
# Check document count
curl http://localhost:9200/medical_docs/_count

# Expected output: {"count": 200000, ...}
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/sample_corpus.py` | Sample 200K from 33M corpus |
| `scripts/delete_index.py` | Delete Elasticsearch index |
| `scripts/reingest_sampled_corpus.py` | Ingest sampled corpus |
| `setup_200k_corpus.sh` | Master orchestration script |
| `SETUP_200K_CORPUS.md` | Complete documentation |

## Data Locations

| Data | Path |
|------|------|
| Full corpus (33M) | `/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl` |
| Sampled corpus (200K) | `/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl` |
| Elasticsearch | `localhost:9200` |
| Index name | `medical_docs` |

## Configuration

Update `configs/pipeline_config.yaml` to use sampled corpus:
```yaml
data:
  docs_path: /data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus_200k.jsonl
```

## Prerequisites

- Elasticsearch running on `localhost:9200`
- Python 3.7+ with elasticsearch and pyyaml packages
- ~50 GB free disk space during sampling

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't connect to ES | Start with: `docker-compose -f docker/compose.yml up -d` |
| Index already exists | Use `--delete-existing` flag |
| Out of memory | Streams are used, should be fine. Check disk space. |
| Slow sampling | Normal - 33M documents takes 15-25 min |

## After Setup

```bash
# Test the sampled corpus with a simple query
python scripts/run_pipeline_bm25.py \
    --config configs/pipeline_config.yaml \
    --query "cancer treatment"
```
