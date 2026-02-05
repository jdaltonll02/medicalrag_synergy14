# BioASQ Synergy 2026 Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Synergy 2026 Pipeline                         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────┐
│     Input Data               │
├──────────────────────────────┤
│ • testset_N.json             │
│ • feedback_round_(N-1).json  │
│ • PubMed Database            │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  1. Load Questions & Feedback            │
│  ├─ BioASQLoader                         │
│  ├─ FeedbackLoader                       │
│  └─ Extract golden answers               │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  2. Document Retrieval                   │
│  ├─ MedCPT Encoder (CPU mode)            │
│  ├─ FAISS Dense Retrieval                │
│  ├─ Python BM25 (sparse)                 │
│  └─ Hybrid Reranking                     │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  3. Snippet Extraction                   │
│  ├─ SnippetExtractor                     │
│  ├─ Find relevant text in abstracts      │
│  └─ Calculate character offsets          │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  4. Answer Generation (if answerReady)   │
│  ├─ AnswerGenerator (factoid/list)       │
│  ├─ YesNoAnswerGenerator                 │
│  ├─ SummaryAnswerGenerator               │
│  └─ CMU OpenAI Gateway LLM               │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  5. Format Submission                    │
│  ├─ SynergyFormatter                     │
│  ├─ Convert to Synergy JSON              │
│  └─ Validate format                      │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│  Output: synergy_round_N_submission.json │
│  ├─ Ready for BioASQ portal              │
│  └─ Contains:                            │
│     • documents (PMIDs)                  │
│     • snippets (with offsets)            │
│     • exact_answer (if answerReady)      │
│     • ideal_answer (if answerReady)      │
└──────────────────────────────────────────┘
```

## Component Details

### 1. Question Loading & Feedback Integration
```
TestSet JSON              Feedback JSON
    │                         │
    └────────────┬────────────┘
                 │
    ┌────────────▼──────────────┐
    │ BioASQLoader               │
    │ FeedbackLoader             │
    │ ────────────────────────── │
    │ Extract:                   │
    │ • Questions                │
    │ • Golden documents         │
    │ • Golden snippets          │
    │ • Golden answers           │
    └────────────┬───────────────┘
                 │
        Questions + Context
```

### 2. Retrieval Pipeline
```
Query Text
    │
    ├──────────────────────────────────┐
    │                                  │
    ▼                                  ▼
┌─────────────────┐          ┌──────────────────┐
│  MedCPT Encoder │          │ BM25 Retriever   │
│  (Dense)        │          │ (Sparse)         │
│  • CPU mode     │          │ • Python impl.   │
│  • FAISS index  │          │ • Fallback mode  │
└────────┬────────┘          └────────┬─────────┘
         │                            │
    Dense Scores              Sparse Scores
         │                            │
         └──────────────┬─────────────┘
                        │
            ┌───────────▼───────────┐
            │ HybridMedCPTRetriever │
            │ • Normalize scores    │
            │ • Combine (α=0.5)     │
            │ • Rerank & filter     │
            └───────────┬───────────┘
                        │
                Top-50 Documents
```

### 3. Snippet Extraction
```
Retrieved Documents
├─ doc_id (PMID)
├─ title
├─ abstract
└─ pub_date
    │
    ├──────────────────────────────┐
    │ SnippetExtractor             │
    │ ────────────────────────────  │
    │ • Parse query terms          │
    │ • Find best matching sentence│
    │ • Calculate offsets          │
    │ • Truncate to 250 chars      │
    └──────────────┬───────────────┘
                   │
        Snippets with Offsets
        {
          "document": "34312178",
          "text": "...",
          "offsetInBeginSection": 0,
          "offsetInEndSection": 131,
          "beginSection": "abstract"
        }
```

### 4. Answer Generation
```
Question (with answerReady flag)
├─ answerReady: true → Generate answers
└─ answerReady: false → Skip answers
    │
    ├─────────────────────────────────────┐
    │                                     │
    ▼                                     ▼
Question Type                      Use Feedback
    │                              (if available)
    ├─ yesno                            │
    │   └─ YesNoAnswerGenerator         │
    │       └─ Return: "yes"/"no"      │
    │                                   │
    ├─ factoid                          │
    │   └─ AnswerGenerator              │
    │       ├─ Extract entities         │
    │       └─ Generate ideal answer   │
    │                                   │
    ├─ list                             │
    │   └─ AnswerGenerator              │
    │       ├─ Extract multiple entities │
    │       └─ Generate ideal answer   │
    │                                   │
    └─ summary                          │
        └─ SummaryAnswerGenerator       │
            └─ Generate summary        │
```

### 5. Output Formatting
```
┌─────────────────────────────────────┐
│ Predictions                         │
├─────────────────────────────────────┤
│ • question_id                       │
│ • retrieved_documents               │
└────────────────┬────────────────────┘
                 │
                 ├─ Extract doc PMIDs
                 ├─ Extract snippets
                 ├─ Generate answers
                 │
    ┌────────────▼────────────┐
    │ SynergyFormatter        │
    │ ────────────────────────│
    │ Convert to JSON:        │
    │ • documents (PMIDs)     │
    │ • snippets (formatted)  │
    │ • exact_answer (if OK)  │
    │ • ideal_answer (if OK)  │
    │ • answer_ready field    │
    └────────────┬────────────┘
                 │
    synergy_round_N_submission.json
```

## Data Flow: Multi-Round Iteration

```
Round 1
├─ Load testset_1.json
├─ No feedback available
├─ Generate baseline answers
└─ SUBMIT → synergy_round_1_submission.json
     │
     └─ (72 hours: await evaluation)
            │
            ▼
Round 2
├─ Load testset_2.json
├─ Load feedback_accompanying_round_1.json
│  ├─ Golden documents (for retrieval tuning)
│  ├─ Golden snippets (reference examples)
│  └─ Golden answers (for validation)
├─ Use feedback to improve:
│  ├─ Re-rank retrievals
│  ├─ Refine entity extraction
│  └─ Better answer generation
└─ SUBMIT → synergy_round_2_submission.json
     │
     └─ (72 hours: await evaluation)
            │
            ▼
Rounds 3-4: REPEAT process with cumulative feedback
```

## File Structure

```
medrag/
├── src/
│   ├── core/
│   │   ├── synergy_formatter.py    ← Snippet extraction & formatting
│   │   └── answer_generator.py     ← Answer generation
│   └── pipeline/
│       └── synergy_pipeline.py     ← Main orchestration
│
├── scripts/
│   └── run_synergy_pipeline.py     ← Entry point
│
├── data/
│   ├── test/
│   │   ├── testset_1.json
│   │   ├── testset_2.json
│   │   ├── testset_3.json
│   │   └── testset_4.json
│   ├── feedback/
│   │   ├── feedback_accompanying_round_1.json
│   │   ├── feedback_accompanying_round_2.json
│   │   ├── feedback_accompanying_round_3.json
│   │   └── feedback_accompanying_round_4.json
│   └── golden/
│       ├── golden_round_1.json
│       ├── golden_round_2.json
│       ├── golden_round_3.json
│       └── golden_round_4.json
│
├── results/
│   └── synergy_round_N_submission.json  ← Submissions
│
├── .env.cmu                        ← CMU credentials
├── SYNERGY_2026.md                 ← Detailed guide
└── SYNERGY_IMPLEMENTATION.md       ← Implementation summary
```

## Key Technologies

| Component | Technology | Mode |
|-----------|-----------|------|
| Embedding | MedCPT | CPU |
| Dense Search | FAISS | CPU |
| Sparse Search | Python BM25 | Fallback |
| Reranker | PubMedBERT | CPU |
| LLM | GPT-4 via CMU Gateway | API |
| Vector Search | FAISS | In-memory |

## Performance Expectations

| Component | Time |
|-----------|------|
| Load questions | < 1s |
| Retrieve documents (50 docs) | ~30-60s per question |
| Extract snippets | < 1s per question |
| Generate answers (LLM) | 2-5s per question |
| Format output | < 1s |
| **Total per round (10 questions)** | **5-10 minutes** |

## Error Handling

```
Each component has fallback mechanisms:

1. MedCPT Encoder
   └─ CPU mode if GPU unavailable

2. Elasticsearch BM25
   └─ Python BM25 fallback if ES not available

3. LLM Generation
   └─ Extractive answer if LLM fails

4. Snippet Extraction
   └─ Return best available snippet

5. Answer Generation
   └─ Return empty if all else fails
```

---

This architecture ensures **robust, multi-round capability** with **graceful degradation** when components are unavailable.
