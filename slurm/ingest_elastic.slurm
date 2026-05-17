#!/bin/bash
#SBATCH --job-name=bioasq_ingest_es
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32GB
#SBATCH --qos=cpu_qos
#SBATCH --time=06:00:00
#SBATCH --output=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/ingest_es_%j.log
#SBATCH --error=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/ingest_es_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=igtechacademy02@gmail.com

# Ingest the full PubMed corpus into Elasticsearch (BM25 index).
# CPU-only — no GPU needed. ES daemon lives and dies within this job.
# ES data written to $TMPDIR (local NVMe) for fast bulk I/O.

set -euo pipefail

PROJECT_DIR="/home/jgibson2/projects/medicalrag_synergy14"
CONFIG="configs/fullpipeline.yaml"

echo "=========================================="
echo "BioASQ ES Ingestion"
echo "SLURM Job ID: $SLURM_JOB_ID"
echo "Node:         $SLURMD_NODENAME"
echo "=========================================="

cd "$PROJECT_DIR"
mkdir -p logs/slurm

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
ulimit -n 65536

echo "[$(date +%T)] Activating Python environment..."
source .venv/bin/activate

# ------------------------------------------------------------------
# Start Elasticsearch — data on $TMPDIR (local NVMe, not NFS)
# ------------------------------------------------------------------
export ES_HOME=$HOME/elasticsearch
export ES_TMPDIR="$TMPDIR/es_tmp"
export ES_DATA="/data/user_data/jgibson2/bioask_pubmed_dataset/fullpipeline/es_data"
export ES_LOGS="$TMPDIR/es_logs"
export ES_JAVA_OPTS="-Xms16g -Xmx16g -XX:+UseG1GC -XX:G1HeapRegionSize=32m"

mkdir -p "$ES_TMPDIR" "$ES_DATA" "$ES_LOGS"

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

echo "[$(date +%T)] Waiting for Elasticsearch to be ready..."
for i in {1..90}; do
  if curl -s http://127.0.0.1:9200 >/dev/null 2>&1; then
    echo "[$(date +%T)] Elasticsearch HTTP up (attempt $i) — waiting for cluster yellow..."
    break
  fi
  sleep 2
done

curl -s http://127.0.0.1:9200 >/dev/null 2>&1 || {
  echo "ERROR: Elasticsearch failed to start after 180 s"
  exit 1
}

# Wait for cluster to reach yellow (all primary shards assigned, fully initialized)
curl -sf "http://127.0.0.1:9200/_cluster/health?wait_for_status=yellow&timeout=120s" >/dev/null || {
  echo "WARNING: Cluster did not reach yellow within 120 s — proceeding anyway"
}

# ------------------------------------------------------------------
# Ingest
# ------------------------------------------------------------------
echo "[$(date +%T)] Starting corpus ingestion..."
t0=$(date +%s)

python scripts/ingest_elastic.py \
  --config "$CONFIG" \
  --chunk-size 2000 \
  --force

elapsed=$(( $(date +%s) - t0 ))
echo "[$(date +%T)] Ingestion done in $(( elapsed / 60 ))m $(( elapsed % 60 ))s"

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
echo ""
echo "=========================================="
echo "ES Ingestion COMPLETE  (Job $SLURM_JOB_ID)"
echo "=========================================="

kill "$ES_PID" 2>/dev/null || true
