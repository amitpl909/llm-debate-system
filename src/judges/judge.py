"""
Judge and Jury Panel classes for LLM Debate system
Implements single judge and multi-judge jury panel (BONUS FEATURE)
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime
from collections import Counter

from src.llm_client import LLMClient
from prompts.templates import (
    JUDGE_SYSTEM_PROMPT,
    JUDGE_VERDICT_PROMPT,
    JURY_JUDGE_SYSTEM_PROMPT,
    JURY_INITIAL_VERDICT_PROMPT,
    JURY_DELIBERATION_PROMPT,
    JURY_CONSENSUS_PROMPT,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class JudgeVerdict:
    """Represents a judge's verdict on a debate"""
    judge_id: str
    proponent_strongest_arg: str
    proponent_weakest_arg: str
    opponent_strongest_arg: str
    opponent_weakest_arg: str
    verdict: str  # Which debater won
    winning_answer: str  # The answer judge picked as correct
    confidence: int  # 1-5 scale
    reasoning: str
    cot_reasoning: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class DeliberationRecord:
    """Represents a judge's deliberation notes"""
    judge_id: str
    round_number: int
    previous_verdict: str
    stance_after_deliberation: str
    reasoning: str
    changed_mind: bool
    confidence: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# SINGLE JUDGE
# ============================================================================

class Judge:
    """A single judge evaluating a debate"""
    
    def __init__(self, 
                 judge_id: str,
                 client: LLMClient):
        self.judge_id = judge_id
        self.client = client
        self.system_prompt = JUDGE_SYSTEM_PROMPT
        
        self.verdict: Optional[JudgeVerdict] = None
        
        logger.info(f"Initialized Judge (ID: {judge_id})")
    
    def render_verdict(self,
                      question: str,
                      debate_transcript: str,
                      temperature: Optional[float] = None) -> JudgeVerdict:
        """Render verdict based on debate transcript"""
        
        user_prompt = JUDGE_VERDICT_PROMPT.format(
            question=question,
            debate_transcript=debate_transcript
        )
        
        logger.info(f"{self.judge_id}: Rendering verdict on debate")
        response = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        self.verdict = self._parse_verdict(response)
        return self.verdict
    
    def _parse_verdict(self, response: str) -> JudgeVerdict:
        """Parse verdict from LLM response"""
        lines = response.split('\n')
        
        result = {
            "cot_reasoning": "",
            "proponent_strongest_arg": "",
            "proponent_weakest_arg": "",
            "opponent_strongest_arg": "",
            "opponent_weakest_arg": "",
            "verdict": "",
            "winning_answer": "",
            "confidence": 3,
            "reasoning": ""
        }
        
        section = None
        current_text = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect section headers
            if "JUDGE_CHAIN_OF_THOUGHT:" in line_stripped:
                section = "cot"
            elif "PROPONENT_STRONGEST_ARGUMENT:" in line_stripped:
                section = "prop_strong"
            elif "PROPONENT_WEAKEST_ARGUMENT:" in line_stripped:
                section = "prop_weak"
            elif "OPPONENT_STRONGEST_ARGUMENT:" in line_stripped:
                section = "opp_strong"
            elif "OPPONENT_WEAKEST_ARGUMENT:" in line_stripped:
                section = "opp_weak"
            elif "VERDICT:" in line_stripped or ("VERDICT" in line_stripped and ":" in line_stripped):
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "verdict"
                current_text = []
                continue
            elif "WINNING_ANSWER:" in line_stripped:
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "answer"
                current_text = []
                continue
            elif "CONFIDENCE_SCORE:" in line_stripped:
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "confidence"
                current_text = []
                # Try to extract confidence from this line
                try:
                    conf_str = line_stripped.replace("CONFIDENCE_SCORE:", "").strip()
                    conf_val = int(conf_str.split()[0])
                    result["confidence"] = min(5, max(1, conf_val))
                except (ValueError, IndexError):
                    pass
                continue
            elif "REASONING_SUMMARY:" in line_stripped:
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "reasoning"
                current_text = []
                continue
            
            # Add line to current section
            if section and line and not any(x in line_stripped for x in [
                "JUDGE_CHAIN_OF_THOUGHT:", "PROPONENT_STRONGEST_ARGUMENT:",
                "PROPONENT_WEAKEST_ARGUMENT:", "OPPONENT_STRONGEST_ARGUMENT:",
                "OPPONENT_WEAKEST_ARGUMENT:", "VERDICT:", "WINNING_ANSWER:",
                "CONFIDENCE_SCORE:", "REASONING_SUMMARY:"
            ]):
                current_text.append(line)
        
        # Capture last section
        if section and current_text:
            result[self._section_to_key(section)] = "\n".join(current_text).strip()
        
        # Fallback/Cleanup: Extract core Yes/No/Maybe from winning_answer
        if result["winning_answer"]:
            verdict_lower = result["winning_answer"].lower()
            
            # Try to find explicit Yes/No/Maybe
            extracted = ""
            for word in verdict_lower.split():
                if word in ["yes", "no", "maybe"]:
                    extracted = word.capitalize()
                    break
            
            if extracted:
                result["winning_answer"] = extracted
            else:
                # Infer from content - check if sentence is affirmative or negative
                if any(phrase in verdict_lower for phrase in [
                    "did not", "cannot", "is not", "no,", "no.", "opposed", 
                    "against", "refute", "refutes", "wrong", "false", "incorrect"
                ]):
                    result["winning_answer"] = "No"
                elif any(phrase in verdict_lower for phrase in [
                    "did", "can", "is", "yes", "yes,", "yes.", "correct", 
                    "true", "valid", "justified", "supported", "compelling"
                ]):
                    result["winning_answer"] = "Yes"
                # If still can't extract, try to infer from verdict
                else:
                    if result["verdict"]:
                        verdict_text = result["verdict"].lower()
                        if any(phrase in verdict_text for phrase in [
                            "opponent's case", "opponent more", "debater b", "opponent won"
                        ]):
                            result["winning_answer"] = "No"
                        elif any(phrase in verdict_text for phrase in [
                            "proponent's case", "proponent more", "debater a", "proponent won"
                        ]):
                            result["winning_answer"] = "Yes"
        
        return JudgeVerdict(
            judge_id=self.judge_id,
            proponent_strongest_arg=result["proponent_strongest_arg"],
            proponent_weakest_arg=result["proponent_weakest_arg"],
            opponent_strongest_arg=result["opponent_strongest_arg"],
            opponent_weakest_arg=result["opponent_weakest_arg"],
            verdict=result["verdict"],
            winning_answer=result["winning_answer"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            cot_reasoning=result["cot_reasoning"]
        )
    
    @staticmethod
    def _section_to_key(section: str) -> str:
        """Convert section name to result dict key"""
        mapping = {
            "cot": "cot_reasoning",
            "prop_strong": "proponent_strongest_arg",
            "prop_weak": "proponent_weakest_arg",
            "opp_strong": "opponent_strongest_arg",
            "opp_weak": "opponent_weakest_arg",
            "verdict": "verdict",
            "answer": "winning_answer",
            "confidence": "confidence",
            "reasoning": "reasoning"
        }
        return mapping.get(section, section)


# ============================================================================
# JURY PANEL (BONUS FEATURE)
# ============================================================================

class JuryPanel:
    """
    A panel of multiple judges that deliberate to reach conclusions
    BONUS FEATURE: Implements multi-judge consensus system
    """
    
    def __init__(self, 
                 judges: List[Judge],
                 enable_deliberation: bool = True,
                 voting_strategy: str = "majority"):
        self.judges = judges
        self.num_judges = len(judges)
        self.enable_deliberation = enable_deliberation
        self.voting_strategy = voting_strategy
        
        self.verdicts: Dict[str, JudgeVerdict] = {}
        self.deliberations: Dict[str, List[DeliberationRecord]] = {j.judge_id: [] for j in judges}
        self.final_consensus: Optional[Dict[str, Any]] = None
        
        logger.info(f"Initialized Jury Panel with {self.num_judges} judges")
        logger.info(f"Deliberation enabled: {enable_deliberation}, Strategy: {voting_strategy}")
    
    def conduct_initial_evaluation(self,
                                  question: str,
                                  debate_transcript: str,
                                  temperature: Optional[float] = None) -> Dict[str, JudgeVerdict]:
        """
        Have all judges independently evaluate the debate
        Phase 1 of jury process
        """
        logger.info("JURY PHASE 1: Conducting independent initial evaluations")
        logger.info(f"Number of judges: {self.num_judges}")
        
        for judge in self.judges:
            verdict = judge.render_verdict(
                question=question,
                debate_transcript=debate_transcript,
                temperature=temperature
            )
            self.verdicts[judge.judge_id] = verdict
            logger.info(f"{judge.judge_id}: Verdict = {verdict.verdict}, Confidence = {verdict.confidence}")
        
        return self.verdicts
    
    def analyze_disagreement(self) -> Dict[str, Any]:
        """Analyze disagreement among judges"""
        if not self.verdicts:
            return {"total_agreement": True, "agreement_level": 1.0}
        
        answers = [v.winning_answer for v in self.verdicts.values()]
        verdicts = [v.verdict for v in self.verdicts.values()]
        confidences = [v.confidence for v in self.verdicts.values()]
        
        # Calculate agreement metrics
        answer_counts = Counter(answers)
        max_answer_count = max(answer_counts.values())
        agreement_level = max_answer_count / len(answers)
        
        # Calculate confidence distribution
        avg_confidence = sum(confidences) / len(confidences)
        confidence_std = (sum((c - avg_confidence) ** 2 for c in confidences) / len(confidences)) ** 0.5
        
        analysis = {
            "total_judges": self.num_judges,
            "unanimous": agreement_level == 1.0,
            "agreement_level": agreement_level,
            "most_common_answer": answer_counts.most_common(1)[0][0],
            "answer_distribution": dict(answer_counts),
            "verdicts": verdicts,
            "average_confidence": avg_confidence,
            "confidence_std": confidence_std,
            "disagreement_details": {
                j.judge_id: {"answer": v.winning_answer, "confidence": v.confidence, "verdict": v.verdict}
                for j, v in zip(self.judges, self.verdicts.values())
            }
        }
        
        return analysis
    
    def conduct_deliberation(self,
                            question: str,
                            debate_transcript: str,
                            rounds: int = 2,
                            temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Conduct deliberation rounds among judges
        Phase 2 of jury process (only if disagreement exists)
        """
        if not self.enable_deliberation:
            logger.info("Deliberation disabled")
            return {}
        
        disagreement = self.analyze_disagreement()
        
        if disagreement["unanimous"]:
            logger.info("Judges are unanimous - skipping deliberation")
            return {"deliberation_conducted": False, "reason": "unanimous"}
        
        logger.info("JURY PHASE 2: Conducting deliberation")
        logger.info(f"Disagreement level: {1 - disagreement['agreement_level']:.2%}")
        
        deliberation_results = {}
        
        for deliberation_round in range(rounds):
            logger.info(f"Deliberation Round {deliberation_round + 1}/{rounds}")
            
            for judge in self.judges:
                # Get other judges' verdicts
                other_verdicts = {
                    jid: v for jid, v in self.verdicts.items() if jid != judge.judge_id
                }
                
                # Format other verdicts for prompt
                other_verdicts_str = "\n".join([
                    f"{jid}: Answer={v.winning_answer}, Confidence={v.confidence}, Verdict={v.verdict}"
                    for jid, v in other_verdicts.items()
                ])
                
                # Determine agreement status
                your_answer = self.verdicts[judge.judge_id].winning_answer
                agreement_status = "all judges agree with you" if all(
                    v.winning_answer == your_answer for v in other_verdicts.values()
                ) else f"not all judges agree - you chose {your_answer}"
                
                # Conduct deliberation
                user_prompt = JURY_DELIBERATION_PROMPT.format(
                    judge_number=judge.judge_id[-1],  # Extract number from judge_id
                    question=question,
                    your_verdict=self.verdicts[judge.judge_id].verdict,
                    other_verdicts=other_verdicts_str,
                    debate_transcript=debate_transcript,
                    agreement_status=agreement_status
                )
                
                response = judge.client.generate(
                    system_prompt=JURY_JUDGE_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    temperature=temperature
                )
                
                # Parse deliberation response
                deliberation_record = self._parse_deliberation_response(
                    judge.judge_id,
                    response,
                    self.verdicts[judge.judge_id],
                    deliberation_round + 1
                )
                
                self.deliberations[judge.judge_id].append(deliberation_record)
                
                # Update judge's verdict if they changed their mind
                if deliberation_record.changed_mind:
                    logger.info(f"{judge.judge_id} changed their verdict during deliberation")
                    # Note: In a full implementation, we'd update the verdict here
        
        return {"deliberation_conducted": True, "rounds": rounds}
    
    def reach_consensus(self,
                       question: str,
                       debate_transcript: str,
                       temperature: Optional[float] = None) -> Dict[str, Any]:
        """
        Reach final consensus based on verdicts and deliberation
        Phase 3 of jury process
        """
        logger.info("JURY PHASE 3: Reaching consensus")
        
        disagreement = self.analyze_disagreement()
        
        # Determine consensus strategy
        if disagreement["unanimous"]:
            logger.info("Unanimous consensus reached immediately")
            consensus_answer = disagreement["most_common_answer"]
            consensus_confidence = sum(v.confidence for v in self.verdicts.values()) / len(self.verdicts)
            consensus_verdict = "All judges agree"
            deliberation_contributed = False
            
        else:
            # Use voting strategy to determine consensus
            if self.voting_strategy == "majority":
                consensus_answer = disagreement["most_common_answer"]
                deliberation_contributed = any(len(d) > 0 for d in self.deliberations.values())
                
            else:  # "weighted" or other strategies
                weighted_answers = {}
                for judge_id, verdict in self.verdicts.items():
                    answer = verdict.winning_answer
                    weight = verdict.confidence
                    weighted_answers[answer] = weighted_answers.get(answer, 0) + weight
                
                consensus_answer = max(weighted_answers.items(), key=lambda x: x[1])[0]
                deliberation_contributed = True
            
            consensus_confidence = sum(v.confidence for v in self.verdicts.values()) / len(self.verdicts)
            consensus_verdict = f"Consensus via {self.voting_strategy} vote"
        
        self.final_consensus = {
            "question": question,
            "consensus_answer": consensus_answer,
            "consensus_confidence": consensus_confidence,
            "consensus_verdict": consensus_verdict,
            "disagreement_analysis": disagreement,
            "deliberation_contributed": deliberation_contributed,
            "num_judges": self.num_judges,
            "individual_verdicts": {j.judge_id: v.to_dict() for j, v in zip(self.judges, self.verdicts.values())},
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"Consensus reached: {consensus_answer} (Confidence: {consensus_confidence:.1f})")
        
        return self.final_consensus
    
    def _parse_deliberation_response(self,
                                    judge_id: str,
                                    response: str,
                                    previous_verdict: JudgeVerdict,
                                    round_number: int) -> DeliberationRecord:
        """Parse deliberation response from judge"""
        lines = response.split('\n')
        
        reasoning = ""
        final_verdict = ""
        final_confidence = previous_verdict.confidence
        changed_mind = False
        
        section = None
        
        for line in lines:
            line_stripped = line.strip()
            
            if "DELIBERATION_REASONING:" in line_stripped or "DELIBERATION:" in line_stripped:
                section = "reasoning"
            elif "FINAL_VERDICT:" in line_stripped:
                section = "verdict"
            elif "FINAL_CONFIDENCE:" in line_stripped:
                section = "confidence"
                try:
                    conf_str = line_stripped.replace("FINAL_CONFIDENCE:", "").strip()
                    final_confidence = int(conf_str.split()[0])
                    final_confidence = min(5, max(1, final_confidence))
                except (ValueError, IndexError):
                    pass
            elif "WILLING_TO_CONSENSUS:" in line_stripped:
                section = "consensus"
            elif section and line and not any(x in line_stripped for x in [
                "DELIBERATION_REASONING:", "FINAL_VERDICT:", "FINAL_CONFIDENCE:", "WILLING_TO_CONSENSUS:"
            ]):
                if section == "reasoning":
                    reasoning += line + " "
                elif section == "verdict":
                    final_verdict += line + " "
        
        changed_mind = final_verdict.strip() != previous_verdict.verdict
        
        return DeliberationRecord(
            judge_id=judge_id,
            round_number=round_number,
            previous_verdict=previous_verdict.verdict,
            stance_after_deliberation=final_verdict.strip(),
            reasoning=reasoning.strip(),
            changed_mind=changed_mind,
            confidence=final_confidence
        )
    
    def get_jury_report(self) -> Dict[str, Any]:
        """Generate comprehensive jury report"""
        if not self.final_consensus:
            raise ValueError("Must reach consensus first")
        
        report = {
            "jury_composition": {
                "total_judges": self.num_judges,
                "judge_ids": [j.judge_id for j in self.judges]
            },
            "consensus": self.final_consensus,
            "deliberation_records": {
                judge_id: [d.__dict__ for d in records]
                for judge_id, records in self.deliberations.items()
            },
            "analysis": {
                "unanimity": self.final_consensus["disagreement_analysis"]["unanimous"],
                "agreement_level": self.final_consensus["disagreement_analysis"]["agreement_level"],
                "deliberation_impact": self.final_consensus["deliberation_contributed"]
            }
        }
        
        return report


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_jury_panel(num_judges: int, 
                     client_factory,
                     enable_deliberation: bool = True) -> JuryPanel:
    """Factory function to create a jury panel"""
    judges = [
        Judge(judge_id=f"judge_{i+1}", client=client_factory())
        for i in range(num_judges)
    ]
    
    return JuryPanel(
        judges=judges,
        enable_deliberation=enable_deliberation,
        voting_strategy="majority"
    )
