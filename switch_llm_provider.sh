#!/bin/bash
# Switch LLM provider for MedRAG pipeline

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/configs/pipeline_config.yaml"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_help() {
    echo "Usage: $0 [openai|gemini|stub]"
    echo ""
    echo "Switch between LLM providers for the MedRAG pipeline"
    echo ""
    echo "Providers:"
    echo "  openai  - OpenAI GPT models (default, requires OPENAI_API_KEY)"
    echo "  gemini  - Google Gemini (requires GOOGLE_API_KEY)"
    echo "  stub    - Offline stub for testing"
    echo ""
    echo "Examples:"
    echo "  $0 gemini    # Switch to Gemini"
    echo "  $0 openai    # Switch to OpenAI"
    echo "  $0 stub      # Switch to offline mode"
}

check_env_vars() {
    local provider=$1
    
    case "$provider" in
        openai)
            if [ -z "$OPENAI_API_KEY" ]; then
                echo -e "${YELLOW}⚠ OPENAI_API_KEY not set${NC}"
                echo "Set it with: export OPENAI_API_KEY='sk-proj-...'"
                return 1
            fi
            echo -e "${GREEN}✓ OPENAI_API_KEY is set${NC}"
            ;;
        gemini)
            if [ -z "$GOOGLE_API_KEY" ]; then
                echo -e "${YELLOW}⚠ GOOGLE_API_KEY not set${NC}"
                echo "Get it from: https://aistudio.google.com/app/apikey"
                echo "Set it with: export GOOGLE_API_KEY='AIzaSyD_...'"
                return 1
            fi
            echo -e "${GREEN}✓ GOOGLE_API_KEY is set${NC}"
            ;;
        stub)
            echo -e "${GREEN}✓ Stub mode (no API key needed)${NC}"
            ;;
    esac
    return 0
}

switch_provider() {
    local provider=$1
    local model=""
    
    case "$provider" in
        openai)
            model="gpt-4o-mini"
            ;;
        gemini)
            model="gemini-2.0-flash"
            ;;
        stub)
            model="stub"
            ;;
        *)
            echo -e "${RED}✗ Unknown provider: $provider${NC}"
            return 1
            ;;
    esac
    
    # Update config file using sed
    sed -i "s/  provider: .*/  provider: $provider/" "$CONFIG_FILE"
    sed -i "s/  model: .*/  model: $model/" "$CONFIG_FILE" || true
    
    echo -e "${GREEN}✓ Switched to $provider${NC}"
    echo -e "${BLUE}Config updated:${NC}"
    echo "  Provider: $provider"
    echo "  Model: $model"
}

verify_switch() {
    local provider=$1
    local actual_provider=$(grep "^\s*provider:" "$CONFIG_FILE" | awk '{print $2}')
    
    if [ "$actual_provider" = "$provider" ]; then
        echo -e "${GREEN}✓ Verification passed${NC}"
        return 0
    else
        echo -e "${RED}✗ Verification failed${NC}"
        echo "Expected: $provider, Got: $actual_provider"
        return 1
    fi
}

main() {
    if [ -z "$1" ]; then
        print_help
        exit 0
    fi
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}✗ Config file not found: $CONFIG_FILE${NC}"
        exit 1
    fi
    
    local provider=$1
    
    echo -e "${BLUE}=== MedRAG LLM Provider Switch ===${NC}"
    echo "Target provider: $provider"
    echo ""
    
    # Check environment variables
    echo -e "${BLUE}Checking environment variables...${NC}"
    if ! check_env_vars "$provider"; then
        echo -e "${YELLOW}Warning: API key not set, but continuing with config update${NC}"
    fi
    echo ""
    
    # Switch provider
    echo -e "${BLUE}Updating configuration...${NC}"
    if ! switch_provider "$provider"; then
        exit 1
    fi
    echo ""
    
    # Verify
    echo -e "${BLUE}Verifying changes...${NC}"
    if ! verify_switch "$provider"; then
        exit 1
    fi
    echo ""
    
    echo -e "${GREEN}=== All done! ===${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review the updated config: $CONFIG_FILE"
    echo "2. Run the pipeline:"
    echo "   cd $(dirname $CONFIG_FILE)/.."
    echo "   source venv/bin/activate"
    echo "   python scripts/run_hybrid_pipeline.py --config $CONFIG_FILE --round 1 ..."
}

# Handle help flag
if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    print_help
    exit 0
fi

main "$@"
