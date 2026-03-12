"""
Main entry point for LLM Debate with Jury Panel System
Complete experiment runner with baselines and evaluation
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
# Look for .env in parent directory or current directory
if os.path.exists("../.env"):
    load_dotenv(dotenv_path="../.env")
elif os.path.exists(".env"):
    load_dotenv(dotenv_path=".env")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/debate_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from config.config import Config, get_debug_config, get_production_config
from src.llm_client import create_llm_client
from src.agents.debater import ProponentDebater, OpponentDebater
from src.judges.judge import Judge, JuryPanel, create_jury_panel
from src.orchestrator.debate_orchestrator import DebateOrchestrator, DebateSession
from src.data.data_loader import create_dataset, DebateQuestion
from src.evaluation.evaluator import ResultsAggregator, EvaluationMetrics


# ============================================================================
# ANSWER EXTRACTION HELPER
# ============================================================================

def extract_answer(response: str) -> str:
    """
    Extract the core answer (Yes/No/Maybe) from LLM response.
    Handles cases where LLM adds explanations after the answer.
    
    Examples:
        "No, a penguin cannot swim faster" → "No"
        "YES, the wall is visible" → "Yes"
        "Maybe, it depends on..." → "Maybe"
    """
    if not response:
        return ""
    
    response_clean = response.strip()
    first_word = response_clean.split()[0].lower() if response_clean else ""
    
    # Check if first word is a clear answer
    if first_word in ["yes", "no", "maybe"]:
        return first_word.capitalize()
    
    # Check for answer in common patterns
    response_lower = response_clean.lower()
    if response_lower.startswith("yes"):
        return "Yes"
    elif response_lower.startswith("no"):
        return "No"
    elif response_lower.startswith("maybe"):
        return "Maybe"
    
    # Fallback: return original if can't extract
    return response_clean


# ============================================================================
# BASELINE IMPLEMENTATIONS
# ============================================================================

class BaselineRunner:
    """Runner for baseline comparisons"""
    
    def __init__(self, config: Config):
        self.config = config
        api_key = config.model.anthropic_api_key if config.model.provider == "anthropic" else config.model.openai_api_key
        self.client = create_llm_client(
            model=config.model.baseline_model,
            api_key=api_key,
            temperature=config.model.temperature,
            max_tokens=config.model.max_tokens_baseline,
            provider=config.model.provider
        )
    
    def direct_qa(self, question: str, context: str = "") -> Dict[str, Any]:
        """Direct QA baseline - single LLM call with CoT"""
        from prompts.templates import BASELINE_DIRECT_QA_PROMPT
        
        user_prompt = BASELINE_DIRECT_QA_PROMPT.format(
            question=question,
            context=context if context else "None provided."
        )
        
        logger.info("Running Direct QA baseline")
        response = self.client.generate(
            system_prompt="You are a helpful assistant. Answer questions accurately.",
            user_prompt=user_prompt
        )
        
        # Parse response
        answer = self._extract_answer(response)
        
        return {
            "answer": answer,
            "reasoning": response,
            "method": "direct_qa"
        }
    
    def self_consistency(self, question: str, context: str = "", num_samples: int = 5) -> Dict[str, Any]:
        """Self-consistency baseline - multiple samples with majority vote"""
        from prompts.templates import BASELINE_SELF_CONSISTENCY_PROMPT
        
        logger.info(f"Running Self-Consistency baseline (samples={num_samples})")
        
        answers = []
        for i in range(num_samples):
            user_prompt = BASELINE_SELF_CONSISTENCY_PROMPT.format(
                question=question,
                context=context if context else "None provided."
            )
            
            response = self.client.generate(
                system_prompt="You are a helpful assistant. Answer questions accurately.",
                user_prompt=user_prompt
            )
            
            answer = self._extract_answer(response)
            answers.append(answer)
            logger.info(f"  Sample {i+1}: {answer}")
        
        # Majority vote
        from collections import Counter
        answer_counts = Counter(answers)
        majority_answer = answer_counts.most_common(1)[0][0]
        
        return {
            "answer": majority_answer,
            "samples": answers,
            "method": "self_consistency"
        }
    
    @staticmethod
    def _extract_answer(response: str) -> str:
        """Extract answer from LLM response"""
        lines = response.split('\n')
        for line in lines:
            if line.startswith("ANSWER:"):
                return line.replace("ANSWER:", "").strip()
        
        # Fallback: take first line
        return response.split('\n')[0].strip()[:50]


# ============================================================================
# EXPERIMENT RUNNER
# ============================================================================

class ExperimentRunner:
    """Main experiment runner"""
    
    def __init__(self, config: Config, experiment_id: Optional[str] = None):
        self.config = config
        self.experiment_id = experiment_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_aggregator = ResultsAggregator()
        self.debate_sessions = []
        
        logger.info(f"\n{'='*60}")
        logger.info(f"EXPERIMENT: {self.experiment_id}")
        logger.info(f"{'='*60}")
    
    def _infer_answer_from_verdict(self, verdict_text: str) -> str:
        """Infer Yes/No/Maybe answer from judge verdict text"""
        if not verdict_text:
            return ""
        
        verdict_lower = verdict_text.lower()
        
        # Try to find explicit Yes/No/Maybe next
        for word in verdict_lower.split():
            if word in ["yes", "no", "maybe"]:
                return word.capitalize()
        
        # Infer from judge's decision about who won
        # Opponent argues "No", Proponent argues "Yes"
        if any(phrase in verdict_lower for phrase in [
            "opponent's case", "opponent's position", "debater b", "b's case",
            "opponent more", "opponent stronger", "opponent won", "opposed"
        ]):
            return "No"
        elif any(phrase in verdict_lower for phrase in [
            "proponent's case", "proponent's position", "debater a", "a's case",
            "proponent more", "proponent stronger", "proponent won"
        ]):
            return "Yes"
        
        return ""
    
    def run_experiment(self, 
                      questions: List[DebateQuestion],
                      debug: bool = False) -> Dict[str, Any]:
        """Run complete experiment on questions"""
        
        logger.info(f"\nStarting experiment on {len(questions)} questions")
        
        for idx, question_obj in enumerate(questions, 1):
            logger.info(f"\n{'─'*60}")
            logger.info(f"Question {idx}/{len(questions)}")
            logger.info(f"{'─'*60}")
            
            try:
                self._run_single_debate(question_obj, debug=debug)
            except Exception as e:
                logger.error(f"Error on question {idx}: {str(e)}")
                if debug:
                    raise
                continue
        
        # Generate summary
        summary = self.results_aggregator.generate_summary_statistics()
        
        logger.info(f"\n{'='*60}")
        logger.info("EXPERIMENT COMPLETED")
        logger.info(f"{'='*60}")
        logger.info(self.results_aggregator.generate_comparison_table())
        
        return summary
    
    def _run_single_debate(self, question_obj: DebateQuestion, debug: bool = False) -> None:
        """Run a single debate on one question"""
        
        question = question_obj.question
        context = question_obj.context or ""
        ground_truth = question_obj.answer
        
        logger.info(f"Question: {question[:80]}..." if len(question) > 80 else f"Question: {question}")
        logger.info(f"Ground Truth: {ground_truth}")
        
        # Create LLM clients
        api_key = self.config.model.anthropic_api_key if self.config.model.provider == "anthropic" else self.config.model.openai_api_key
        
        debater_a_client = create_llm_client(
            model=self.config.model.debater_model,
            api_key=api_key,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens_debater,
            provider=self.config.model.provider
        )
        
        debater_b_client = create_llm_client(
            model=self.config.model.debater_model,
            api_key=api_key,
            temperature=self.config.model.temperature,
            max_tokens=self.config.model.max_tokens_debater,
            provider=self.config.model.provider
        )
        
        judge_client = create_llm_client(
            model=self.config.model.judge_model,
            api_key=api_key,
            temperature=0.3,  # Lower temp for consistency
            max_tokens=self.config.model.max_tokens_judge,
            provider=self.config.model.provider
        )
        
        # Create debaters
        debater_a = ProponentDebater(debater_a_client)
        debater_b = OpponentDebater(debater_b_client)
        
        # Create judge
        judge = Judge("judge_single", judge_client) if self.config.use_single_judge else None
        
        # Create jury panel
        jury_panel = None
        if self.config.use_jury:
            jury_clients = [
                create_llm_client(
                    model=self.config.model.judge_model,
                    api_key=api_key,
                    temperature=0.3,
                    max_tokens=self.config.model.max_tokens_judge,
                    provider=self.config.model.provider
                )
                for _ in range(self.config.jury.num_judges)
            ]
            
            judges_list = [
                Judge(f"judge_{i+1}", client)
                for i, client in enumerate(jury_clients)
            ]
            
            jury_panel = JuryPanel(
                judges=judges_list,
                enable_deliberation=self.config.jury.enable_deliberation,
                voting_strategy=self.config.jury.voting_strategy
            )
        
        # Create orchestrator
        orchestrator = DebateOrchestrator(self.config)
        
        # Create session
        session = orchestrator.create_session(
            question=question,
            debater_a=debater_a,
            debater_b=debater_b,
            judge=judge,
            jury_panel=jury_panel,
            context=context,
            ground_truth_answer=ground_truth,
            session_id=f"{self.experiment_id}_{question_obj.question_id}"
        )
        
        # Run debate
        orchestrator.run_complete_debate(session)
        self.debate_sessions.append(session)
        
        # Run baselines
        baseline_runner = BaselineRunner(self.config)
        
        if self.config.baseline.enable_direct_qa:
            logger.info("\nRunning Direct QA baseline...")
            direct_qa_result = baseline_runner.direct_qa(question, context)
            direct_qa_answer = direct_qa_result["answer"]
            direct_qa_correct = (
                extract_answer(direct_qa_answer).lower() == ground_truth.lower().strip()
            )
            logger.info(f"  Answer: {direct_qa_answer}")
            logger.info(f"  Correct: {direct_qa_correct}")
        else:
            direct_qa_answer = "N/A"
            direct_qa_correct = False
        
        if self.config.baseline.enable_self_consistency:
            logger.info("\nRunning Self-Consistency baseline...")
            sc_result = baseline_runner.self_consistency(
                question, 
                context,
                num_samples=self.config.baseline.self_consistency_samples
            )
            sc_answer = sc_result["answer"]
            sc_correct = (
                extract_answer(sc_answer).lower() == ground_truth.lower().strip()
            )
            logger.info(f"  Answer: {sc_answer}")
            logger.info(f"  Correct: {sc_correct}")
        else:
            sc_answer = "N/A"
            sc_correct = False
        
        # Extract results
        judge_answer = session.judge_verdict["winning_answer"] if session.judge_verdict else "N/A"
        
        # Enhanced: if judge_answer is empty, try to extract from verdict with smart inference
        if not judge_answer or judge_answer == "":
            judge_verdict_text = session.judge_verdict.get("verdict", "") if session.judge_verdict else ""
            if judge_verdict_text:
                judge_answer = self._infer_answer_from_verdict(judge_verdict_text)
        
        # If still empty, try to use extract_answer as last resort
        if not judge_answer or judge_answer == "":
            judge_answer = extract_answer(judge_answer if judge_answer else "")
        
        judge_correct = session.judge_verdict is not None and (\
            extract_answer(judge_answer).lower() == ground_truth.lower().strip()\
        )
        judge_confidence = session.judge_verdict["confidence"] if session.judge_verdict else 0
        
        jury_answer = session.jury_consensus["consensus_answer"] if session.jury_consensus else "N/A"
        
        # Enhanced: if jury_answer is empty, try to infer from individual verdicts
        if not jury_answer or jury_answer == "":
            # Try to infer from individual judge verdicts in disagreement analysis
            try:
                disagreement_details = session.jury_consensus.get("disagreement_analysis", {}).get("disagreement_details", {}) if session.jury_consensus else {}
                if disagreement_details:
                    # Collect answers from individual judges
                    answers = []
                    for judge_data in disagreement_details.values():
                        answer = judge_data.get("answer", "")
                        verdict = judge_data.get("verdict", "")
                        
                        # If answer is empty, try to infer from verdict
                        if not answer or answer == "":
                            inferred = self._infer_answer_from_verdict(verdict)
                            if inferred:
                                answers.append(inferred)
                        else:
                            answers.append(answer)
                    
                    # Use majority vote from answers
                    if answers:
                        from collections import Counter
                        most_common = Counter(answers).most_common(1)
                        if most_common:
                            jury_answer = most_common[0][0]
            except (KeyError, TypeError, AttributeError):
                pass
        
        jury_correct = session.jury_consensus is not None and (
            extract_answer(jury_answer).lower() == ground_truth.lower().strip()
        )
        jury_confidence = session.jury_consensus["consensus_confidence"] if session.jury_consensus else 0
        jury_unanimous = session.jury_consensus.get("disagreement_analysis", {}).get("unanimous", False) if session.jury_consensus else False
        jury_agreement = session.jury_consensus.get("disagreement_analysis", {}).get("agreement_level", 0) if session.jury_consensus else 0
        
        # Add to results
        self.results_aggregator.add_debate_result(
            debate_id=session.session_id,
            question=question,
            ground_truth=ground_truth,
            direct_qa_answer=direct_qa_answer,
            direct_qa_correct=direct_qa_correct,
            self_consistency_answer=sc_answer,
            self_consistency_correct=sc_correct,
            judge_answer=judge_answer,
            judge_correct=judge_correct,
            judge_confidence=judge_confidence,
            jury_answer=jury_answer,
            jury_correct=jury_correct,
            jury_confidence=jury_confidence,
            jury_unanimous=jury_unanimous,
            jury_agreement_level=jury_agreement,
            num_judges=self.config.jury.num_judges
        )
        
        # Save session
        os.makedirs(self.config.logging.log_dir, exist_ok=True)
        session_file = os.path.join(
            self.config.logging.log_dir,
            f"session_{question_obj.question_id}.json"
        )
        orchestrator.save_session(session, session_file)
    
    def save_results(self, output_dir: str = "outputs") -> None:
        """Save results to files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON results
        json_file = os.path.join(output_dir, f"results_{self.experiment_id}.json")
        self.results_aggregator.to_json(json_file)
        
        # Save CSV results
        csv_file = os.path.join(output_dir, f"results_{self.experiment_id}.csv")
        self.results_aggregator.to_csv(csv_file)
        
        logger.info(f"\nResults saved to {output_dir}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    
    # Configuration
    config = get_debug_config() if "--debug" in sys.argv else get_production_config()
    
    # Load dataset
    logger.info("\nLoading dataset...")
    questions = create_dataset(
        dataset_type=config.debate.task_domain,
        sample_size=config.debate.sample_size,
        seed=42
    )
    
    logger.info(f"Loaded {len(questions)} questions")
    
    # Run experiment
    runner = ExperimentRunner(config)
    summary = runner.run_experiment(questions, debug="--debug" in sys.argv)
    
    # Save results
    runner.save_results(config.logging.output_dir)
    
    logger.info("\n" + "="*60)
    logger.info("EXPERIMENT FINISHED")
    logger.info("="*60)


if __name__ == "__main__":
    main()
