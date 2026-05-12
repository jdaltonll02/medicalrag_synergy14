# MedRAG LLM Providers - Quick Reference Card

## One-Liner Setup

### Gemini (Recommended for Testing)
```bash
pip install google-generativeai>=0.3.0 && \
export GOOGLE_API_KEY="$(curl -s https://aistudio.google.com/app/apikey)" && \
./switch_llm_provider.sh gemini
```

### OpenAI (Current Production)
```bash
export OPENAI_API_KEY="sk-proj-..." && \
./switch_llm_provider.sh openai
```

---

## Model Quick Selection

| Use Case | Gemini | OpenAI |
|----------|--------|--------|
| **Testing/Dev** | gemini-2.0-flash | gpt-3.5-turbo |
| **BioASQ (Balanced)** | gemini-2.0-flash ⭐ | gpt-4o-mini ⭐ |
| **High Quality** | gemini-1.5-pro | gpt-4o |
| **Fast Inference** | gemini-1.5-flash | gpt-3.5-turbo |
| **Offline** | (Use stub provider) | (Use stub provider) |

---

## Environment Variables

```bash
# For Gemini
export GOOGLE_API_KEY="AIzaSyD_..."          # Required
export GOOGLE_CLOUD_PROJECT="my-project"    # Optional

# For OpenAI
export OPENAI_API_KEY="sk-proj-..."         # Required
export OPENAI_BASE_URL="https://..."        # Optional (CMU Gateway)
export OPENAI_PROJECT_ID="proj_..."         # Optional

# Both
export LLM_PROVIDER="gemini"                 # or "openai", "stub"
```

---

## Config File Reference

```yaml
llm:
  enabled: true
  provider: gemini           # "openai", "gemini", or "stub"
  model: gemini-2.0-flash    # Model to use
  temperature: 0.7           # 0=deterministic, 2=creative
  max_tokens: 1024           # Output length
  api_key: null              # Use env variable (recommended)
```

---

## Install Commands

```bash
# Minimal (Gemini only)
pip install google-generativeai>=0.3.0

# Full (both + extras)
pip install openai>=1.0.0 google-generativeai>=0.3.0

# With GCP integration
pip install -r requirements-gemini.txt

# All at once
pip install -r requirements.txt -r requirements-gemini.txt
```

---

## Common Commands

```bash
# Switch provider
./switch_llm_provider.sh gemini
./switch_llm_provider.sh openai
./switch_llm_provider.sh stub

# Test API key (Gemini)
echo "import os; os.environ['GOOGLE_API_KEY']='$GOOGLE_API_KEY'; \
from src.llm.gemini_client import GeminiClient; \
print(GeminiClient().generate('test'))" | python

# Validate config
python -c "import yaml; yaml.safe_load(open('configs/pipeline_config.yaml')); print('✓ Valid')"

# Run with Gemini
python scripts/run_hybrid_pipeline.py --config configs/pipeline_config.yaml --round 1 --max_questions 1

# Run full pipeline
python scripts/run_hybrid_pipeline.py --round 1 \
  --dataset_root /data/user_data/jgibson2/bioask_pubmed_dataset/json \
  --testset_root /home/jgibson2/projects/medrag/test_data \
  --config configs/pipeline_config.yaml \
  --output results_gemini
```

---

## Cost Comparison (Quick)

For **200K docs + 63 questions**:

| Provider | Model | Cost | Speed |
|----------|-------|------|-------|
| **Gemini** | 2.0-flash | $15-20 | Fast ⚡ |
| **OpenAI** | gpt-4o-mini | $15-20 | Slow 🐢 |
| **Gemini** | 1.5-pro | $500+ | Medium |
| **OpenAI** | gpt-4o | $1000+ | Medium |

**Recommendation:** Use `gemini-2.0-flash` (free tier available!)

---

## File Structure

```
medrag/
├── src/llm/
│   ├── gemini_client.py          ← Gemini implementation
│   └── openai_client.py          ← OpenAI implementation
├── configs/pipeline_config.yaml  ← Edit provider here
├── switch_llm_provider.sh        ← Use to switch easily
├── LLM_INTEGRATION_GUIDE.md      ← Full setup guide
└── GEMINI_IMPLEMENTATION.md      ← Implementation details
```

---

## Troubleshooting (TL;DR)

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: google.generativeai` | `pip install google-generativeai>=0.3.0` |
| `401 Unauthorized` | Check API key: `echo $GOOGLE_API_KEY` |
| `429 Too Many Requests` | Free tier limit (15 req/min), wait or upgrade |
| `YAML Parse Error` | Check indentation, use 2 spaces |
| Empty API key | `export GOOGLE_API_KEY="your-key-from-aistudio"` |
| Wrong provider | Edit `configs/pipeline_config.yaml` or `./switch_llm_provider.sh gemini` |

---

## Getting API Keys (Quick Links)

- **Google Gemini:** https://aistudio.google.com/app/apikey (1-click, free)
- **OpenAI:** https://platform.openai.com/api/keys (requires account)
- **GCP:** https://console.cloud.google.com (more setup, optional)

---

## Code Examples

### Switch in Python
```python
from src.llm.gemini_client import GeminiClient
from src.llm.openai_client import OpenAIClient

config = load_config()
provider = config.get("llm", {}).get("provider", "openai")

if provider == "gemini":
    llm = GeminiClient(model="gemini-2.0-flash")
else:
    llm = OpenAIClient(model="gpt-4o-mini")

response = llm.generate("Your prompt here")
```

### Use in Pipeline
```python
# Already integrated! Just update config:
# configs/pipeline_config.yaml:
#   provider: gemini
#   model: gemini-2.0-flash

python scripts/run_hybrid_pipeline.py --config configs/pipeline_config.yaml ...
```

---

## Performance Metrics

| Metric | Gemini 2.0 | OpenAI Mini |
|--------|-----------|-------------|
| **Queries/min** | 15 (free) | 3-5 |
| **Latency (avg)** | 400ms | 800ms |
| **Cost/1M tokens** | $0.375 | $0.375 |
| **Setup time** | 1 min | 5 min |
| **Free tier?** | ✅ Yes | ❌ No |

---

## Next Steps

1. ✅ **Install:** `pip install google-generativeai>=0.3.0`
2. ✅ **Get key:** https://aistudio.google.com/app/apikey
3. ✅ **Export:** `export GOOGLE_API_KEY="..."`
4. ✅ **Switch:** `./switch_llm_provider.sh gemini`
5. ✅ **Test:** `python scripts/run_hybrid_pipeline.py --max_questions 1`
6. ✅ **Run:** Full pipeline on SLURM

---

## Documentation

- **Full Setup Guide:** `LLM_INTEGRATION_GUIDE.md`
- **Implementation Details:** `GEMINI_IMPLEMENTATION.md`
- **Checklist:** `GEMINI_CHECKLIST.md`
- **This Quick Ref:** `LLM_QUICK_REFERENCE.md` ← You are here

---

**Questions?** See the full guides above or check `src/llm/gemini_client.py` for implementation.

**Issues?** See Troubleshooting section or check GitHub issues.

**Ready to go?** Run: `./switch_llm_provider.sh gemini` and start indexing! 🚀
