#!/bin/bash
#SBATCH --job-name=process_bioasq_data
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=16GB
#SBATCH --qos=cpu_qos
#SBATCH --time=90:00
#SBATCH --output=logs/slurm/process_bioasq_round2_%j.log
#SBATCH --error=logs/slurm/process_bioasq_round2_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=${EMAIL:-jgibson2@andrew.cmu.edu}

set -e

# Configuration
PROJECT_DIR="/home/jgibson2/projects/medrag"
CONFIG_FILE="configs/pipeline_config.yaml"
EMAIL="${1:-$EMAIL}"

# Setup
echo "=========================================="
echo "BioASQ Synergy Corpus Setup"
echo "SLURM Job ID: $SLURM_JOB_ID"
echo "=========================================="
echo ""

# Check email parameter
if [ -z "$EMAIL" ]; then
    echo "ERROR: Email not specified!"
    echo ""
    echo "Usage: sbatch --export=EMAIL=jgibson2@andrew.cmu.edu process_200_docs.slurm"
    echo "   or: sbatch process_200_docs.slurm jgibson2@andrew.cmu.edu"
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
echo "Starting 200K corpus setup..."
echo "(This will take approximately 50-60 minutes)"
echo ""

start_time=$(date +%s)

./setup_200k_corpus.sh \
    --config "$CONFIG_FILE" \
    --email "$EMAIL" \
    --confirm-delete

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
    echo "Check logs/slurm/bioasq_200k_setup_${SLURM_JOB_ID}.err for details"
fi
echo "=========================================="
echo ""

exit $setup_exit_code
