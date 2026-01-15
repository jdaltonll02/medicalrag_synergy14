# BioASQ Synergy 2026 Implementation - Summary

## ✅ All Tasks Completed

### 1. ✅ Review Current Data Structure
- Confirmed data is already in Synergy 2026 format
- Test datasets: `data/test/testset_{1-4}.json`
- Feedback files: `data/feedback/feedback_accompanying_round_{1-4}.json`
- Golden answers: `data/golden/golden_round_{1-4}.json`

### 2. ✅ Snippet Extraction with Offsets
**File:** `src/core/synergy_formatter.py`
- `SnippetExtractor` class extracts relevant text from abstracts
- Calculates character offsets (`offsetInBeginSection`, `offsetInEndSection`)
- Supports extraction from both title and abstract sections
- Returns snippets in Synergy format

### 3. ✅ Synergy Submission Formatter
**File:** `src/core/synergy_formatter.py`
- `SynergyFormatter` converts predictions to Synergy JSON format
- Handles document list, snippet list, and answer fields
- Respects `answerReady` flag for answer inclusion
- Saves to proper JSON format required for submission

### 4. ✅ Answer Readiness Handling
**File:** `src/core/answer_generator.py`
- `AnswerGenerator`: Generates exact answers for factoid/list questions
- `YesNoAnswerGenerator`: Handles yes/no questions
- `SummaryAnswerGenerator`: Generates summary answers
- **Critical:** Only generates exact/ideal answers when `answerReady=true`
- Provides LLM-based generation with fallback to extractive methods

### 5. ✅ Feedback Incorporation
**File:** `src/core/synergy_formatter.py`
- `FeedbackLoader` class loads feedback from previous rounds
- Extracts golden documents, snippets, and answers
- Methods:
  - `extract_golden_documents()`: Get reference documents
  - `extract_golden_snippets()`: Get reference snippets
  - `extract_golden_answers()`: Get reference answers
- Can be used for training/validation in subsequent rounds

### 6. ✅ Evaluation Metrics
**File:** `src/pipeline/synergy_pipeline.py`
- `SynergyEvaluator` class implements Synergy-specific evaluation
- Metrics supported:
  - Document retrieval: Precision, Recall, F1, MRR
  - Snippet extraction: Precision, Recall, F1
  - Answer quality: Exact match, Approximate match
- Can be applied independently or as part of pipeline

## New Files Created

| File | Purpose |
|------|---------|
| `src/core/synergy_formatter.py` | Snippet extraction and format conversion |
| `src/core/answer_generator.py` | Answer generation for different question types |
| `src/pipeline/synergy_pipeline.py` | Main Synergy processing pipeline |
| `scripts/run_synergy_pipeline.py` | End-to-end submission script |
| `SYNERGY_2026.md` | Comprehensive documentation |
| `.env.cmu` | CMU OpenAI Gateway credentials |

## Key Implementation Details

### Input Format (Test Dataset)
```json
{
  "questions": [
    {
      "id": "...",
      "body": "...",
      "type": "yesno|factoid|list|summary",
      "answerReady": true|false
    }
  ]
}
```

### Output Format (Submission)
```json
{
  "questions": [
    {
      "id": "...",
      "body": "...",
      "type": "...",
      "answer_ready": true|false,
      "documents": ["pmid1", "pmid2", ...],
      "snippets": [
        {
          "document": "pmid",
          "text": "...",
          "offsetInBeginSection": 0,
          "offsetInEndSection": 131,
          "beginSection": "abstract",
          "endSection": "abstract"
        }
      ],
      "exact_answer": [["answer1"], ["answer2"]],  // Only if answerReady=true
      "ideal_answer": "..."                         // Only if answerReady=true
    }
  ]
}
```

## How to Use

### Setup
```bash
# Set CMU credentials
source .env.cmu

# Or manually set:
export OPENAI_API_KEY="sk-v4B4KHdez6V4sALNjvvv-A"
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu/openai/deployments/gpt-4/chat/completions"
```

### Round 1 Submission (January 12)
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --output results
```

### Round 2-4 Submissions (with feedback)
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 2 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_1.json \
  --output results
```

## Output Location
- Submissions: `results/synergy_round_N_submission.json`
- Ready for direct submission to BioASQ Synergy portal

## Testing
```bash
# Quick test with stub LLM
python3 scripts/run_synergy_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --use-stub-llm \
  --output results
```

## Configuration Notes

Key settings in `configs/pipeline_config.yaml`:
- `encoder.device: "cpu"` - CPU-only for compatibility
- `reranker.device: "cpu"` - CPU-only for compatibility
- `llm.provider: "openai"` - Uses CMU gateway when credentials set
- `bm25.k1: 2.0` - Improved BM25 scoring

## Timeline

| Date | Round | Deadline |
|------|-------|----------|
| Jan 12, 2026 | 1 | Jan 15 (72h) |
| Jan 26, 2026 | 2 | Jan 29 (72h) |
| Feb 9, 2026 | 3 | Feb 12 (72h) |
| Feb 23, 2026 | 4 | Feb 26 (72h) |

## Next Steps

1. **Submit Round 1**: Run script January 12-15
2. **Receive Feedback**: Available before Round 2 (Jan 26)
3. **Iterate**: Use `FeedbackLoader` to incorporate golden answers
4. **Improve**: Fine-tune based on feedback metrics
5. **Submit Subsequent Rounds**: Follow same process for rounds 2-4

---

**All implementation complete and ready for submission!**
