# BioASQ Synergy 2026 Submission Checklist

## Pre-Submission (All Rounds)

### Environment Setup
- [ ] `.env.cmu` file exists
- [ ] `OPENAI_API_KEY` set to CMU credentials
- [ ] `OPENAI_BASE_URL` points to CMU gateway
- [ ] `PYTHONPATH` includes project root
- [ ] Python 3.10+ available
- [ ] Required packages installed (torch, transformers, yaml)

### Data Preparation
- [ ] Test dataset present (`data/test/testset_N.json`)
- [ ] Feedback available (for Round 2+): `data/feedback/feedback_accompanying_round_(N-1).json`
- [ ] Configuration file ready: `configs/pipeline_config.yaml`
- [ ] Output directory prepared: `results/`

### Code Verification
- [ ] Core modules present:
  - [ ] `src/core/synergy_formatter.py`
  - [ ] `src/core/answer_generator.py`
  - [ ] `src/pipeline/synergy_pipeline.py`
- [ ] Scripts present:
  - [ ] `scripts/run_synergy_pipeline.py`
- [ ] Documentation present:
  - [ ] `SYNERGY_2026.md`
  - [ ] `SYNERGY_IMPLEMENTATION.md`
  - [ ] `SYNERGY_ARCHITECTURE.md`

## Round-Specific Checklist

### Round 1 (January 12-15, 2026)

**Pre-Submission (by Jan 12)**
- [ ] System tested with stub LLM
- [ ] System tested with real LLM (if API key available)
- [ ] Output format validated
- [ ] Results directory prepared

**Submission Command**
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 1 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --output results
```

**Post-Submission**
- [ ] File `results/synergy_round_1_submission.json` exists
- [ ] JSON is valid (checked with `python3 -m json.tool`)
- [ ] File contains all required fields
- [ ] Submitted to BioASQ portal
- [ ] Confirmation received from organizers

### Round 2 (January 26-29, 2026)

**Pre-Submission (by Jan 26)**
- [ ] Feedback file received and validated
- [ ] Feedback loaded successfully
- [ ] Golden answers analyzed for patterns
- [ ] System improvements implemented based on feedback

**Submission Command**
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 2 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_1.json \
  --output results
```

**Post-Submission**
- [ ] File `results/synergy_round_2_submission.json` exists
- [ ] JSON is valid
- [ ] Improvement over Round 1 verified (if comparing)
- [ ] Submitted to BioASQ portal
- [ ] Confirmation received from organizers

### Round 3 (February 9-12, 2026)

**Pre-Submission**
- [ ] Feedback from Round 2 received
- [ ] Additional improvements implemented
- [ ] System tuned based on cumulative feedback

**Submission**
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 3 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_2.json \
  --output results
```

### Round 4 (February 23-26, 2026)

**Pre-Submission**
- [ ] Final feedback from Round 3 integrated
- [ ] Maximum performance optimization applied
- [ ] Final validation complete

**Submission**
```bash
python3 scripts/run_synergy_pipeline.py \
  --round 4 \
  --config configs/pipeline_config.yaml \
  --email jgibson2@andrew.cmu.edu \
  --feedback data/feedback/feedback_accompanying_round_3.json \
  --output results
```

## Output Validation Checklist

### File Format
- [ ] Output is valid JSON
- [ ] Top-level key is "questions"
- [ ] All questions from input included in output

### Required Fields (All Questions)
- [ ] `id` matches input
- [ ] `body` matches input
- [ ] `type` is valid: yesno, factoid, list, or summary
- [ ] `answer_ready` is boolean
- [ ] `documents` is array of PMIDs (strings)
- [ ] `snippets` is array of objects

### Snippet Format (for each snippet)
- [ ] `document` field present (PMID)
- [ ] `text` field present and not empty
- [ ] `offsetInBeginSection` is integer >= 0
- [ ] `offsetInEndSection` is integer > offsetInBeginSection
- [ ] `beginSection` is valid: title, abstract
- [ ] `endSection` equals beginSection

### Answer Fields (only if answer_ready=true)
- [ ] `exact_answer` is array
- [ ] `ideal_answer` is string
- [ ] At least one answer provided

### Answer Fields (if answer_ready=false)
- [ ] `exact_answer` is empty array
- [ ] `ideal_answer` is empty string

## Validation Commands

```bash
# Check JSON validity
python3 -m json.tool results/synergy_round_N_submission.json > /dev/null
echo $?  # Should return 0

# Validate structure
python3 << 'PYTHON'
import json

with open('results/synergy_round_N_submission.json', 'r') as f:
    submission = json.load(f)

assert 'questions' in submission, "Missing 'questions' key"
questions = submission['questions']

for i, q in enumerate(questions):
    assert 'id' in q, f"Question {i}: missing 'id'"
    assert 'body' in q, f"Question {i}: missing 'body'"
    assert 'type' in q, f"Question {i}: missing 'type'"
    assert 'answer_ready' in q, f"Question {i}: missing 'answer_ready'"
    assert 'documents' in q, f"Question {i}: missing 'documents'"
    assert 'snippets' in q, f"Question {i}: missing 'snippets'"
    
    if q.get('answer_ready'):
        assert 'exact_answer' in q, f"Question {i}: missing 'exact_answer'"
        assert 'ideal_answer' in q, f"Question {i}: missing 'ideal_answer'"

print(f"✓ Valid submission with {len(questions)} questions")
PYTHON
```

## Performance Expectations

| Metric | Target |
|--------|--------|
| Time to process 10 questions | < 10 minutes |
| JSON output file size | 100KB - 2MB |
| Questions with documents | > 95% |
| Questions with snippets (if docs found) | > 95% |
| Answer-ready questions with answers | 100% |
| Answer-not-ready questions with empty answers | 100% |

## Troubleshooting During Submission

| Error | Solution |
|-------|----------|
| Connection timeout | Check internet, retry |
| API key invalid | Verify credentials in `.env.cmu` |
| Module not found | Check PYTHONPATH |
| Memory error | Reduce batch size, restart Python |
| Slow processing | Check system resources, network |
| Invalid JSON output | Verify answer generation module |
| Empty documents | Check retrieval pipeline |
| Empty snippets | Check snippet extractor |

## Post-Submission Actions

### Immediately After Submission
- [ ] Record submission time
- [ ] Note round number and timestamp
- [ ] Save copy of submission file
- [ ] Document any issues or notes

### Before Next Round
- [ ] Check for feedback from organizers
- [ ] Analyze golden answers
- [ ] Plan improvements for next round
- [ ] Update configuration if needed
- [ ] Test improved system

### After Final Round
- [ ] Compile all submissions
- [ ] Gather all feedback
- [ ] Calculate final metrics
- [ ] Document lessons learned
- [ ] Prepare final report

## Submission Portal

**URL**: https://www.synergy.bioasq.org/

**Required Information**:
- Team name
- Contact email
- Organization
- Submission file (JSON)

## Important Dates

| Event | Date | Deadline |
|-------|------|----------|
| Round 1 Questions Release | Jan 12, 2026 | Jan 15 (72h) |
| Round 2 Questions Release | Jan 26, 2026 | Jan 29 (72h) |
| Round 3 Questions Release | Feb 9, 2026 | Feb 12 (72h) |
| Round 4 Questions Release | Feb 23, 2026 | Feb 26 (72h) |
| Task Completion | | Mar 2, 2026 |

## Contact Information

**BioASQ Organizers**: info@bioasq.org

**System Owner**: jgibson2@andrew.cmu.edu

**CMU AI Gateway Support**: ai-gateway-support@cmu.edu

---

**Last Updated**: January 14, 2026
**Status**: READY FOR SUBMISSION
