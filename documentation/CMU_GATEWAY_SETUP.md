# CMU AI Gateway Setup Guide

## Problem Fixed

**Error:** `HTTP/1.1 404 Not Found` at `https://ai-gateway.andrew.cmu.edu/chat/chat/completions`

**Root Cause:** The OpenAI client was appending `/chat/completions` to the base URL, creating the wrong path.

**Solution:** Normalize the base URL to include `/v1` so the final endpoint is correct.

## Correct Setup

### 1. Set Environment Variables

```bash
# Required: Your OpenAI API key (from CMU or your OpenAI account)
export OPENAI_API_KEY="sk-your-key-here"

# Required: CMU AI Gateway URL (any of these formats work)
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu"
# OR
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu/chat"
# OR  
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu/v1"

# Optional: OpenAI project ID (if using OpenAI directly)
export OPENAI_PROJECT_ID="your-project-id"
```

### 2. URL Normalization (Automatic)

The updated `openai_client.py` now automatically normalizes CMU gateway URLs:

```
Input:  https://ai-gateway.andrew.cmu.edu
        OR https://ai-gateway.andrew.cmu.edu/chat
        OR https://ai-gateway.andrew.cmu.edu/chat/v1

Output: https://ai-gateway.andrew.cmu.edu/v1

Final Endpoint: https://ai-gateway.andrew.cmu.edu/v1/chat/completions ✓
```

### 3. Verify Configuration

```bash
# Check environment variables
echo "OPENAI_API_KEY: ${OPENAI_API_KEY:0:30}..."
echo "OPENAI_BASE_URL: $OPENAI_BASE_URL"
echo "OPENAI_PROJECT_ID: ${OPENAI_PROJECT_ID:-'(not set)'}"
```

## Running with CMU Gateway

```bash
# Make sure you're in the venv
source venv/bin/activate

# Set your credentials
export OPENAI_API_KEY="sk-your-key"
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu"

# Run the pipeline
python scripts/run_hybrid_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --max_questions 1 \
  --output test_results
```

## Debugging 404 Errors

If you still get `404 Not Found`, check:

1. **API Key Valid?**
   ```bash
   # Test with a simple curl request
   curl -X POST https://ai-gateway.andrew.cmu.edu/v1/chat/completions \
     -H "Authorization: Bearer $OPENAI_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"hello"}]}'
   ```

2. **Base URL Set?**
   ```bash
   # Verify it's not empty
   [[ -z "$OPENAI_BASE_URL" ]] && echo "ERROR: Base URL not set" || echo "OK: $OPENAI_BASE_URL"
   ```

3. **Check Logs**
   ```bash
   # Look for "[OPENAI]" initialization messages
   python scripts/run_hybrid_pipeline.py ... 2>&1 | grep OPENAI
   ```

## URL Mapping Reference

| Input URL | Normalized | Final Endpoint |
|-----------|-----------|----------------|
| `https://ai-gateway.andrew.cmu.edu` | `/v1` | `/v1/chat/completions` ✓ |
| `https://ai-gateway.andrew.cmu.edu/` | `/v1` | `/v1/chat/completions` ✓ |
| `https://ai-gateway.andrew.cmu.edu/chat` | `/v1` | `/v1/chat/completions` ✓ |
| `https://api.openai.com` | (no change) | `/v1/chat/completions` ✓ |

## Code Changes

File: `src/llm/openai_client.py`

The `_initialize_client()` method now includes automatic CMU gateway URL normalization:

```python
# Handle CMU AI Gateway URL normalization
if base_url and "ai-gateway.andrew.cmu.edu" in base_url:
    base_url = base_url.rstrip("/")
    if base_url.endswith("/chat"):
        base_url = base_url[:-5]
    if not base_url.endswith("/v1"):
        base_url = base_url + "/v1"
```

This ensures the OpenAI client creates the correct endpoint path.

## Support

For CMU gateway issues, contact:
- CMU AI Services: ai-gateway@cmu.edu
- OpenAI Support: https://help.openai.com

For MedRAG issues, check:
- [LLM_INTEGRATION_GUIDE.md](LLM_INTEGRATION_GUIDE.md)
- [LLM_QUICK_REFERENCE.md](LLM_QUICK_REFERENCE.md)
