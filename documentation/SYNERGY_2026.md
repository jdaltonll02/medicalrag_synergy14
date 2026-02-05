# BioASQ Synergy 2026 Implementation

This document describes the implementation of BioASQ Synergy 2026 support in the Medical RAG system.

## Overview

The system has been updated to support the BioASQ Synergy 2026 task requirements, including:

- **New JSON format** for test datasets and submissions
- **Snippet extraction** with character offsets from abstracts
- **Answer readiness handling** - only generating exact/ideal answers when `answerReady=true`
- **Feedback incorporation** for iterative improvement across rounds
- **Multi-round support** (rounds 1-4 with 2-week intervals)

## Key Components

### 1. Synergy Formatter (`src/core/synergy_formatter.py`)

Handles conversion between internal representation and Synergy JSON format.

**Classes:**
- **SnippetExtractor**: Extracts relevant text snippets from documents with character offsets
- **SynergyFormatter**: Converts predictions to Synergy submission format
- **FeedbackLoader**: Loads and parses feedback from previous rounds

**Example Usage:**
```python
from src.core.synergy_formatter import SynergyFormatter, SnippetExtractor

# Extract snippets
snippets = SnippetExtractor.extract_snippets(
    query="What is CD177?",
    documents=retrieved_docs,
    max_snippets=10
)

# Format submission
submission = SynergyFormatter.format_submission(
    questions=questions,
    predictions=predictions,
    exact_answers=exact_answers,
    ideal_answers=ideal_answers
)

# Save
SynergyFormatter.save_submission(submission, "output.json")
```

### 2. Answer Generator (`src/core/answer_generator.py`)

Generates exact and ideal answers based on question type and answer readiness.

**Classes:**
- **AnswerGenerator**: Generates exact answers for factoid/list questions
- **YesNoAnswerGenerator**: Generates yes/no answers
- **SummaryAnswerGenerator**: Generates summary answers

**Key Features:**
- Only generates answers when `answerReady=true`
- Supports LLM-based generation via CMU OpenAI Gateway
- Fallback to extractive methods when LLM unavailable

**Example Usage:**
```python
from src.core.answer_generator import AnswerGenerator, YesNoAnswerGenerator

# For factoid questions
if question.get("answerReady"):
    exact = AnswerGenerator.generate_exact_answer(question, docs, llm)
    ideal = AnswerGenerator.generate_ideal_answer(question, docs, llm)

# For yes/no questions
if question.get("type") == "yesno":
    answer = YesNoAnswerGenerator.generate_yesno_answer(question, docs, llm)
```

### 3. Synergy Pipeline (`src/pipeline/synergy_pipeline.py`)

Main pipeline orchestrating document retrieval, answer generation, and submission formatting.

**Classes:**
- **SynergyPipeline**: Processes a complete round
- **SynergyEvaluator**: Evaluates submissions against golden answers

**Methods:**
```python
pipeline = SynergyPipeline(config)
pipeline.set_llm_client(llm)
pipeline.set_retrieval_pipeline(retrieval_pipeline)

result = pipeline.process_round(
    testset_path="data/test/testset_1.json",
    round_num=1,
    output_dir="results",
    feedback_path=None  # For rounds 2+, provide feedback path
)
```

### 4. Run Script (`scripts/run_synergy_pipeline.py`)

End-to-end script for processing Synergy rounds.

**Usage:**
```bash
# Round 1 (no feedback)
python3 scripts/run_synergy_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --output results

# Round 2+ (with feedback)
python3 scripts/run_synergy_pipeline.py \
  --round 2 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_1.json \
  --output results
```

## Data Formats

### Input: Test Dataset Format

```json
{
  "questions": [
    {
      "id": "5e5b8170b761aafe09000010",
      "body": "Which diagnostic test is approved for coronavirus infection screening?",
      "type": "factoid",
      "answerReady": true
    },
    {
      "id": "5e3ebaa348dab47f2600000a",
      "body": "Is the FIP virus a mutated strain of feline enteric coronavirus?",
      "type": "yesno",
      "answerReady": false
    }
  ]
}
```

### Input: Feedback Format (from previous round)

```json
{
  "questions": [
    {
      "id": "5e5b8170b761aafe09000010",
      "body": "Which diagnostic test is approved for coronavirus infection screening?",
      "type": "factoid",
      "answerReady": true,
      "documents": [
        {"id": "34312178", "golden": true},
        {"id": "36781712", "golden": true},
        {"id": "26783383", "golden": false}
      ],
      "snippets": [
        {
          "document": "34312178",
          "offsetInBeginSection": 0,
          "offsetInEndSection": 131,
          "text": "The most commonly used diagnostic tests during the COVID-19 pandemic are polymerase chain reaction (PCR) tests.",
          "beginSection": "abstract",
          "endSection": "abstract",
          "golden": true
        }
      ],
      "exact_answer": ["PCR", "polymerase chain reaction"],
      "ideal_answer": ["PCR tests are the most commonly used diagnostic tests..."]
    }
  ]
}
```

### Output: Submission Format

```json
{
  "questions": [
    {
      "id": "5e5b8170b761aafe09000010",
      "body": "Which diagnostic test is approved for coronavirus infection screening?",
      "type": "factoid",
      "answer_ready": true,
      "documents": ["34312178", "36781712", "26783383"],
      "snippets": [
        {
          "document": "34312178",
          "offsetInBeginSection": 0,
          "offsetInEndSection": 131,
          "text": "The most commonly used diagnostic tests during the COVID-19 pandemic are polymerase chain reaction (PCR) tests.",
          "beginSection": "abstract",
          "endSection": "abstract"
        }
      ],
      "exact_answer": [["PCR"], ["polymerase chain reaction"]],
      "ideal_answer": "PCR tests are the most commonly used diagnostic tests during the COVID-19 pandemic for detection and screening."
    }
  ]
}
```

**Key Differences from Input:**
- `answer_ready` (lowercase) in output vs `answerReady` (camelCase) in input
- `exact_answer` is list of lists in output (up to 5 alternatives per question)
- `ideal_answer` is a single string in output (not a list)
- Only included if `answerReady=true`

## Processing Pipeline

### Round 1 (January 12, 2026)
1. Load testset_1.json with 10-15 questions
2. Retrieve documents from PubMed
3. Generate snippets (all questions)
4. Generate answers (only for answerReady=true questions)
5. Submit in Synergy format
6. **Deadline: 72 hours**

### Rounds 2-4 (January 26, February 9, February 23)
1. Load testset_N.json
2. Load feedback_accompanying_round_(N-1).json
3. Extract golden documents, snippets, and answers from feedback
4. Use as training/validation data
5. Process new/updated questions
6. Generate better answers based on feedback patterns
7. Submit in Synergy format
8. **Deadline: 72 hours per round**

## Configuration

Update `configs/pipeline_config.yaml`:

```yaml
# For Synergy, these are the critical settings:
encoder:
  device: "cpu"  # CPU for compatibility

reranker:
  device: "cpu"  # CPU for compatibility

bm25:
  k1: 2.0
  b: 0.75

# LLM credentials (from CMU AI Gateway)
llm:
  provider: "openai"
  model: "gpt-4"
```

## CMU OpenAI Gateway Setup

Before running, set environment variables:

```bash
export OPENAI_API_KEY="sk-v4B4KHdez6V4sALNjvvv-A"
export OPENAI_BASE_URL="https://ai-gateway.andrew.cmu.edu/openai/deployments/gpt-4/chat/completions"
```

Or use the provided config file:

```bash
source .env.cmu
```

## Example Workflow

```bash
# Setup credentials
source /home/Jdalton/codespace/medrag/.env.cmu

cd /home/Jdalton/codespace/medrag

# Round 1: Process initial questions
python3 scripts/run_synergy_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --output results

# Check output
cat results/synergy_round_1_submission.json | head -50

# Round 2: Process with feedback
python3 scripts/run_synergy_pipeline.py \
  --round 2 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_1.json \
  --output results
```

## Evaluation Metrics

The system evaluates:

1. **Document Retrieval**: Precision, Recall, F1, MRR
2. **Snippet Extraction**: Precision, Recall, F1
3. **Answer Quality**: Exact match, Approximate match (for answer-ready questions)

See `SynergyEvaluator` class for implementation.

## Known Limitations

1. **Snippet Offsets**: Currently calculated based on sentence boundaries. For exact character offsets, may need refinement.
2. **Entity Extraction**: Uses simple regex-based extraction. NER models could improve accuracy.
3. **LLM Availability**: Falls back to extractive methods if LLM unavailable.
4. **Multi-language**: Currently supports English only.

## Future Enhancements

1. Integrate NER service for better entity extraction
2. Add active learning from feedback
3. Implement cross-encoder reranking
4. Support for fulltext retrieval (optional in Synergy)
5. Performance optimization for multi-round iteration

## References

- BioASQ Synergy 2026: https://www.synergy.bioasq.org/
- Synergy Task Guidelines: Available on BioASQ website
- Feedback Format: `data/feedback/feedback_accompanying_round_*.json`

