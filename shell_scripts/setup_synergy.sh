#!/bin/bash
# BioASQ Synergy 2026 - Quick Start Script
# Run this to prepare for Round 1 submission

set -e

PROJECT_ROOT="/home/Jdalton/codespace/medrag"
cd "$PROJECT_ROOT"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║       BioASQ Synergy 2026 - Quick Start Setup                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check environment
echo "📋 Step 1: Checking environment..."
if [ ! -f ".env.cmu" ]; then
    echo "⚠️  .env.cmu not found. Creating default..."
    cat > .env.cmu << 'EOF'
export OPENAI_API_KEY="sk-v4B4KHdez6V4sALNjvvv-A"
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu/openai/deployments/gpt-4/chat/completions"
export PYTHONPATH="/home/Jdalton/codespace/medrag"
EOF
    echo "✓ Created .env.cmu"
fi

# Step 2: Load credentials
echo ""
echo "🔐 Step 2: Loading CMU OpenAI Gateway credentials..."
source .env.cmu
echo "✓ Credentials loaded"

# Step 3: Check Python environment
echo ""
echo "🐍 Step 3: Checking Python environment..."
python3 -c "import torch; print(f'✓ PyTorch version: {torch.__version__}')" || echo "⚠️  PyTorch not available"
python3 -c "import transformers; print(f'✓ Transformers version: {transformers.__version__}')" || echo "⚠️  Transformers not available"
python3 -c "import yaml; print(f'✓ YAML available')" || echo "⚠️  YAML not available"

# Step 4: Check data files
echo ""
echo "📁 Step 4: Checking data files..."
for round in 1 2 3 4; do
    if [ -f "data/test/testset_${round}.json" ]; then
        echo "  ✓ testset_${round}.json found"
    else
        echo "  ⚠️  testset_${round}.json NOT found"
    fi
done

# Step 5: Create output directory
echo ""
echo "📂 Step 5: Preparing output directory..."
mkdir -p results
echo "✓ results/ directory ready"

# Step 6: Show submission commands
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    READY FOR SUBMISSION                        ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Round 1 (January 12-15, 2026):"
echo "   python3 scripts/run_synergy_pipeline.py \\"
echo "     --round 1 \\"
echo "     --config configs/pipeline_config.yaml \\"
echo "     --email jgibson2@andrew.cmu.edu \\"
echo "     --output results"
echo ""
echo "📝 Round 2 (January 26-29, 2026):"
echo "   python3 scripts/run_synergy_pipeline.py \\"
echo "     --round 2 \\"
echo "     --config configs/pipeline_config.yaml \\"
echo "     --email jgibson2@andrew.cmu.edu \\"
echo "     --feedback data/feedback/feedback_accompanying_round_1.json \\"
echo "     --output results"
echo ""
echo "📝 Quick Test (with stub LLM - no API required):"
echo "   python3 scripts/run_synergy_pipeline.py \\"
echo "     --round 1 \\"
echo "     --config configs/pipeline_config.yaml \\"
echo "     --email jgibson2@andrew.cmu.edu \\"
echo "     --use-stub-llm \\"
echo "     --output results"
echo ""
echo "📚 Documentation:"
echo "   • SYNERGY_2026.md - Complete guide"
echo "   • SYNERGY_IMPLEMENTATION.md - Implementation summary"
echo "   • SYNERGY_ARCHITECTURE.md - System architecture"
echo ""
echo "🎯 Key files:"
echo "   • src/core/synergy_formatter.py - Snippet extraction & formatting"
echo "   • src/core/answer_generator.py - Answer generation"
echo "   • src/pipeline/synergy_pipeline.py - Main pipeline"
echo "   • scripts/run_synergy_pipeline.py - Entry point"
echo ""
echo "✅ Setup complete! Ready to submit."
