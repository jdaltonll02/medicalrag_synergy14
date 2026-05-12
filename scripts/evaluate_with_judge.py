#!/usr/bin/env python3
"""
BioASQ Answer Judge Evaluator

Uses ChatGPT/OpenAI as an expert judge to evaluate BioASQ answers against 
reference answers and provide detailed scoring and feedback.

Usage:
    python evaluate_with_judge.py --results results3/round_3_results.json --output evaluation_report.json
    python evaluate_with_judge.py --question "What is BRCA1?" --type factoid --answer "BRCA1 is..." --references "BRCA1 is..."
"""

import json
import argparse
import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("ERROR: openai package not installed. Install with: pip install openai")
    exit(1)

# Import judge prompt utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.evaluation.judge_prompt import (
    JUDGE_SYSTEM_PROMPT,
    get_judge_evaluation_prompt,
    get_comparative_evaluation_prompt,
    create_evaluation_report
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class BioASQJudge:
    """Uses LLM as expert judge for BioASQ answer evaluation."""
    
    def __init__(self, model: str = "gpt-4o-mini", api_base: str = None, api_key: str = None):
        """
        Initialize the judge with OpenAI client.
        
        Args:
            model: LLM model to use (default: gpt-4o-mini)
            api_base: Custom API base URL (for CMU AI Gateway, etc.)
            api_key: Custom API key
        """
        import os
        self.model = model
        
        # Get API key from arguments or environment
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        if api_key is None:
            raise RuntimeError("OPENAI_API_KEY environment variable not set or --api-key not provided")
        
        # Support CMU AI Gateway
        if api_base is None:
            api_base = os.getenv("OPENAI_BASE_URL", "https://ai-gateway.andrew.cmu.edu/v1")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base
        )
    
    def evaluate_answer(self, question: str, question_type: str, 
                       candidate_answer: str, reference_answers: Optional[List[str]] = None,
                       parse_json: bool = True) -> Dict[str, Any]:
        """
        Evaluate a single BioASQ answer using the judge.
        
        Args:
            question: The BioASQ question
            question_type: Type (yesno, factoid, list, summary)
            candidate_answer: Answer to evaluate
            reference_answers: Reference/ideal answers for comparison
            parse_json: Whether to parse judge response as JSON
        
        Returns:
            Dictionary containing evaluation results
        """
        # Generate evaluation prompt
        prompt = get_judge_evaluation_prompt(
            question, question_type, candidate_answer, reference_answers
        )
        
        logger.info(f"Evaluating answer for question type: {question_type}")
        
        try:
            # Call LLM judge
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent scoring
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            judge_response = response.choices[0].message.content
            
            # Parse JSON response if requested
            if parse_json:
                try:
                    evaluation = json.loads(judge_response)
                except json.JSONDecodeError:
                    # Try to extract JSON from response
                    import re
                    json_match = re.search(r'\{.*\}', judge_response, re.DOTALL)
                    if json_match:
                        evaluation = json.loads(json_match.group())
                    else:
                        evaluation = {"raw_response": judge_response}
            else:
                evaluation = {"raw_response": judge_response}
            
            # Create report
            report = create_evaluation_report(
                question, question_type, candidate_answer, 
                reference_answers or [], evaluation
            )
            
            return report
        
        except Exception as e:
            logger.error(f"Error during evaluation: {e}")
            return {
                "error": str(e),
                "question": question,
                "question_type": question_type
            }
    
    def evaluate_batch(self, questions_data: List[Dict[str, Any]], 
                      output_file: Optional[str] = None,
                      max_questions: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Evaluate a batch of answers.
        
        Args:
            questions_data: List of dicts with 'question', 'question_type', 'answer' keys
            output_file: Optional file to save evaluation results
            max_questions: Limit number of questions to evaluate
        
        Returns:
            List of evaluation reports
        """
        results = []
        total = len(questions_data)
        if max_questions:
            total = min(total, max_questions)
        
        for idx, q_data in enumerate(questions_data[:max_questions]):
            if idx % 5 == 0:
                logger.info(f"Evaluating question {idx + 1}/{total}")
            
            report = self.evaluate_answer(
                question=q_data.get("question", ""),
                question_type=q_data.get("question_type", "factoid"),
                candidate_answer=q_data.get("answer", ""),
                reference_answers=q_data.get("reference_answers", None)
            )
            
            results.append(report)
        
        # Save results if output file specified
        if output_file:
            self._save_results(results, output_file)
        
        return results
    
    def evaluate_results_file(self, results_file: str, 
                             output_file: Optional[str] = None,
                             reference_file: Optional[str] = None,
                             max_questions: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Evaluate answers from BioASQ results JSON file.
        
        Args:
            results_file: Path to results JSON file
            output_file: Optional file to save evaluation results
            reference_file: Optional file with reference answers for comparison
            max_questions: Limit number of questions to evaluate
        
        Returns:
            List of evaluation reports
        """
        # Load results
        logger.info(f"Loading results from {results_file}")
        with open(results_file) as f:
            results = json.load(f)
        
        # Load reference answers if provided
        reference_map = {}
        if reference_file:
            logger.info(f"Loading reference answers from {reference_file}")
            with open(reference_file) as f:
                ref_data = json.load(f)
                for item in ref_data.get("questions", []):
                    reference_map[item.get("id")] = item.get("ideal_answer") or item.get("exact_answer")
        
        # Prepare questions for evaluation
        questions_data = []
        for question in results.get("questions", []):
            q_id = question.get("id")
            questions_data.append({
                "question_id": q_id,
                "question": question.get("body", ""),
                "question_type": question.get("type", "factoid"),
                "answer": question.get("ideal_answer", ""),
                "reference_answers": [reference_map[q_id]] if q_id in reference_map else None
            })
        
        # Evaluate batch
        return self.evaluate_batch(questions_data, output_file, max_questions)
    
    def compare_answers(self, question: str, question_type: str,
                       answer_a: str, answer_b: str,
                       reference_answers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare two answers and determine which is better.
        
        Args:
            question: The BioASQ question
            question_type: Type (yesno, factoid, list, summary)
            answer_a: First answer
            answer_b: Second answer
            reference_answers: Reference answers for context
        
        Returns:
            Comparison analysis
        """
        prompt = get_comparative_evaluation_prompt(
            question, question_type, answer_a, answer_b, reference_answers
        )
        
        logger.info("Running comparative evaluation")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
            )
            
            judge_response = response.choices[0].message.content
            
            # Parse JSON response
            try:
                comparison = json.loads(judge_response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\{.*\}', judge_response, re.DOTALL)
                if json_match:
                    comparison = json.loads(json_match.group())
                else:
                    comparison = {"raw_response": judge_response}
            
            return {
                "question": question,
                "question_type": question_type,
                "answer_a": answer_a,
                "answer_b": answer_b,
                "comparison": comparison,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error during comparison: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _save_results(results: List[Dict[str, Any]], output_file: str):
        """Save evaluation results to JSON file."""
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
    
    def generate_summary_report(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics from evaluations."""
        overall_scores = []
        accuracy_scores = []
        completeness_scores = []
        type_scores = {}
        
        for eval_result in evaluations:
            if "evaluation" in eval_result and "overall_score" in eval_result["evaluation"]:
                overall_scores.append(eval_result["evaluation"]["overall_score"])
                
                if "accuracy_score" in eval_result["evaluation"]:
                    accuracy_scores.append(eval_result["evaluation"]["accuracy_score"])
                
                if "completeness_score" in eval_result["evaluation"]:
                    completeness_scores.append(eval_result["evaluation"]["completeness_score"])
                
                q_type = eval_result.get("question_type", "unknown")
                if q_type not in type_scores:
                    type_scores[q_type] = []
                type_scores[q_type].append(eval_result["evaluation"]["overall_score"])
        
        summary = {
            "total_evaluations": len(evaluations),
            "average_overall_score": sum(overall_scores) / len(overall_scores) if overall_scores else 0,
            "average_accuracy_score": sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0,
            "average_completeness_score": sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0,
            "score_by_type": {
                q_type: sum(scores) / len(scores) for q_type, scores in type_scores.items()
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate BioASQ answers using LLM as expert judge"
    )
    parser.add_argument("--results", help="BioASQ results JSON file to evaluate")
    parser.add_argument("--question", help="Single question to evaluate")
    parser.add_argument("--type", dest="question_type", default="factoid", 
                       help="Question type (yesno, factoid, list, summary)")
    parser.add_argument("--answer", help="Answer to evaluate")
    parser.add_argument("--references", nargs="+", help="Reference answers")
    parser.add_argument("--compare-a", help="First answer for comparison")
    parser.add_argument("--compare-b", help="Second answer for comparison")
    parser.add_argument("--output", help="Output file for evaluation results")
    parser.add_argument("--max-questions", type=int, help="Max questions to evaluate")
    parser.add_argument("--api-base", help="Custom API base URL")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model to use")
    parser.add_argument("--summary", action="store_true", help="Generate summary report")
    
    args = parser.parse_args()
    
    # Initialize judge
    judge = BioASQJudge(model=args.model, api_base=args.api_base)
    
    # Single question evaluation
    if args.question and args.answer:
        logger.info("Running single question evaluation")
        report = judge.evaluate_answer(
            args.question,
            args.question_type,
            args.answer,
            args.references
        )
        print(json.dumps(report, indent=2))
    
    # Comparative evaluation
    elif args.compare_a and args.compare_b:
        if not args.question:
            logger.error("--question required for comparison")
            return
        logger.info("Running comparative evaluation")
        comparison = judge.compare_answers(
            args.question,
            args.question_type,
            args.compare_a,
            args.compare_b,
            args.references
        )
        print(json.dumps(comparison, indent=2))
    
    # Batch evaluation from results file
    elif args.results:
        logger.info("Running batch evaluation from results file")
        evaluations = judge.evaluate_results_file(
            args.results,
            args.output,
            max_questions=args.max_questions
        )
        
        if args.summary:
            summary = judge.generate_summary_report(evaluations)
            logger.info("Summary Report:")
            print(json.dumps(summary, indent=2))
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
