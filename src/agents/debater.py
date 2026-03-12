"""
Debater Agent classes for LLM Debate system
Implements ProponentDebater (A) and OpponentDebater (B)
"""

import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from datetime import datetime

from src.llm_client import LLMClient
from prompts.templates import (
    DEBATER_A_SYSTEM_PROMPT,
    DEBATER_A_INITIAL_POSITION_PROMPT,
    DEBATER_A_DEBATE_ROUND_PROMPT,
    DEBATER_B_SYSTEM_PROMPT,
    DEBATER_B_INITIAL_POSITION_PROMPT,
    DEBATER_B_DEBATE_ROUND_PROMPT,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class DebaterPosition:
    """Represents a debater's position on a question"""
    answer: str
    confidence: int
    reasoning: str
    arguments: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DebateRound:
    """Represents a single round of debate"""
    round_number: int
    debater_a_argument: str
    debater_a_answer: str
    debater_b_argument: str
    debater_b_answer: str
    debater_a_response_to_opponent: str = ""
    debater_b_response_to_opponent: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


# ============================================================================
# ABSTRACT DEBATER BASE CLASS
# ============================================================================

class BaseDebater:
    """Base class for debater agents"""
    
    def __init__(self, 
                 debater_id: str,
                 role: str,
                 client: LLMClient,
                 system_prompt: str):
        self.debater_id = debater_id
        self.role = role  # "proponent" or "opponent"
        self.client = client
        self.system_prompt = system_prompt
        
        self.initial_position: Optional[DebaterPosition] = None
        self.current_position: Optional[DebaterPosition] = None
        self.debate_history: List[DebateRound] = []
        
        logger.info(f"Initialized {self.role} debater (ID: {debater_id})")
    
    def parse_initial_position(self, response: str) -> DebaterPosition:
        """Parse initial position from LLM response"""
        lines = response.split('\n')
        answer = ""
        confidence = 3
        reasoning = ""
        arguments = []
        
        section = None
        for line in lines:
            line = line.strip()
            if line.startswith("ANSWER:"):
                answer = line.replace("ANSWER:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = int(line.replace("CONFIDENCE:", "").strip())
                except ValueError:
                    confidence = 3
            elif line.startswith("COT_REASONING:"):
                section = "reasoning"
            elif line.startswith("KEY_ARGUMENTS:"):
                section = "arguments"
            elif section == "reasoning" and line and not line.startswith(("ANSWER:", "CONFIDENCE:", "KEY_ARGUMENTS:")):
                reasoning += line + " "
            elif section == "arguments" and line.startswith(("1.", "2.", "3.")):
                arg = line[line.find(".")+1:].strip()
                if arg:
                    arguments.append(arg)
        
        return DebaterPosition(
            answer=answer,
            confidence=min(5, max(1, confidence)),
            reasoning=reasoning.strip(),
            arguments=arguments
        )
    
    def parse_debate_response(self, response: str) -> Dict[str, str]:
        """Parse debate round response from LLM"""
        lines = response.split('\n')
        result = {
            "argument": "",
            "response_to_opponent": "",
            "updated_answer": ""
        }
        
        section = None
        current_text = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith("ROUND_ARGUMENT:"):
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "argument"
                current_text = []
            elif line_stripped.startswith("RESPONSE_TO_OPPONENT:"):
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "response"
                current_text = []
            elif line_stripped.startswith("UPDATED_ANSWER:"):
                if section and current_text:
                    result[self._section_to_key(section)] = "\n".join(current_text).strip()
                section = "answer"
                current_text = []
            elif section and line and not line_stripped.startswith((
                "ROUND_ARGUMENT:", "RESPONSE_TO_OPPONENT:", "UPDATED_ANSWER:"
            )):
                current_text.append(line)
        
        # Capture last section
        if section and current_text:
            result[self._section_to_key(section)] = "\n".join(current_text).strip()
        
        return result
    
    @staticmethod
    def _section_to_key(section: str) -> str:
        """Convert section name to result dict key"""
        mapping = {
            "argument": "argument",
            "response": "response_to_opponent",
            "answer": "updated_answer"
        }
        return mapping.get(section, section)
    
    def get_debate_transcript(self) -> str:
        """Generate formatted debate transcript"""
        transcript = "DEBATE TRANSCRIPT:\n"
        transcript += "=" * 60 + "\n\n"
        
        for round_num, round_data in enumerate(self.debate_history, 1):
            transcript += f"ROUND {round_num}\n"
            transcript += "-" * 40 + "\n"
            transcript += f"PROPONENT (Debater A):\n{round_data.debater_a_argument}\n\n"
            transcript += f"OPPONENT (Debater B):\n{round_data.debater_b_argument}\n\n"
        
        return transcript
    
    def has_converged(self, rounds: int = 2) -> bool:
        """Check if debater has maintained same answer for N rounds"""
        if len(self.debate_history) < rounds:
            return False
        
        recent_answers = [
            self.debate_history[-i].debater_a_answer if self.role == "proponent" 
            else self.debate_history[-i].debater_b_answer
            for i in range(1, rounds + 1)
        ]
        
        return len(set(recent_answers)) == 1


# ============================================================================
# PROPONENT DEBATER (DEBATER A)
# ============================================================================

class ProponentDebater(BaseDebater):
    """Debater A: Argues in favor of the proposition"""
    
    def __init__(self, client: LLMClient, debater_id: str = "debater_a"):
        super().__init__(
            debater_id=debater_id,
            role="proponent",
            client=client,
            system_prompt=DEBATER_A_SYSTEM_PROMPT
        )
    
    def generate_initial_position(self, 
                                 question: str,
                                 context: str = "",
                                 temperature: Optional[float] = None) -> DebaterPosition:
        """Generate initial position for the question"""
        
        user_prompt = DEBATER_A_INITIAL_POSITION_PROMPT.format(
            question=question,
            context=context if context else "None provided."
        )
        
        logger.info(f"{self.debater_id}: Generating initial position")
        response = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        self.initial_position = self.parse_initial_position(response)
        self.current_position = self.initial_position
        
        logger.info(f"{self.debater_id}: Initial position - Answer: {self.initial_position.answer}, "
                   f"Confidence: {self.initial_position.confidence}")
        
        return self.initial_position
    
    def generate_argument(self,
                         question: str,
                         debate_history: str,
                         round_number: int,
                         total_rounds: int,
                         temperature: Optional[float] = None) -> Dict[str, str]:
        """Generate argument for a debate round"""
        
        user_prompt = DEBATER_A_DEBATE_ROUND_PROMPT.format(
            question=question,
            debate_history=debate_history,
            round_number=round_number,
            total_rounds=total_rounds
        )
        
        logger.info(f"{self.debater_id}: Generating Round {round_number} argument")
        response = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        parsed = self.parse_debate_response(response)
        
        # Update current position
        if parsed["updated_answer"]:
            self.current_position = DebaterPosition(
                answer=parsed["updated_answer"],
                confidence=self.current_position.confidence,
                reasoning=parsed["argument"],
                arguments=self.current_position.arguments
            )
        
        return parsed


# ============================================================================
# OPPONENT DEBATER (DEBATER B)
# ============================================================================

class OpponentDebater(BaseDebater):
    """Debater B: Argues against the proposition"""
    
    def __init__(self, client: LLMClient, debater_id: str = "debater_b"):
        super().__init__(
            debater_id=debater_id,
            role="opponent",
            client=client,
            system_prompt=DEBATER_B_SYSTEM_PROMPT
        )
    
    def generate_initial_position(self,
                                 question: str,
                                 context: str = "",
                                 temperature: Optional[float] = None) -> DebaterPosition:
        """Generate initial position for the question"""
        
        user_prompt = DEBATER_B_INITIAL_POSITION_PROMPT.format(
            question=question,
            context=context if context else "None provided."
        )
        
        logger.info(f"{self.debater_id}: Generating initial position")
        response = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        self.initial_position = self.parse_initial_position(response)
        self.current_position = self.initial_position
        
        logger.info(f"{self.debater_id}: Initial position - Answer: {self.initial_position.answer}, "
                   f"Confidence: {self.initial_position.confidence}")
        
        return self.initial_position
    
    def generate_argument(self,
                         question: str,
                         debate_history: str,
                         round_number: int,
                         total_rounds: int,
                         temperature: Optional[float] = None) -> Dict[str, str]:
        """Generate counterargument for a debate round"""
        
        user_prompt = DEBATER_B_DEBATE_ROUND_PROMPT.format(
            question=question,
            debate_history=debate_history,
            round_number=round_number,
            total_rounds=total_rounds
        )
        
        logger.info(f"{self.debater_id}: Generating Round {round_number} argument")
        response = self.client.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=temperature
        )
        
        parsed = self.parse_debate_response(response)
        
        # Update current position
        if parsed["updated_answer"]:
            self.current_position = DebaterPosition(
                answer=parsed["updated_answer"],
                confidence=self.current_position.confidence,
                reasoning=parsed["argument"],
                arguments=self.current_position.arguments
            )
        
        return parsed


# ============================================================================
# DEBATE UTILITIES
# ============================================================================

def check_positions_match(position_a: DebaterPosition, position_b: DebaterPosition) -> bool:
    """Check if two positions represent the same answer"""
    return position_a.answer.lower().strip() == position_b.answer.lower().strip()

