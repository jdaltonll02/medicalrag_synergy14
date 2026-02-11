# LLM Integration Guide: OpenAI vs Gemini

This document outlines the prerequisites and dependencies for using different LLM providers in the MedRAG pipeline.

## Quick Start

### OpenAI (Current Default)
```bash
export OPENAI_API_KEY="sk-proj-your-key-here"
export OPENAI_BASE_URL="https://api.openai.com"  # Optional, for custom endpoints
export OPENAI_PROJECT_ID="proj_your-id"          # Optional, for OpenAI projects
```

Then in `configs/pipeline_config.yaml`:
```yaml
llm:
  provider: openai
  model: gpt-4o-mini
```

### Google Gemini (Alternative)
```bash
export GOOGLE_API_KEY="AIzaSyD_your-api-key-here"
export GOOGLE_CLOUD_PROJECT="your-gcp-project"  # Optional, for GCP integration
```

Then in `configs/pipeline_config.yaml`:
```yaml
llm:
  provider: gemini
  model: gemini-2.0-flash  # or gemini-1.5-pro, etc.
```

---

## OpenAI Setup

### Prerequisites
- OpenAI API account (https://platform.openai.com)
- Valid API key with gpt-4 or gpt-4o access
- For CMU AI Gateway: CMU credentials

### Python Dependencies
```bash
pip install openai>=1.0.0
```

### Environment Variables
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | ✅ Yes | `sk-proj-...` | Authentication key |
| `OPENAI_BASE_URL` | ❌ No | `https://api.openai.com` | API endpoint (custom gateways) |
| `OPENAI_PROJECT_ID` | ❌ No | `proj_DMiMpLL...` | OpenAI project ID |

### Configuration File Options
```yaml
llm:
  provider: openai                # LLM provider name
  model: gpt-4o-mini              # Model to use
  temperature: 0.7                # Sampling temperature (0-2)
  max_tokens: 1024                # Max output length
  api_key: null                   # Uses OPENAI_API_KEY env var
  base_url: null                  # Uses OPENAI_BASE_URL env var
  project_id: null                # Uses OPENAI_PROJECT_ID env var
  prompt_for_key: true            # Prompt for key interactively
  use_keyring: true               # Store key in system keyring
  save_to_keyring: false          # Auto-save key after prompt
```

### Available Models
- `gpt-4o` - Latest, most capable
- `gpt-4o-mini` - Faster, cheaper (recommended for BioASQ)
- `gpt-4-turbo` - Previous generation
- `gpt-4` - Older, slower
- `gpt-3.5-turbo` - Basic, very fast

### Cost Estimation (OpenAI)
- Input: ~$0.0003 per 1K tokens
- Output: ~$0.0006 per 1K tokens
- For 200K documents + 63 questions: **~$5-15 estimate**

---

## Google Gemini Setup

### Prerequisites
- Google Cloud account (https://cloud.google.com)
- Google AI Studio API key OR GCP project with Generative AI API enabled
- Billing enabled on GCP account

### Python Dependencies
```bash
pip install google-generativeai>=0.3.0
```

### Obtaining API Key

#### Option 1: Google AI Studio (Simpler, Free Tier Available)
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key to `GOOGLE_API_KEY` environment variable
4. ✅ No GCP project needed
5. ✅ Free tier: 15 requests per minute

#### Option 2: Google Cloud Platform (More Control)
1. Create GCP project: https://console.cloud.google.com/projectcreate
2. Enable Generative AI API:
   ```bash
   gcloud services enable generativeai.googleapis.com
   ```
3. Create service account:
   ```bash
   gcloud iam service-accounts create medrag-gemini \
     --display-name="MedRAG Gemini Access"
   ```
4. Create API key:
   ```bash
   gcloud services api-keys create \
     --display-name="MedRAG Gemini" \
     --api-target=generativeai.googleapis.com
   ```
5. Export the key

### Environment Variables
| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `GOOGLE_API_KEY` | ✅ Yes | `AIzaSyD_...` | API key from Google AI Studio or GCP |
| `GOOGLE_CLOUD_PROJECT` | ❌ No | `my-gcp-project` | GCP project ID for billing |

### Configuration File Options
```yaml
llm:
  provider: gemini                # LLM provider name
  model: gemini-2.0-flash         # Model to use (recommended)
  temperature: 0.7                # Sampling temperature (0-2)
  max_tokens: 1024                # Max output length
  api_key: null                   # Uses GOOGLE_API_KEY env var
  project_id: null                # Uses GOOGLE_CLOUD_PROJECT env var
```

### Available Models
- `gemini-2.0-flash` - Latest, fastest, best for BioASQ (recommended)
- `gemini-1.5-pro` - More capable, slower, higher cost
- `gemini-1.5-flash` - Faster version of 1.5
- `gemini-pro` - Original model

### Cost Estimation (Gemini)
- Free tier: 15 requests/minute, 32K tokens/minute
- Paid tier:
  - Input: ~$0.075 per 1M tokens
  - Output: ~$0.30 per 1M tokens
- For 200K documents + 63 questions: **~$10-25 estimate** (similar to OpenAI)

### Rate Limits
- Free tier: 15 RPM, 32K tokens/min
- Paid tier: Higher limits, consult GCP docs
- Recommendation: Use within free tier limits for testing

---

## Stub/Offline Mode

For testing without API calls:

```yaml
llm:
  provider: stub
```

Or via environment variable:
```bash
export LLM_PROVIDER=stub
```

The Stub LLM returns mock answers without consuming API tokens.

---

## Implementation Details

### Client Classes

#### OpenAIClient (`src/llm/openai_client.py`)
- **Methods:**
  - `generate(prompt, system_prompt, temperature, max_tokens)` - Basic generation
  - `generate_with_context(query, context_documents, system_prompt)` - RAG generation
- **Features:**
  - Environment variable resolution
  - Custom endpoint support (CMU AI Gateway)
  - Keyring integration for secure key storage
  - Comprehensive error handling

#### GeminiClient (`src/llm/gemini_client.py`)
- **Methods:**
  - `generate(prompt, system_prompt, temperature, max_tokens)` - Basic generation
  - `generate_with_context(query, context_documents, system_prompt)` - RAG generation
- **Features:**
  - Environment variable resolution
  - Automatic API initialization
  - Detailed logging and error messages
  - Same interface as OpenAIClient for drop-in replacement

### Pipeline Integration

All pipelines support provider selection:

```python
llm_config = config.get("llm", {})
provider = llm_config.get("provider", "openai")

if provider == "gemini":
    llm = GeminiClient(...)
elif provider == "openai":
    llm = OpenAIClient(...)
else:  # stub
    llm = StubLLM()
```

---

## Switching Providers

### Option 1: Config File Only
```yaml
# Change in configs/pipeline_config.yaml
llm:
  provider: gemini  # or "openai"
  model: gemini-2.0-flash
```

### Option 2: Environment Variable Override
```bash
# These will override config file settings
export GOOGLE_API_KEY="your-key"
export LLM_PROVIDER=gemini

python scripts/run_hybrid_pipeline.py \
  --config configs/pipeline_config.yaml \
  ...
```

### Option 3: SLURM Job Script
```bash
#!/bin/bash
#SBATCH --job-name=medrag-gemini

# Set up Gemini API
export GOOGLE_API_KEY="your-key"
export GOOGLE_CLOUD_PROJECT="your-project"

# Run with Gemini (via config)
python scripts/run_hybrid_pipeline.py \
  --config configs/pipeline_config.yaml \
  ...
```

---

## Troubleshooting

### OpenAI Issues

**Problem:** `401 Unauthorized`
- **Solution:** Check `OPENAI_API_KEY` is set correctly
  ```bash
  echo $OPENAI_API_KEY | head -c 10  # Should show first 10 chars
  ```

**Problem:** `Invalid proxy server token`
- **Solution:** Key is expired or invalid, request new one from OpenAI dashboard

**Problem:** `RateLimitError`
- **Solution:** Wait and retry, or upgrade to higher tier

### Gemini Issues

**Problem:** `ModuleNotFoundError: No module named 'google.generativeai'`
- **Solution:** Install the package
  ```bash
  pip install google-generativeai>=0.3.0
  ```

**Problem:** `APIError: Invalid API key`
- **Solution:** Verify `GOOGLE_API_KEY` is set:
  ```bash
  echo $GOOGLE_API_KEY | head -c 10
  ```

**Problem:** `APIError: 429 Too Many Requests`
- **Solution:** Hit rate limit
  - Free tier: 15 requests per minute
  - Upgrade to paid tier or implement request throttling

**Problem:** `APIError: 503 Service Unavailable`
- **Solution:** Google's API is temporarily down, retry in a few minutes

---

## Performance Comparison

| Metric | OpenAI (gpt-4o-mini) | Gemini (2.0-flash) |
|--------|----------------------|-------------------|
| **Speed (queries/min)** | 3-5 | 10-15 |
| **Latency (avg ms)** | 800-1200 | 400-600 |
| **Cost per 1M tokens** | $0.075 (in) / $0.30 (out) | $0.075 (in) / $0.30 (out) |
| **Quality (BioASQ domain)** | Excellent | Very Good |
| **Setup Complexity** | Low | Medium (GCP) |
| **Free Tier** | Limited | 15 RPM, 32K tokens/min |

---

## Best Practices

1. **Use Gemini for testing/development**: Free tier available, faster
2. **Use OpenAI for production**: More stable, better domain-specific performance
3. **Set API keys in environment, not code**: Use SLURM scripts or .env files
4. **Monitor API usage**: Check OpenAI dashboard or GCP console
5. **Implement backoff/retry logic**: Both APIs have rate limits
6. **Test with small batches first**: Verify setup before running full pipeline

---

## Running the Full Pipeline

### With OpenAI
```bash
export OPENAI_API_KEY="your-key"
cd /home/jgibson2/projects/medrag
source venv/bin/activate

python scripts/run_hybrid_pipeline.py \
  --round 1 \
  --dataset_root /data/user_data/jgibson2/bioask_pubmed_dataset/json \
  --testset_root /home/jgibson2/projects/medrag/test_data \
  --config /home/jgibson2/projects/medrag/configs/pipeline_config.yaml \
  --output /home/jgibson2/projects/medrag/results1
```

### With Gemini
```bash
export GOOGLE_API_KEY="your-key"
cd /home/jgibson2/projects/medrag
source venv/bin/activate

# Update config to use Gemini
sed -i 's/provider: openai/provider: gemini/' configs/pipeline_config.yaml

python scripts/run_hybrid_pipeline.py \
  --round 1 \
  --dataset_root /data/user_data/jgibson2/bioask_pubmed_dataset/json \
  --testset_root /home/jgibson2/projects/medrag/test_data \
  --config /home/jgibson2/projects/medrag/configs/pipeline_config.yaml \
  --output /home/jgibson2/projects/medrag/results_gemini
```

---

## Additional Resources

- OpenAI Docs: https://platform.openai.com/docs
- Google Gemini Docs: https://ai.google.dev/docs
- Google Cloud Docs: https://cloud.google.com/docs
- API Status: 
  - OpenAI: https://status.openai.com
  - Google Cloud: https://status.cloud.google.com
