#!/bin/bash
#SBATCH --job-name=start_elasticsearch
#SBATCH --partition=cpu
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8GB
#SBATCH --qos=cpu_qos
#SBATCH --time=48:00:00
#SBATCH --output=/home/jgibson2/projects/medrag/logs2/elasticsearch_%j.log
#SBATCH --error=/home/jgibson2/projects/medrag/logs2/elasticsearch_%j.err
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=jgibson2@andrew.cmu.edu

set -e

# Configuration
export ES_HOME=$HOME/elasticsearch
export ES_TMPDIR="$TMPDIR/es_tmp"
export ES_DATA="$TMPDIR/es_data"
export ES_LOGS="$TMPDIR/es_logs"
export ES_JAVA_OPTS="-Xms4g -Xmx4g"

mkdir -p "$ES_TMPDIR" "$ES_DATA" "$ES_LOGS"

cd "$ES_HOME"

echo "Starting Elasticsearch..."
$ES_HOME/bin/elasticsearch \
  -Ediscovery.type=single-node \
  -Epath.data="$ES_DATA" \
  -Epath.logs="$ES_LOGS" \
  -Enetwork.host=127.0.0.1 \
  -Ehttp.port=9200


curl -X DELETE 'http://localhost:9200/medical_docs_3'
