#!/bin/bash
#SBATCH --job-name=bioasq_pipeline
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=160GB
#SBATCH --gres=gpu:1
#SBATCH --time=10:00:00
#SBATCH --qos=normal
#SBATCH --output=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/pipeline_%j.log
#SBATCH --error=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/pipeline_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jgibson2@andrew.cmu.edu

# Full-corpus BioASQ RAG pipeline.
# Requires pre-built FAISS index (build_faiss_index.slurm).
# ES BM25 index is built fresh on local NVMe ($TMPDIR) each run — no separate ingest job needed.
#
# Set TESTSET to the BioASQ JSON for the current round before submitting.

set -euo pipefail

PROJECT_DIR="/home/jgibson2/projects/medicalrag_synergy14"
CONFIG="configs/fullpipeline.yaml"
RUNS_DIR="/data/user_data/jgibson2/bioask_pubmed_dataset/fullpipeline/runs"

# ---- Set this to the testset for the current round ----
TESTSET="${TESTSET:-/home/jgibson2/projects/medicalrag_synergy14/test_data/round_3/testset_round_3.json}"
OUTPUT="${OUTPUT:-$PROJECT_DIR/results/submission.json}"

echo "=========================================="
echo "BioASQ Full Corpus Pipeline"
echo "SLURM Job ID: $SLURM_JOB_ID"
echo "Node:         $SLURMD_NODENAME"
echo "GPUs:         $CUDA_VISIBLE_DEVICES"
echo "Config:       $CONFIG"
echo "Testset:      $TESTSET"
echo "Output:       $OUTPUT"
echo "=========================================="

cd "$PROJECT_DIR"
mkdir -p logs/slurm "$(dirname "$OUTPUT")"

export OPENAI_API_KEY="sk-FSe9sem3s0klJg7R77q4-A"
export OPENAI_ORG_ID="8bd2c6d561fa8190e42860b2a835207361d9c596262ba3541c50da670c21be13"
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export TOKENIZERS_PARALLELISM=true

echo "[$(date +%T)] Activating Python environment..."
source .venv/bin/activate
echo "Python:       $(which python)"
echo "PyTorch CUDA: $(python -c 'import torch; print(torch.cuda.is_available(), torch.version.cuda)' 2>/dev/null || echo unavailable)"

# ------------------------------------------------------------------
# Start Elasticsearch on local NVMe ($TMPDIR) — fast I/O, no NFS latency
# ------------------------------------------------------------------
export ES_HOME=$HOME/elasticsearch
export ES_DATA="$TMPDIR/es_data"
export ES_TMPDIR="$TMPDIR/es_tmp"
export ES_LOGS="$TMPDIR/es_logs"
export ES_JAVA_OPTS="-Xms16g -Xmx16g -XX:+UseG1GC -XX:G1HeapRegionSize=32m"

mkdir -p "$ES_DATA" "$ES_TMPDIR" "$ES_LOGS"

echo "[$(date +%T)] Starting Elasticsearch (data → $ES_DATA)..."
"$ES_HOME/bin/elasticsearch" \
  -Ediscovery.type=single-node \
  -Epath.data="$ES_DATA" \
  -Epath.logs="$ES_LOGS" \
  -Enetwork.host=127.0.0.1 \
  -Ehttp.port=9200 \
  -Expack.security.enabled=false \
  -Eindices.memory.index_buffer_size=20% \
  -Ethread_pool.write.queue_size=2000 &
ES_PID=$!
trap 'echo "[$(date +%T)] Stopping Elasticsearch..."; kill "$ES_PID" 2>/dev/null || true' EXIT

echo "[$(date +%T)] Waiting for Elasticsearch to be ready..."
for i in {1..90}; do
  if curl -s http://127.0.0.1:9200 >/dev/null 2>&1; then
    echo "[$(date +%T)] Elasticsearch HTTP up (attempt $i) — waiting for cluster yellow..."
    break
  fi
  sleep 2
done

curl -s http://127.0.0.1:9200 >/dev/null 2>&1 || {
  echo "WARNING: Elasticsearch failed to start — pipeline will run FAISS-only"
}

curl -sf "http://127.0.0.1:9200/_cluster/health?wait_for_status=yellow&timeout=120s" >/dev/null || {
  echo "WARNING: Cluster did not reach yellow within 120 s — proceeding anyway"
}

# ------------------------------------------------------------------
# Ingest corpus into ES (fast on local NVMe — ~40 min for full corpus)
# ------------------------------------------------------------------
echo ""
echo "[$(date +%T)] === Ingesting BM25 corpus ==="
t_ingest=$(date +%s)

python scripts/ingest_elastic.py \
  --config "$CONFIG" \
  --chunk-size 2000 \
  --force || echo "WARNING: ES ingest failed — pipeline will use FAISS-only"

echo "[$(date +%T)] Ingest done in $(( ($(date +%s) - t_ingest) / 60 ))m $(( ($(date +%s) - t_ingest) % 60 ))s"

# ------------------------------------------------------------------
# Run pipeline
# ------------------------------------------------------------------
echo ""
echo "[$(date +%T)] === Running pipeline ==="
t0=$(date +%s)

python scripts/run_hybrid_pipeline.py \
  --testset   "$TESTSET" \
  --config    "$CONFIG" \
  --output    "$OUTPUT" \
  --skip-indexing

elapsed=$(( $(date +%s) - t0 ))
echo "[$(date +%T)] Pipeline done in $(( elapsed / 60 ))m $(( elapsed % 60 ))s"

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
echo ""
echo "=========================================="
echo "COMPLETE  (Job $SLURM_JOB_ID)"
echo "Submission: $OUTPUT"
echo "=========================================="
