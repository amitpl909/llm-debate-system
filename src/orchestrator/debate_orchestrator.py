"""
Debate Orchestrator - manages the complete debate process
Coordinates debaters, judges, and jury panels through all phases
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from datetime import datetime

from src.agents.debater import (
    ProponentDebater,
    OpponentDebater,
    DebateRound,
    check_positions_match
)
from src.judges.judge import Judge, JuryPanel
from config.config import Config

logger = logging.getLogger(__name__)


# ============================================================================
# DEBATE SESSION DATA MODEL
# ============================================================================

@dataclass
class DebateSession:
    """Represents a complete debate session"""
    session_id: str
    question: str
    context: str
    ground_truth_answer: Optional[str]
    
    debater_a: ProponentDebater = None
    debater_b: OpponentDebater = None
    judge: Optional[Judge] = None
    jury_panel: Optional[JuryPanel] = None
    
    # Results
    initial_positions_match: bool = False
    phase: str = "initialization"  # initialization, debate, judgment, evaluation
    rounds_completed: int = 0
    judge_verdict: Optional[Dict[str, Any]] = None
    jury_consensus: Optional[Dict[str, Any]] = None
    
    # Metadata
    timestamp: str = None
    config: Optional[Config] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary (for JSON serialization)"""
        return {
            "session_id": self.session_id,
            "question": self.question,
            "context": self.context,
            "ground_truth_answer": self.ground_truth_answer,
            "initial_positions_match": self.initial_positions_match,
            "phase": self.phase,
            "rounds_completed": self.rounds_completed,
            "timestamp": self.timestamp,
            "judge_verdict": self.judge_verdict,
            "jury_consensus": self.jury_consensus,
        }


# ============================================================================
# DEBATE ORCHESTRATOR
# ============================================================================

class DebateOrchestrator:
    """Orchestrates the complete debate process"""
    
    def __init__(self, config: Config):
        self.config = config
        self.sessions: Dict[str, DebateSession] = {}
        self.current_session: Optional[DebateSession] = None
        
        logger.info("Initialized DebateOrchestrator")
        logger.info(f"Configuration: {config.experiment_name}")
        logger.info(f"Use jury: {config.use_jury}, Use single judge: {config.use_single_judge}")
    
    def create_session(self,
                      question: str,
                      debater_a: ProponentDebater,
                      debater_b: OpponentDebater,
                      judge: Optional[Judge] = None,
                      jury_panel: Optional[JuryPanel] = None,
                      context: str = "",
                      ground_truth_answer: Optional[str] = None,
                      session_id: Optional[str] = None) -> DebateSession:
        """Create a new debate session"""
        
        if session_id is None:
            session_id = f"session_{len(self.sessions) + 1}"
        
        session = DebateSession(
            session_id=session_id,
            question=question,
            context=context,
            ground_truth_answer=ground_truth_answer,
            debater_a=debater_a,
            debater_b=debater_b,
            judge=judge,
            jury_panel=jury_panel,
            config=self.config
        )
        
        self.sessions[session_id] = session
        self.current_session = session
        
        logger.info(f"Created debate session: {session_id}")
        logger.info(f"Question: {question[:100]}..." if len(question) > 100 else f"Question: {question}")
        
        return session
    
    # ========================================================================
    # PHASE 1: INITIALIZATION
    # ========================================================================
    
    def phase1_initialization(self, session: Optional[DebateSession] = None) -> bool:
        """
        Phase 1: Initialize debate
        - Get initial positions from both debaters
        - Check for consensus
        """
        if session is None:
            session = self.current_session
        
        if session is None:
            raise ValueError("No session provided or set")
        
        logger.info(f"\n{'='*60}")
        logger.info("PHASE 1: INITIALIZATION")
        logger.info(f"{'='*60}")
        
        session.phase = "initialization"
        
        # Generate initial positions
        logger.info("\nGetting initial positions from debaters...")
        
        pos_a = session.debater_a.generate_initial_position(
            question=session.question,
            context=session.context,
            temperature=self.config.model.temperature
        )
        logger.info(f"  Debater A: Answer = {pos_a.answer}, Confidence = {pos_a.confidence}")
        
        pos_b = session.debater_b.generate_initial_position(
            question=session.question,
            context=session.context,
            temperature=self.config.model.temperature
        )
        logger.info(f"  Debater B: Answer = {pos_b.answer}, Confidence = {pos_b.confidence}")
        
        # Check if positions match (consensus)
        positions_match = check_positions_match(pos_a, pos_b)
        session.initial_positions_match = positions_match
        
        if positions_match:
            logger.info(f"\n✓ CONSENSUS REACHED at initialization!")
            logger.info(f"  Both debaters agree: {pos_a.answer}")
            logger.info("  Skipping to Phase 3 (Judgment)")
            return True
        
        logger.info(f"\n✗ Positions differ - proceeding to debate")
        logger.info(f"  Debater A: {pos_a.answer}")
        logger.info(f"  Debater B: {pos_b.answer}")
        
        return False
    
    # ========================================================================
    # PHASE 2: MULTI-ROUND DEBATE
    # ========================================================================
    
    def phase2_debate(self, session: Optional[DebateSession] = None) -> None:
        """
        Phase 2: Multi-round debate
        - Conduct multiple rounds of debate
        - Apply adaptive stopping criterion
        """
        if session is None:
            session = self.current_session
        
        if session is None:
            raise ValueError("No session provided or set")
        
        if session.initial_positions_match:
            logger.info("Skipping Phase 2 - positions already match")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info("PHASE 2: MULTI-ROUND DEBATE")
        logger.info(f"{'='*60}")
        
        session.phase = "debate"
        
        for round_num in range(1, self.config.debate.num_rounds + 1):
            logger.info(f"\n--- ROUND {round_num}/{self.config.debate.num_rounds} ---")
            
            # Get debate transcript so far
            transcript = session.debater_a.get_debate_transcript()
            
            # Debater A presents argument
            logger.info("Debater A (Proponent):")
            debater_a_response = session.debater_a.generate_argument(
                question=session.question,
                debate_history=transcript,
                round_number=round_num,
                total_rounds=self.config.debate.num_rounds,
                temperature=self.config.model.temperature
            )
            logger.info(f"  {debater_a_response['argument'][:100]}...")
            
            # Debater B responds
            logger.info("Debater B (Opponent):")
            transcript = session.debater_a.get_debate_transcript()
            debater_b_response = session.debater_b.generate_argument(
                question=session.question,
                debate_history=transcript,
                round_number=round_num,
                total_rounds=self.config.debate.num_rounds,
                temperature=self.config.model.temperature
            )
            logger.info(f"  {debater_b_response['argument'][:100]}...")
            
            # Create debate round record
            debate_round = DebateRound(
                round_number=round_num,
                debater_a_argument=debater_a_response["argument"],
                debater_a_answer=debater_a_response["updated_answer"],
                debater_b_argument=debater_b_response["argument"],
                debater_b_answer=debater_b_response["updated_answer"],
                debater_a_response_to_opponent=debater_a_response["response_to_opponent"],
                debater_b_response_to_opponent=debater_b_response["response_to_opponent"]
            )
            
            session.debater_a.debate_history.append(debate_round)
            session.debater_b.debate_history.append(debate_round)
            session.rounds_completed = round_num
            
            # Check convergence
            if self.config.debate.enable_early_stopping:
                if (session.debater_a.has_converged(self.config.debate.convergence_rounds) and
                    session.debater_b.has_converged(self.config.debate.convergence_rounds)):
                    
                    final_answer_a = session.debater_a.current_position.answer
                    final_answer_b = session.debater_b.current_position.answer
                    
                    if check_positions_match(session.debater_a.current_position, 
                                            session.debater_b.current_position):
                        logger.info(f"\n✓ CONVERGENCE DETECTED after Round {round_num}")
                        logger.info(f"  Both debaters converged to: {final_answer_a}")
                        break
        
        logger.info(f"\nPhase 2 completed: {session.rounds_completed} rounds conducted")
    
    # ========================================================================
    # PHASE 3: JUDGMENT
    # ========================================================================
    
    def phase3_judgment(self, session: Optional[DebateSession] = None) -> None:
        """
        Phase 3: Judgment
        - Single judge renders verdict
        - Jury panel conducts evaluation and deliberation
        """
        if session is None:
            session = self.current_session
        
        if session is None:
            raise ValueError("No session provided or set")
        
        logger.info(f"\n{'='*60}")
        logger.info("PHASE 3: JUDGMENT")
        logger.info(f"{'='*60}")
        
        session.phase = "judgment"
        
        # Get full debate transcript
        transcript = self._generate_full_transcript(session)
        
        # Single Judge (if enabled)
        if self.config.use_single_judge and session.judge:
            logger.info("\nSingle Judge Evaluation:")
            verdict = session.judge.render_verdict(
                question=session.question,
                debate_transcript=transcript,
                temperature=self.config.model.temperature
            )
            
            session.judge_verdict = verdict.to_dict()
            
            logger.info(f"  Judge: {session.judge.judge_id}")
            logger.info(f"  Verdict: {verdict.verdict}")
            logger.info(f"  Winning Answer: {verdict.winning_answer}")
            logger.info(f"  Confidence: {verdict.confidence}/5")
        
        # Jury Panel (BONUS FEATURE)
        if self.config.use_jury and session.jury_panel:
            logger.info("\nJury Panel Evaluation (BONUS FEATURE - 3+ Judges):")
            
            # Phase 1: Independent evaluation
            logger.info(f"\n  Phase 1: Independent evaluation by {session.jury_panel.num_judges} judges")
            verdicts = session.jury_panel.conduct_initial_evaluation(
                question=session.question,
                debate_transcript=transcript,
                temperature=self.config.model.temperature
            )
            
            # Analyze disagreement
            disagreement = session.jury_panel.analyze_disagreement()
            logger.info(f"  Agreement level: {disagreement['agreement_level']:.1%}")
            logger.info(f"  Answer distribution: {disagreement['answer_distribution']}")
            
            # Phase 2: Deliberation (if not unanimous)
            if not disagreement["unanimous"] and session.jury_panel.enable_deliberation:
                logger.info(f"\n  Phase 2: Deliberation (judges not unanimous)")
                session.jury_panel.conduct_deliberation(
                    question=session.question,
                    debate_transcript=transcript,
                    rounds=self.config.jury.deliberation_rounds,
                    temperature=self.config.model.temperature
                )
            
            # Phase 3: Reach consensus
            logger.info(f"\n  Phase 3: Reaching consensus")
            consensus = session.jury_panel.reach_consensus(
                question=session.question,
                debate_transcript=transcript,
                temperature=self.config.model.temperature
            )
            
            session.jury_consensus = consensus
            
            logger.info(f"  Final Consensus Answer: {consensus['consensus_answer']}")
            logger.info(f"  Consensus Confidence: {consensus['consensus_confidence']:.1f}/5")
            logger.info(f"  Unanimous: {disagreement['unanimous']}")
    
    # ========================================================================
    # PHASE 4: EVALUATION
    # ========================================================================
    
    def phase4_evaluation(self, session: Optional[DebateSession] = None) -> Dict[str, Any]:
        """
        Phase 4: Evaluation
        - Compare judge/jury verdicts against ground truth
        - Calculate accuracy metrics
        """
        if session is None:
            session = self.current_session
        
        if session is None:
            raise ValueError("No session provided or set")
        
        logger.info(f"\n{'='*60}")
        logger.info("PHASE 4: EVALUATION")
        logger.info(f"{'='*60}")
        
        session.phase = "evaluation"
        
        results = {
            "question": session.question,
            "ground_truth": session.ground_truth_answer,
            "single_judge": {},
            "jury_panel": {},
            "accuracy_metrics": {}
        }
        
        # Evaluate single judge
        if session.judge_verdict:
            judge_answer = session.judge_verdict.get("winning_answer", "")
            judge_correct = judge_answer.lower().strip() == session.ground_truth_answer.lower().strip() if session.ground_truth_answer else None
            
            results["single_judge"] = {
                "judge_id": session.judge_verdict.get("judge_id"),
                "answer": judge_answer,
                "confidence": session.judge_verdict.get("confidence"),
                "correct": judge_correct
            }
            
            logger.info(f"\nSingle Judge Result:")
            logger.info(f"  Answer: {judge_answer}")
            logger.info(f"  Correct: {judge_correct}")
            if judge_correct is not None:
                logger.info(f"  ✓ CORRECT" if judge_correct else f"  ✗ INCORRECT")
        
        # Evaluate jury panel
        if session.jury_consensus:
            jury_answer = session.jury_consensus.get("consensus_answer", "")
            jury_correct = jury_answer.lower().strip() == session.ground_truth_answer.lower().strip() if session.ground_truth_answer else None
            
            results["jury_panel"] = {
                "num_judges": session.jury_consensus.get("num_judges"),
                "answer": jury_answer,
                "confidence": session.jury_consensus.get("consensus_confidence"),
                "correct": jury_correct,
                "unanimous": session.jury_consensus.get("disagreement_analysis", {}).get("unanimous"),
                "agreement_level": session.jury_consensus.get("disagreement_analysis", {}).get("agreement_level")
            }
            
            logger.info(f"\nJury Panel Result:")
            logger.info(f"  Answer: {jury_answer}")
            logger.info(f"  Num Judges: {session.jury_consensus.get('num_judges')}")
            logger.info(f"  Correct: {jury_correct}")
            if jury_correct is not None:
                logger.info(f"  ✓ CORRECT" if jury_correct else f"  ✗ INCORRECT")
        
        return results
    
    # ========================================================================
    # COMPLETE DEBATE EXECUTION
    # ========================================================================
    
    def run_complete_debate(self, session: Optional[DebateSession] = None) -> Dict[str, Any]:
        """Run complete debate through all phases"""
        if session is None:
            session = self.current_session
        
        if session is None:
            raise ValueError("No session provided or set")
        
        logger.info(f"\n{'#'*60}")
        logger.info("STARTING COMPLETE DEBATE SESSION")
        logger.info(f"Session ID: {session.session_id}")
        logger.info(f"{'#'*60}")
        
        # Phase 1
        consensus_at_init = self.phase1_initialization(session)
        
        # Phase 2
        if not consensus_at_init:
            self.phase2_debate(session)
        
        # Phase 3
        self.phase3_judgment(session)
        
        # Phase 4
        evaluation_results = self.phase4_evaluation(session)
        
        logger.info(f"\n{'#'*60}")
        logger.info("DEBATE SESSION COMPLETE")
        logger.info(f"{'#'*60}\n")
        
        return evaluation_results
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def _generate_full_transcript(self, session: DebateSession) -> str:
        """Generate full debate transcript for judges"""
        transcript = f"QUESTION: {session.question}\n"
        transcript += f"CONTEXT: {session.context if session.context else 'None'}\n\n"
        
        transcript += "INITIAL POSITIONS:\n"
        transcript += f"  Debater A (Proponent): {session.debater_a.initial_position.answer} (Confidence: {session.debater_a.initial_position.confidence})\n"
        transcript += f"  Debater B (Opponent):  {session.debater_b.initial_position.answer} (Confidence: {session.debater_b.initial_position.confidence})\n\n"
        
        for round_data in session.debater_a.debate_history:
            transcript += f"ROUND {round_data.round_number}:\n"
            transcript += f"  PROPONENT (Debater A):\n    {round_data.debater_a_argument}\n\n"
            transcript += f"  OPPONENT (Debater B):\n    {round_data.debater_b_argument}\n\n"
        
        return transcript
    
    def save_session(self, session: DebateSession, filepath: str) -> None:
        """Save session to JSON file"""
        session_dict = session.to_dict()
        
        with open(filepath, 'w') as f:
            json.dump(session_dict, f, indent=2, default=str)
        
        logger.info(f"Session saved to {filepath}")
    
    def get_session(self, session_id: str) -> Optional[DebateSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)
