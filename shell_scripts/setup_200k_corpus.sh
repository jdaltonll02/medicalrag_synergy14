#!/bin/bash
#
# setup_200k_corpus.sh
# --------------------
# Master script to set up a 200K document corpus from both round 1 and round 2 snapshots
#
# Steps:
# 1. Sample 200K documents (100K from round 1 + 100K from round 2)
# 2. Delete existing Elasticsearch index
# 3. Reingest with sampled 200K corpus
#
# Usage:
#     ./setup_200k_corpus.sh --config configs/pipeline_config.yaml
#

set -e

# Configuration
CONFIG_FILE="configs/pipeline_config.yaml"
INPUT_CORPUS="/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_corpus.jsonl"
OUTPUT_CORPUS="/data/user_data/jgibson2/bioask_pubmed_dataset/json/pubmed_round2_corpus.jsonl"
SAMPLE_SIZE=200000
ROUND1_DATE="2026-01-09"
ROUND2_DATE="2026-01-22"
EMAIL=""
CONFIRM_DELETE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        --input)
            INPUT_CORPUS="$2"
            shift 2
            ;;
        --output)
            OUTPUT_CORPUS="$2"
            shift 2
            ;;
        --sample-size)
            SAMPLE_SIZE="$2"
            shift 2
            ;;
        --round1-date)
            ROUND1_DATE="$2"
            shift 2
            ;;
        --round2-date)
            ROUND2_DATE="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --confirm-delete)
            CONFIRM_DELETE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --config PATH          Config file (default: configs/pipeline_config.yaml)"
            echo "  --input PATH           Input corpus (default: full pubmed_corpus.jsonl)"
            echo "  --output PATH          Output corpus (default: pubmed_corpus_200k.jsonl)"
            echo "  --sample-size N        Sample size (default: 200000)"
            echo "  --round1-date DATE     Round 1 snapshot date (default: 2026-01-09)"
            echo "  --round2-date DATE     Round 2 snapshot date (default: 2026-01-22)"
            echo "  --email EMAIL          Email for PubMed API (required)"
            echo "  --confirm-delete       Skip confirmation for index deletion"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}   200K Corpus Setup Orchestration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verify email
if [ -z "$EMAIL" ]; then
    echo -e "${RED}Error: --email is required for PubMed API queries${NC}"
    echo "Usage: $0 --email jgibson2@andrew.cmu.edu [other options]"
    exit 1
fi
echo -e "${GREEN}✓ Email provided: $EMAIL${NC}"
echo ""

# Step 0: Verify files
echo -e "${YELLOW}[STEP 0] Verifying configuration...${NC}"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Config file found: $CONFIG_FILE${NC}"

if [ ! -f "$INPUT_CORPUS" ]; then
    echo -e "${RED}Error: Input corpus not found: $INPUT_CORPUS${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Input corpus found: $INPUT_CORPUS${NC}"
echo ""

# Step 1: Sample corpus
echo -e "${YELLOW}[STEP 1] Sampling 200K documents...${NC}"
echo "  - Round 1 snapshot (≤ $ROUND1_DATE): 100K documents"
echo "  - Round 2 snapshot ($ROUND1_DATE to $ROUND2_DATE): 100K documents"
echo "  - Output: $OUTPUT_CORPUS"
echo "  - Note: Fetching publication dates from PubMed API... (40-55 minutes)"
echo ""

python3 scripts/sample_corpus.py \
    --input "$INPUT_CORPUS" \
    --output "$OUTPUT_CORPUS" \
    --sample-size "$SAMPLE_SIZE" \
    --round1-date "$ROUND1_DATE" \
    --round2-date "$ROUND2_DATE" \
    --email "$EMAIL"

if [ -f "$OUTPUT_CORPUS" ]; then
    file_size=$(du -h "$OUTPUT_CORPUS" | cut -f1)
    line_count=$(wc -l < "$OUTPUT_CORPUS")
    echo -e "${GREEN}✓ Sampling complete!${NC}"
    echo "  - File: $OUTPUT_CORPUS"
    echo "  - Size: $file_size"
    echo "  - Documents: $line_count"
else
    echo -e "${RED}✗ Sampling failed!${NC}"
    exit 1
fi
echo ""

# Step 2: Delete existing index
echo -e "${YELLOW}[STEP 2] Deleting existing Elasticsearch index...${NC}"

if [ "$CONFIRM_DELETE" = true ]; then
    delete_args="--confirm"
else
    delete_args=""
fi

python3 scripts/delete_index.py \
    --config "$CONFIG_FILE" \
    $delete_args || {
    echo -e "${YELLOW}Note: Index deletion cancelled or failed. Proceeding anyway...${NC}"
}
echo ""

# Step 3: Reingest sampled corpus
echo -e "${YELLOW}[STEP 3] Reingesting 200K sampled corpus...${NC}"
echo "  - BioASQ Round 1 snapshot date: $ROUND1_DATE"
echo "  - BioASQ Round 2 snapshot date: $ROUND2_DATE"
echo ""

python3 scripts/reingest_sampled_corpus.py \
    --config "$CONFIG_FILE" \
    --corpus "$OUTPUT_CORPUS" \
    --delete-existing

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Summary:"
echo "  - Sampled corpus: $OUTPUT_CORPUS"
echo "  - Documents: $SAMPLE_SIZE (100K round 1 + 100K round 2)"
echo "  - Ingested into Elasticsearch"
echo ""
echo "Next steps:"
echo "  1. Test retrieval with sample queries"
echo "  2. Run pipeline on the sampled corpus"
echo "  3. Evaluate results"
echo ""
