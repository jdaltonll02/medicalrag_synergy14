#!/bin/bash
#SBATCH --job-name=process_bioasq_data
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=16GB
#SBATCH --qos=cpu_qos
#SBATCH --time=90:00
#SBATCH --output=/home/jgibson2/projects/medrag/logs2/process_bioasq_round3_%j.log
#SBATCH --error=/home/jgibson2/projects/medrag/logs2/process_bioasq_round3_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=${EMAIL:-jgibson2@andrew.cmu.edu}

set -e

# Configuration
PROJECT_DIR="/home/jgibson2/projects/medrag"
CONFIG_FILE="configs/pipeline_config.yaml"
INPUT_CORPUS="/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl"
OUTPUT_CORPUS="/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_round3_corpus.jsonl"
SAMPLE_SIZE=300000
ROUND1_SIZE=100000
ROUND2_SIZE=100000
ROUND1_DATE="2026-01-09"
ROUND2_DATE="2026-01-22"
ROUND3_DATE="2026-02-08"
EMAIL="${1:-${EMAIL:-jgibson2@andrew.cmu.edu}}"

# Setup
echo "=========================================="
echo "BioASQ Synergy Corpus Setup (Round 3)"
echo "SLURM Job ID: $SLURM_JOB_ID"
echo "=========================================="
echo ""

# Check email parameter
if [ -z "$EMAIL" ]; then
  echo "ERROR: Email not specified!"
  echo ""
  echo "Usage: sbatch --export=EMAIL=jgibson2@andrew.cmu.edu process_300_docs.slurm"
  echo "   or: sbatch process_300_docs.slurm jgibson2@andrew.cmu.edu"
  echo ""
  exit 1
fi

echo "Email for PubMed API: $EMAIL"
echo "Project directory: $PROJECT_DIR"
echo "Config file: $CONFIG_FILE"
echo ""

# Navigate to project directory
cd "$PROJECT_DIR"

# Create logs directory if needed
mkdir -p /home/jgibson2/projects/medrag/logs

# Activate virtual environment
echo "Activating Python environment..."
source venv/bin/activate
echo "✓ Environment activated"
echo "Python: $(which python)"
echo ""

# -------------------------------------------------
# Start Elasticsearch (local-only)
# -------------------------------------------------
export ES_HOME=$HOME/elasticsearch
export ES_TMPDIR="$TMPDIR/es_tmp"
export ES_DATA="$TMPDIR/es_data"
export ES_LOGS="$TMPDIR/es_logs"
export ES_JAVA_OPTS="-Xms8g -Xmx8g"

mkdir -p "$ES_TMPDIR" "$ES_DATA" "$ES_LOGS"

echo "Starting Elasticsearch..."
$ES_HOME/bin/elasticsearch \
  -Ediscovery.type=single-node \
  -Epath.data="$ES_DATA" \
  -Epath.logs="$ES_LOGS" \
  -Enetwork.host=127.0.0.1 \
  -Ehttp.port=9200 &

# -------------------------------------------------
# Wait for Elasticsearch to be READY (not just alive)
# -------------------------------------------------
echo "Waiting for Elasticsearch to become available..."
for i in {1..60}; do
  if curl -s http://127.0.0.1:9200 >/dev/null; then
    echo "Elasticsearch is up"
    break
  fi
  sleep 2
done

# Final safety check
curl -s http://127.0.0.1:9200 >/dev/null || {
  echo "ERROR: Elasticsearch failed to start"
  exit 1
}

# Run the setup
echo "Starting 300K corpus setup..."
echo "(This will take approximately 60-80 minutes)"
echo ""

start_time=$(date +%s)

python3 scripts/sample_corpus.py \
  --input "$INPUT_CORPUS" \
  --output "$OUTPUT_CORPUS" \
  --sample-size "$SAMPLE_SIZE" \
  --round1-size "$ROUND1_SIZE" \
  --round2-size "$ROUND2_SIZE" \
  --round1-date "$ROUND1_DATE" \
  --round2-date "$ROUND2_DATE" \
  --round3-date "$ROUND3_DATE" \
  --email "$EMAIL"

python3 scripts/delete_index.py \
  --config "$CONFIG_FILE" \
  --confirm

python3 scripts/reingest_sampled_corpus.py \
  --config "$CONFIG_FILE" \
  --corpus "$OUTPUT_CORPUS" \
  --delete-existing

setup_exit_code=$?

end_time=$(date +%s)
duration=$((end_time - start_time))
minutes=$((duration / 60))
seconds=$((duration % 60))

echo ""
echo "=========================================="
if [ $setup_exit_code -eq 0 ]; then
    echo "✓ Setup completed successfully!"
    echo "Total time: ${minutes}m ${seconds}s"
    echo ""
    echo "Next steps:"
    echo "  1. Run verification: python scripts/verify_setup.py --config $CONFIG_FILE"
    echo "  2. Test retrieval with sample queries"
    echo "  3. Start pipeline on the sampled corpus"
else
    echo "✗ Setup failed with exit code $setup_exit_code"
    echo "Check logs/slurm/process_bioasq_round3_${SLURM_JOB_ID}.err for details"
fi
echo "=========================================="
echo ""

exit $setup_exit_code
