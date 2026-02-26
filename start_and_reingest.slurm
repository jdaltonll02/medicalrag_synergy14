#!/bin/bash
#SBATCH --job-name=start_es_and_reingest
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16GB
#SBATCH --qos=cpu_qos
#SBATCH --time=24:00:00
#SBATCH --output=/home/jgibson2/projects/medrag/logs2/start_es_and_reingest_%j.log
#SBATCH --error=/home/jgibson2/projects/medrag/logs2/start_es_and_reingest_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jgibson2@andrew.cmu.edu

set -e

# Configuration
PROJECT_DIR="/home/jgibson2/projects/medrag"
CONFIG_FILE="configs/pipeline_config.yaml"
OUTPUT_CORPUS="/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_round4_corpus.jsonl"

# Activate environment
cd "$PROJECT_DIR"
echo "Activating Python environment..."
source venv/bin/activate

# Start Elasticsearch
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

# Wait for Elasticsearch to be ready
sleep 5
echo "Waiting for Elasticsearch to become available..."
for i in {1..60}; do
  if curl -s http://127.0.0.1:9200 >/dev/null; then
    echo "Elasticsearch is up"
    break
  fi
  sleep 2
done

curl -s http://127.0.0.1:9200 >/dev/null || {
  echo "ERROR: Elasticsearch failed to start"
  exit 1
}

echo "Running reingestion..."
python3 scripts/reingest_sampled_corpus.py \
  --config "$CONFIG_FILE" \
  --corpus "$OUTPUT_CORPUS" \
  --delete-existing

echo "Reingestion complete."
