#!/bin/bash
#SBATCH --job-name=bioasq_build_faiss
#SBATCH --partition=general
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=160GB
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00
#SBATCH --qos=normal
#SBATCH --output=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/build_faiss_%j.log
#SBATCH --error=/home/jgibson2/projects/medicalrag_synergy14/logs/slurm/build_faiss_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=rabiakalimat02@gmail.com

# Encode the full PubMed corpus with MedCPT article encoder and build FAISS index.
# GPU required for encoding. Runs independently from ES ingestion.
#
# Batch size defaults to 256 (A100-80GB). Override with:
#   sbatch --export=ENCODE_BATCH_SIZE=128 build_faiss_index.slurm  (V100-32GB)

set -euo pipefail

PROJECT_DIR="/home/jgibson2/projects/medicalrag_synergy14"
CONFIG="configs/fullpipeline.yaml"
RUNS_DIR="/data/user_data/jgibson2/bioask_pubmed_dataset/fullpipeline/runs"
ENCODE_BATCH_SIZE="${ENCODE_BATCH_SIZE:-256}"
EMBEDDINGS="$RUNS_DIR/embeddings.npy"

echo "=========================================="
echo "BioASQ Encode + Build FAISS"
echo "SLURM Job ID: $SLURM_JOB_ID"
echo "Node:         $SLURMD_NODENAME"
echo "GPUs:         $CUDA_VISIBLE_DEVICES"
echo "CPUs:         $SLURM_CPUS_PER_TASK"
echo "Batch size:   $ENCODE_BATCH_SIZE"
echo "Runs dir:     $RUNS_DIR"
echo "=========================================="

cd "$PROJECT_DIR"
mkdir -p logs/slurm "$RUNS_DIR"

# ------------------------------------------------------------------
# Performance environment
# ------------------------------------------------------------------
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export NUMEXPR_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export CUDA_LAUNCH_BLOCKING=0
export TOKENIZERS_PARALLELISM=true

echo "[$(date +%T)] Activating Python environment..."
source .venv/bin/activate
echo "Python: $(which python)"
echo "PyTorch CUDA: $(python -c 'import torch; print(torch.cuda.is_available(), torch.version.cuda)' 2>/dev/null || echo unavailable)"

# ------------------------------------------------------------------
# Step 1 — Encode corpus with MedCPT article encoder
# Skipped automatically if embeddings.npy already exists.
# ------------------------------------------------------------------
echo ""
echo "[$(date +%T)] === Step 1: Document encoding ==="
if [[ -f "$EMBEDDINGS" ]]; then
  echo "[SKIP] $EMBEDDINGS already exists — skipping encode step"
else
  echo "[$(date +%T)] Encoding (GPU, batch=$ENCODE_BATCH_SIZE)..."
  t0=$(date +%s)

  ENCODE_TMP="$TMPDIR/encode_scratch"
  mkdir -p "$ENCODE_TMP"

  python scripts/encode_documents.py \
    --config "$CONFIG" \
    --output-dir "$RUNS_DIR" \
    --tmp-dir "$ENCODE_TMP" \
    --batch-size "$ENCODE_BATCH_SIZE"

  elapsed=$(( $(date +%s) - t0 ))
  echo "[$(date +%T)] Encoding done in $(( elapsed / 60 ))m $(( elapsed % 60 ))s"
fi

# ------------------------------------------------------------------
# Step 2 — Build FAISS index from embeddings
# GPU used for add(), result saved as CPU-portable index.
# ------------------------------------------------------------------
echo ""
echo "[$(date +%T)] === Step 2: Build FAISS index (GPU + $SLURM_CPUS_PER_TASK threads) ==="
t0=$(date +%s)

python scripts/build_faiss_index.py \
  --config "$CONFIG" \
  --gpu

elapsed=$(( $(date +%s) - t0 ))
echo "[$(date +%T)] FAISS build done in $(( elapsed / 60 ))m $(( elapsed % 60 ))s"

# ------------------------------------------------------------------
# Done
# ------------------------------------------------------------------
echo ""
echo "=========================================="
echo "Encode + FAISS COMPLETE  (Job $SLURM_JOB_ID)"
echo "Embeddings: $RUNS_DIR/embeddings.npy"
echo "Doc IDs:    $RUNS_DIR/doc_ids.json"
echo "FAISS:      $RUNS_DIR/faiss.index"
echo "=========================================="
