#!/usr/bin/env python3
"""
BioASQ Synergy 2026 - Complete submission script
"""

import os
import sys
import json
import yaml
import logging
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.pipeline.synergy_pipeline import SynergyPipeline, SynergyEvaluator
from src.llm.openai_client import OpenAIClient
from src.llm.stub_llm import StubLLM

# Import the appropriate pipeline based on config
from src.pipeline.med_rag_hybrid_medcpt import MedicalRAGPipelineHybridMedCPT


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_llm(config: dict, use_stub: bool = False):
    """Setup LLM client"""
    if use_stub or os.getenv("LLM_PROVIDER") == "stub":
        logger.info("Using Stub LLM for testing")
        return StubLLM()

    llm_config = config.get("llm", {})
    provider = llm_config.get("provider", "openai")

    if provider == "gemini":
        from src.llm.gemini_client import GeminiClient
        logger.info("Initializing Gemini client")
        return GeminiClient(
            model=llm_config.get("model", "gemini-2.0-flash"),
            api_key=llm_config.get("api_key"),
            project_id=llm_config.get("project_id"),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 1024)
        )

    # OpenAI (default)
    if "OPENAI_API_KEY" not in os.environ:
        logger.warning("OPENAI_API_KEY not set, using Stub LLM")
        return StubLLM()

    logger.info("Initializing OpenAI client")
    return OpenAIClient(
        model=llm_config.get("model", "gpt-4"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 1024)
    )


def setup_retrieval_pipeline(config: dict, documents: list):
    """Setup retrieval pipeline"""
    logger.info("Initializing retrieval pipeline")
    
    pipeline = MedicalRAGPipelineHybridMedCPT(config)
    pipeline.index_documents(documents)
    
    return pipeline


def main():
    parser = argparse.ArgumentParser(description="BioASQ Synergy 2026 Submission Script")
    parser.add_argument("--round", type=int, required=True, choices=[1, 2, 3, 4],
                        help="Synergy round number")
    parser.add_argument("--config", required=True, help="Path to config YAML")
    parser.add_argument("--testset", help="Path to testset JSON (auto-inferred if not provided)")
    parser.add_argument("--feedback", help="Path to feedback JSON (for rounds 2+)")
    parser.add_argument("--output", default="results", help="Output directory")
    parser.add_argument("--email", required=True, help="Email for PubMed queries")
    parser.add_argument("--data-dir", default="data/processed", help="Directory with prepared data")
    parser.add_argument("--use-stub-llm", action="store_true", help="Use stub LLM instead of OpenAI")
    
    args = parser.parse_args()
    
    # Setup paths
    if args.testset is None:
        args.testset = f"data/test/testset_{args.round}.json"
    if args.feedback is None and args.round > 1:
        args.feedback = f"data/feedback/feedback_accompanying_round_{args.round - 1}.json"
    
    logger.info(f"Starting Synergy Round {args.round}")
    logger.info(f"Testset: {args.testset}")
    if args.feedback:
        logger.info(f"Feedback: {args.feedback}")
    
    # Load configuration
    config = load_config(args.config)
    
    # Set email for NCBI
    config["pubmed_email"] = args.email
    
    # Load test questions
    with open(args.testset, 'r') as f:
        testset = json.load(f)
    
    questions = testset.get("questions", [])
    logger.info(f"Loaded {len(questions)} questions")
    
    # Load pre-built document corpus from configured path
    docs_path = config.get("data", {}).get("docs_path") or args.data_dir
    documents = []
    if docs_path and Path(docs_path).exists():
        logger.info(f"Loading corpus from {docs_path}")
        with open(docs_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    documents.append(json.loads(line))
    else:
        logger.warning(f"No corpus found at {docs_path!r}; continuing with empty corpus")
    logger.info(f"Loaded {len(documents)} documents")
    
    # Setup LLM
    llm = setup_llm(config, args.use_stub_llm)
    
    # Setup retrieval pipeline
    retrieval_pipeline = setup_retrieval_pipeline(config, documents)
    
    # Setup Synergy pipeline
    synergy = SynergyPipeline(config)
    synergy.set_llm_client(llm)
    synergy.set_retrieval_pipeline(retrieval_pipeline)
    
    # Process round
    result = synergy.process_round(
        testset_path=args.testset,
        round_num=args.round,
        output_dir=args.output,
        feedback_path=args.feedback
    )
    
    # Print metrics
    metrics = result.get("metrics", {})
    print("\n" + "=" * 60)
    print(f"SYNERGY ROUND {args.round} COMPLETE")
    print("=" * 60)
    print(f"Questions processed: {metrics.get('num_questions')}")
    print(f"Answer-ready questions: {metrics.get('num_answer_ready')}")
    print(f"Submission saved to: {metrics.get('output_path')}")
    print("=" * 60 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
