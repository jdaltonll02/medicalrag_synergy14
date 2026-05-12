# BioASQ Answer Evaluation - LLM Judge System

## Summary

I've created a comprehensive **LLM Judge evaluation system** for scoring and evaluating BioASQ answers using ChatGPT as an expert biomedical evaluator.

## Components Created

### 1. Judge Prompt System (`src/evaluation/judge_prompt.py`)
- **Expert system prompt**: Defines the judge persona as a biomedical researcher with expertise in BioASQ evaluation
- **5-criterion scoring framework**:
  - Accuracy (0-100)
  - Completeness (0-100)
  - Relevance (0-100)
  - Clarity (0-100)
  - Conciseness (0-100)
  - Overall score (0-100, weighted by question type)

- **Question-type-specific guidance**:
  - **Yes/No**: Accuracy 60%, Explanation 25%, Brevity 15%
  - **Factoid**: Accuracy 50%, Completeness 30%, Clarity 20%
  - **List**: Completeness 40%, Accuracy 40%, Clarity 20%
  - **Summary**: Accuracy 40%, Completeness 35%, Clarity 25%

### 2. Judge Evaluator Script (`scripts/evaluate_with_judge.py`)
- Batch evaluation of BioASQ results
- Single-question evaluation
- Comparative analysis (Answer A vs Answer B)
- Summary statistics generation
- JSON output for integration with pipelines

## Usage Examples

```bash
# Evaluate all questions from results file
python scripts/evaluate_with_judge.py \
  --results results3/round_3_results.json \
  --output evaluation_report.json \
  --summary \
  --model gpt-4o-mini-2024-07-18

# Evaluate first 10 questions
python scripts/evaluate_with_judge.py \
  --results results3/round_3_results.json \
  --output eval_sample.json \
  --max-questions 10 \
  --summary

# Evaluate single answer
python scripts/evaluate_with_judge.py \
  --question "What is BRCA1?" \
  --type factoid \
  --answer "BRCA1 is a tumor suppressor..." \
  --references "BRCA1 encodes a nuclear protein..."

# Compare two answers
python scripts/evaluate_with_judge.py \
  --question "What causes retinal detachment?" \
  --type factoid \
  --compare-a "Answer from Model A..." \
  --compare-b "Answer from Model B..." \
  --summary
```

## Sample Evaluation Results

### Question 1: Glucocorticoid Withdrawal Syndrome Symptoms (List Question)
```json
{
  "overall_score": 88,
  "accuracy_score": 90,
  "completeness_score": 80,
  "relevance_score": 90,
  "clarity_score": 90,
  "conciseness_score": 100,
  "feedback": "The candidate answer provides a list of symptoms associated with glucocorticoid withdrawal syndrome, which is accurate and relevant. However, the completeness score is slightly lower due to the omission of some common symptoms such as joint pain, dizziness, or mood changes...",
  "strengths": [
    "Accurate symptoms listed",
    "Clear and well-organized presentation",
    "Concise response"
  ],
  "weaknesses": [
    "Missing some common symptoms of glucocorticoid withdrawal syndrome"
  ],
  "improvements": "Include additional symptoms commonly associated with glucocorticoid withdrawal syndrome, such as joint pain, dizziness, or mood changes..."
}
```

### Question 2: Serine/Threonine Kinase Family Count (Factoid Question)
```json
{
  "overall_score": 86,
  "accuracy_score": 90,
  "completeness_score": 80,
  "relevance_score": 90,
  "clarity_score": 85,
  "conciseness_score": 80,
  "feedback": "The answer provides a factually correct estimate of the number of serine/threonine kinases in the human proteome, which is approximately 518. However, while the additional context is relevant, it slightly detracts from the completeness score as it does not directly address the question..."
}
```

### Question 3: Scleral Buckle Purpose (Factoid Question)
```json
{
  "overall_score": 91,
  "accuracy_score": 95,
  "completeness_score": 90,
  "relevance_score": 100,
  "clarity_score": 90,
  "conciseness_score": 85,
  "feedback": "The answer accurately describes the scleral buckle procedure and its purpose in treating retinal detachment, which is factually correct. It provides a good level of detail about the method and its effectiveness..."
}
```

## Performance Summary (First 3 Questions)
```
Total Evaluations: 3
Average Overall Score: 88.33/100
Average Accuracy Score: 91.67/100
Average Completeness Score: 83.33/100

Scores by Question Type:
- List questions: 88.0/100
- Factoid questions: 88.5/100
```

## Key Features

### 1. Expert Evaluation
- Uses gpt-4o-mini-2024-07-18 via CMU AI Gateway
- Biomedical domain expertise built into prompts
- Consistent scoring criteria across all evaluations

### 2. Detailed Feedback
Each evaluation includes:
- Individual criterion scores (0-100)
- Overall weighted score
- Detailed feedback explaining reasoning
- Strengths and weaknesses
- Specific improvement suggestions
- Comparison to reference answers (when available)

### 3. Question-Type Aware
Different scoring weights based on question type:
- Yes/No questions emphasize correctness of binary answer
- Factoid questions emphasize accuracy of named entities
- List questions emphasize completeness of items
- Summary questions emphasize comprehensive coverage

### 4. Batch Processing
- Evaluate all questions in results file
- Limit evaluations with `--max-questions` for testing
- Generate summary statistics automatically
- JSON output for downstream processing

### 5. Integration Ready
- Compatible with BioASQ submission format
- Can evaluate against reference answers
- Supports comparative analysis
- Enables automated quality assessment

## Next Steps

To evaluate all round 3 results:
```bash
python scripts/evaluate_with_judge.py \
  --results results3/round_3_results.json \
  --output evaluation_report_r3_complete.json \
  --summary \
  --model gpt-4o-mini-2024-07-18
```

This will:
1. Load all questions from round 3 results
2. Evaluate each answer using the LLM judge
3. Generate detailed evaluation reports
4. Produce summary statistics by question type
5. Save results to JSON file for analysis

## Cost Estimation

- Each evaluation: ~4 seconds (0.5-1 min per question with LLM latency)
- 64 questions: ~4-6 minutes total
- Estimated cost: ~$0.10-0.20 per full evaluation (using gpt-4o-mini)

## Output Format

Each evaluation contains:
```json
{
  "question": "Question text",
  "question_type": "factoid|yesno|list|summary",
  "candidate_answer": "The evaluated answer",
  "reference_answers": ["Reference answer 1", "Reference answer 2"],
  "evaluation": {
    "accuracy_score": 0-100,
    "completeness_score": 0-100,
    "relevance_score": 0-100,
    "clarity_score": 0-100,
    "conciseness_score": 0-100,
    "overall_score": 0-100,
    "feedback": "Detailed explanation...",
    "strengths": ["strength1", "strength2"],
    "weaknesses": ["weakness1", "weakness2"],
    "improvements": "Specific recommendations..."
  },
  "timestamp": "2026-02-11T11:34:50.142696"
}
```

---

**System Status**: ✅ Ready for evaluation
**Test Results**: 88.33/100 average on first 3 questions
**Availability**: Requires OPENAI_API_KEY environment variable set
