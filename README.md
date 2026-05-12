# RAG System for Biomedical Question-Answering (QA)

This repository contains a biomedical Retrieval-Augmented Generation system built for BioASQ-style question answering and the BioASQ Synergy challenge. The codebase combines query understanding, PubMed document acquisition, dense and sparse retrieval, reranking, answer generation, and evaluation into a set of reusable pipeline components and task-specific runner scripts.

The project is not a single monolithic application. It is a working research system with multiple operating modes:

- competition pipelines for BioASQ round evaluation
- Synergy round submission generation with feedback-aware processing
- indexing and ingestion utilities for large PubMed corpora
- an API service for interactive querying
- evaluation utilities for retrieval and answer quality analysis

## What The System Does

At a high level, the system answers biomedical questions by retrieving relevant literature and using an LLM to synthesize submission-ready answers.

The default path in the current codebase is:

1. Load BioASQ questions or Synergy testsets.
2. Build or load a document set, either from PubMed or from a prepared local corpus.
3. Normalize the query and optionally extract biomedical entities.
4. Encode the query for dense retrieval.
5. Retrieve candidate documents with FAISS and or Elasticsearch BM25.
6. Merge and normalize dense and sparse scores in a hybrid retriever.
7. Rerank the candidate set with a cross-encoder.
8. Assemble context and generate exact and ideal answers with a configurable LLM.
9. Save submission artifacts and evaluate them against golden data when available.

## Current Architecture

The core pipeline is centered on MedCPT-based dense retrieval plus BM25 sparse retrieval.

### Main runtime path

- `scripts/run_synergy_pipeline.py` runs the Synergy submission workflow.
- `scripts/run_hybrid_pipeline_medcpt_BM25.py` runs the MedCPT + BM25 BioASQ pipeline.
- `src/pipeline/med_rag_hybrid_medcpt.py` owns the main hybrid orchestration logic.
- `src/retrieval/hybrid_medcpt_retriever.py` merges FAISS and BM25 retrieval results.
- `src/pipeline/synergy_pipeline.py` wraps round processing, feedback loading, and submission formatting.

### Component flow

```text
Question/Testset
  -> BioASQ loader / Synergy loader
  -> PubMed fetch or local corpus access
  -> query normalization + NER
  -> MedCPT query embedding
  -> FAISS dense retrieval
  -> Elasticsearch BM25 retrieval
  -> hybrid score fusion
  -> cross-encoder reranking
  -> answer generation via OpenAI, Gemini, or stub LLM
  -> BioASQ/Synergy submission JSON
  -> evaluation metrics and optional LLM judging
```

### Important distinction

There are several pipeline implementations under `src/pipeline/`.

- `med_rag_hybrid_medcpt.py` is the main competition-oriented hybrid pipeline in current use.
- `med_rag_medcpt.py`, `med_rag_biobert.py`, `med_rag_bm25.py`, and `med_rag_faiss.py` provide alternate retrieval strategies.
- `src/api/app.py` still initializes `src.pipeline.med_rag.MedicalRAGPipeline`, which is a more generic API-facing path than the newer hybrid competition runners.

That split matters: the repository supports both experimentation and submission workflows, and not every entrypoint uses the same orchestration class.

## Major Subsystems

### `src/core`

Core utilities handle data preparation and common pipeline logic.

- `bioasq_loader.py` loads testsets, golden files, feedback files, and question metadata.
- `pubmed_fetcher.py` pulls abstracts and metadata from NCBI Entrez.
- `normalizer.py` provides text normalization.
- `mmr.py` supports maximal marginal relevance and diversity control.
- `answer_generator.py` and `synergy_formatter.py` help shape final outputs.

### `src/retrieval`

Retrieval is intentionally modular so dense-only, sparse-only, and hybrid experiments can share infrastructure.

- `faiss_index.py` manages vector search.
- `bm25_retriever.py` queries Elasticsearch.
- `medcpt_retriever.py` and `biobert_retriever.py` wrap dense retrieval variants.
- `hybrid_retriever.py` and `hybrid_medcpt_retriever.py` combine retrieval signals.

### `src/encoder`

Encoders produce embeddings for dense retrieval. The current config defaults to MedCPT, but the repo also contains alternate pipelines for BioBERT-based retrieval.

### `src/reranker`

Cross-encoder reranking improves the final candidate ordering after initial recall-heavy retrieval.

### `src/llm`

LLM backends are swappable.

- `openai_client.py` supports OpenAI-compatible endpoints, including custom base URLs and project IDs.
- `gemini_client.py` supports Google Gemini.
- `stub_llm.py` provides an offline testing path.
- `llm_judge.py` supports model-based answer evaluation.

### `src/pipeline`

This package contains the end-to-end orchestration layers. It is the most important package for understanding behavior.

- `med_rag_hybrid_medcpt.py` is the primary hybrid biomedical QA pipeline.
- `synergy_pipeline.py` adds round-based processing and feedback integration.
- other files in the package support FAISS-only, BM25-only, MedCPT-only, and BioBERT experiments.

### `src/api`

The FastAPI app exposes a simple query interface, health endpoint, and config endpoint for interactive use or service deployment.

## Execution Modes

### 1. BioASQ evaluation runs

These scripts execute retrieval and generation against BioASQ-style datasets and then write predictions and metrics.

- `scripts/run_pipeline_medcpt.py`
- `scripts/run_pipeline_biobert.py`
- `scripts/run_pipeline_bm25.py`
- `scripts/run_pipeline_faiss.py`
- `scripts/run_hybrid_pipeline.py`
- `scripts/run_hybrid_pipeline_medcpt_BM25.py`

Use these when comparing retrieval strategies or producing round-specific evaluation outputs.

### 2. Synergy submission runs

`scripts/run_synergy_pipeline.py` is the main entrypoint for the BioASQ Synergy task. It:

- loads the current round testset
- optionally loads previous-round feedback
- prepares the retrieval corpus
- initializes the configured LLM and retrieval pipeline
- produces submission JSON and summary metrics

This is the clearest script to read if you want the end-to-end competition flow.

### 3. Corpus preparation and indexing

The repository also contains utilities for building large retrieval corpora and indexes.

- `scripts/prepare_data.py`
- `scripts/encode_documents.py`
- `scripts/build_faiss_index.py`
- `scripts/ingest_elastic.py`
- `scripts/sample_corpus.py`
- `scripts/merge_dedup_corpus.py`
- `scripts/reingest_sampled_corpus.py`
- `scripts/setup_elasticsearch.py`
- `scripts/delete_index.py`

These scripts support the larger-scale workflows referenced by the SLURM files and the 200K and 2.4M corpus documentation.

### 4. Evaluation and validation

Quality checks and grading live in separate scripts so retrieval experiments can be measured consistently.

- `scripts/evaluate_bioasq.py` evaluates BioASQ-style predictions against golden data.
- `scripts/evaluate_with_judge.py` adds judge-based evaluation.
- `scripts/validate_submission.py` checks submission format.
- `scripts/verify_setup.py` verifies environment readiness.

## Configuration Model

The main config surface is `configs/pipeline_config.yaml`.

Key sections include:

- `bioasq`: dataset locations, cache paths, question types, and rounds
- `data`: corpus, embedding, manifest, and results paths
- `encoder`: embedding backend, model, batch size, device, and dimensions
- `bm25`: Elasticsearch host, port, index name, and retrieval parameters
- `faiss`: index type and saved index path
- `retrieval`: top-k values for dense, sparse, and final retrieval
- `reranker`: cross-encoder model and device settings
- `llm`: provider, model, prompts, and endpoint configuration
- `evaluation`: retrieval metrics and optional LLM judge settings
- `temporal` and `mmr`: recency and diversity behavior

The current default config is tuned for a local or cluster-hosted biomedical corpus rather than a small demo dataset. Many paths point at external data directories, which is consistent with the SLURM and large-corpus workflow in this repo.

## LLM Provider Strategy

The system supports three answer-generation modes:

- OpenAI-compatible APIs
- Google Gemini
- stub mode for offline testing

`switch_llm_provider.sh` updates provider settings in `configs/pipeline_config.yaml` and is meant as a quick environment switcher.

This lets the same retrieval stack be reused while changing only the answer-generation backend.

## Infrastructure And Deployment

### Docker

`docker/compose.yml` defines a small service stack with:

- Elasticsearch for sparse retrieval
- a FAISS-related service container
- the FastAPI application

This is the operational path for local service deployment.


## Data And Artifacts

The repository includes both code and accumulated run artifacts.

- `configs/` stores runtime configuration.
- `results/`, `results1/`, `results3/`, and `results4/` store round outputs.
- `evaluation/` contains the evaluation framework.
- `test_data/` contains test resources and round-specific inputs.
- `evaluation_report_r3.json` and related JSON files capture concrete experiment outputs.

This layout reflects a research workflow where code, evaluation outputs, and submission artifacts live together.

## Documentation Layout

There are two documentation areas in the repo.

- `documentation/` contains the main project writeups, setup guides, Synergy notes, large-corpus instructions, and submission checklists.
- `docs/` contains additional usage material and generated documentation assets.

The most relevant deep-dive documents are:

- `documentation/README.md` for the older general overview
- `documentation/README_SYNERGY.md` for Synergy-specific guidance
- `documentation/SYNERGY_ARCHITECTURE.md` and `documentation/SYNERGY_IMPLEMENTATION.md` for the Synergy design
- `documentation/SETUP_200K_CORPUS.md` and `documentation/QUICK_START_200K.md` for large-corpus workflows
- `documentation/SUBMISSION_CHECKLIST.md` for final delivery steps

## Recommended Reading Order

If you are new to the repo, read files in this order:

1. `README.md` for the system map.
2. `configs/pipeline_config.yaml` for the active runtime contract.
3. `scripts/run_synergy_pipeline.py` for the main submission flow.
4. `src/pipeline/med_rag_hybrid_medcpt.py` for the primary retrieval and generation orchestration.
5. `src/retrieval/hybrid_medcpt_retriever.py` for score fusion behavior.
6. `scripts/evaluate_bioasq.py` for how outputs are measured.
7. the relevant files in `documentation/` for setup and operational detail.

## Practical Summary

This project is best understood as a modular biomedical QA platform optimized for BioASQ and Synergy work. Its defining characteristics are:

- hybrid retrieval over biomedical literature
- multiple interchangeable dense retrievers and LLM backends
- evaluation-first workflow with submission artifacts kept in-repo
- support for both local serving and larger cluster-based corpus processing
- specialized scripts for competition rounds, indexing, validation, and experiments

If you need to change behavior, start with the config and the orchestration classes under `src/pipeline/`. If you need to operate the system, start with the runner scripts under `scripts/` and the setup documents under `documentation/`.

## Author
- Professor Eric Nyberg
  Professor, Language Technology Institute
  Carnegie Mellon University

- John Dalton Gibson
  MSECE Student, Department of ECE
  Carnegie Mellon University
