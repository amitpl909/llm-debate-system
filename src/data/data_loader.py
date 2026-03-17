"""
Data loading utilities
Load and manage datasets for debate tasks
"""

import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class DebateQuestion:
    """Represents a single question for debate"""
    question_id: str
    question: str
    answer: str  # Ground truth
    context: Optional[str] = None
    difficulty: Optional[str] = None  # "easy", "medium", "hard"
    source: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "question_id": self.question_id,
            "question": self.question,
            "answer": self.answer,
            "context": self.context,
            "difficulty": self.difficulty,
            "source": self.source,
            "metadata": self.metadata or {}
        }


# ============================================================================
# DATA LOADER
# ============================================================================

class DataLoader:
    """Load and manage debate questions"""
    
    def __init__(self):
        self.questions: Dict[str, DebateQuestion] = {}
        self.total_loaded = 0
    
    def load_json_file(self, filepath: str) -> List[DebateQuestion]:
        """Load questions from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            questions = []
            
            if isinstance(data, list):
                # List of questions
                for item in data:
                    question = self._parse_question_item(item)
                    if question:
                        questions.append(question)
                        self.questions[question.question_id] = question
            
            elif isinstance(data, dict):
                # Dictionary where values are questions
                for key, item in data.items():
                    question = self._parse_question_item(item, question_id=key)
                    if question:
                        questions.append(question)
                        self.questions[question.question_id] = question
            
            self.total_loaded += len(questions)
            logger.info(f"Loaded {len(questions)} questions from {filepath}")
            return questions
        
        except Exception as e:
            logger.error(f"Error loading {filepath}: {str(e)}")
            return []
    
    def _parse_question_item(self, item: Dict[str, Any], question_id: Optional[str] = None) -> Optional[DebateQuestion]:
        """Parse a single question item"""
        try:
            qid = question_id or item.get("id") or item.get("question_id") or str(len(self.questions))
            question_text = item.get("question") or item.get("text") or ""
            answer_text = item.get("answer") or item.get("label") or ""
            
            if not question_text or not answer_text:
                logger.warning(f"Skipping item {qid}: missing question or answer")
                return None
            
            return DebateQuestion(
                question_id=str(qid),
                question=question_text,
                answer=str(answer_text),
                context=item.get("context") or item.get("passage"),
                difficulty=item.get("difficulty"),
                source=item.get("source"),
                metadata=item.get("metadata", {})
            )
        
        except Exception as e:
            logger.warning(f"Error parsing question item: {str(e)}")
            return None
    
    def get_sample(self, num_questions: int, seed: Optional[int] = None) -> List[DebateQuestion]:
        """Get a random sample of questions"""
        import random
        
        if seed is not None:
            random.seed(seed)
        
        available = list(self.questions.values())
        num_to_get = min(num_questions, len(available))
        
        sample = random.sample(available, num_to_get)
        logger.info(f"Sampled {num_to_get} questions from {len(available)} available")
        
        return sample
    
    def get_by_difficulty(self, difficulty: str) -> List[DebateQuestion]:
        """Get questions by difficulty level"""
        return [q for q in self.questions.values() if q.difficulty == difficulty]
    
    def get_all(self) -> List[DebateQuestion]:
        """Get all loaded questions"""
        return list(self.questions.values())
    
    def filter_questions(self, predicate) -> List[DebateQuestion]:
        """Filter questions using a predicate function"""
        return [q for q in self.questions.values() if predicate(q)]


# ============================================================================
# BUILT-IN SAMPLE DATASETS
# ============================================================================

class SampleDatasets:
    """Built-in sample datasets for testing"""
    
    @staticmethod
    def load_strategy_qa_from_github(num_questions: int = 200) -> List[DebateQuestion]:
        """Load StrategyQA dataset from GitHub or fallback to ARC-Challenge from Hugging Face"""
        try:
            # Try to use datasets library to load from Hugging Face
            from datasets import load_dataset
            
            logger.info(f"Loading ARC-Challenge from Hugging Face ({num_questions} questions)...")
            dataset = load_dataset("ai2_arc", "ARC-Challenge", split="train")
            
            questions = []
            for idx, item in enumerate(dataset):
                if idx >= num_questions:
                    break
                    
                try:
                    # Extract the answer text from choices
                    answer_key = item.get("answerKey", "")
                    choices_dict = item.get("choices", {})
                    
                    # choices is a dict with 'text' and 'label' keys
                    choices_text = choices_dict.get("text", []) if isinstance(choices_dict, dict) else []
                    
                    # Find the answer text based on the key (A, B, C, D)
                    answer_text = ""
                    if answer_key and choices_text:
                        # Map A->0, B->1, C->2, D->3
                        choice_idx = ord(answer_key) - ord('A')
                        if 0 <= choice_idx < len(choices_text):
                            answer_text = choices_text[choice_idx]
                    
                    question = DebateQuestion(
                        question_id=f"arc_challenge_{idx}",
                        question=item.get("question", "").strip(),
                        answer=answer_text if answer_text else answer_key,  # Use text if available, else key
                        difficulty="medium",  # ARC doesn't specify difficulty
                        source="arc_challenge",
                        metadata={
                            "original_id": item.get("id"),
                            "choices": choices_text,
                            "answer_key": answer_key
                        }
                    )
                    if question.question and question.answer:
                        questions.append(question)
                except Exception as e:
                    logger.warning(f"Error parsing ARC item {idx}: {str(e)}")
                    continue
            
            logger.info(f"Loaded {len(questions)} questions from ARC-Challenge")
            return questions
        
        except ImportError:
            logger.warning("datasets library not available, using sample dataset...")
            return SampleDatasets.get_commonsense_qa_sample()
        except Exception as e:
            logger.error(f"Error loading from Hugging Face: {str(e)}")
            logger.info("Falling back to sample dataset...")
            return SampleDatasets.get_commonsense_qa_sample()
    
    @staticmethod
    def _load_from_github_url(num_questions: int = 200) -> List[DebateQuestion]:
        """Attempt to load from GitHub URL as fallback"""
        return SampleDatasets.get_commonsense_qa_sample()
    
    @staticmethod
    def get_commonsense_qa_sample() -> List[DebateQuestion]:
        """Get sample of commonsense QA questions"""
        questions = [
            DebateQuestion(
                question_id="cqa_1",
                question="Did the Roman Empire exist at the same time as the Mayan civilization?",
                answer="Yes",
                difficulty="medium",
                source="strategy_qa",
                context="Roman Empire: ~27 BC–476 AD. Mayan civilization: ~2000 BC–1500s AD."
            ),
            DebateQuestion(
                question_id="cqa_2",
                question="Can a penguin swim faster than a salmon?",
                answer="No",
                difficulty="medium",
                source="strategy_qa",
                context="Penguins max out around 6 mph. Salmon can swim up to 30 mph."
            ),
            DebateQuestion(
                question_id="cqa_3",
                question="Is a tomato technically a fruit?",
                answer="Yes",
                difficulty="easy",
                source="strategy_qa",
                context="Botanically, a tomato is the berry of the tomato plant."
            ),
            DebateQuestion(
                question_id="cqa_4",
                question="Would a typical house cat be able to defeat a fox in a fight?",
                answer="No",
                difficulty="medium",
                source="strategy_qa",
                context="Foxes are larger (4-5 kg vs 2-5 kg) with more predatory instinct."
            ),
            DebateQuestion(
                question_id="cqa_5",
                question="Is honey considered vegan?",
                answer="No",
                difficulty="easy",
                source="strategy_qa",
                context="Honey is produced by bees; vegans avoid it due to animal exploitation concerns."
            ),
            DebateQuestion(
                question_id="cqa_6",
                question="Did Albert Einstein ever win a Nobel Prize in Physics?",
                answer="Yes",
                difficulty="easy",
                source="strategy_qa",
                context="Einstein won the Nobel Prize in Physics in 1921 for his work on the photoelectric effect."
            ),
            DebateQuestion(
                question_id="cqa_7",
                question="Is the Great Wall of China visible from space?",
                answer="No",
                difficulty="medium",
                source="strategy_qa",
                context="Despite popular belief, the Great Wall is not visible from space with naked eye."
            ),
            DebateQuestion(
                question_id="cqa_8",
                question="Can octopuses taste with their arms?",
                answer="Yes",
                difficulty="medium",
                source="strategy_qa",
                context="Octopus arms have taste receptors allowing them to taste what they touch."
            ),
            DebateQuestion(
                question_id="cqa_9",
                question="Is Australia considered a continent or a country?",
                answer="Both",
                difficulty="easy",
                source="strategy_qa",
                context="Australia is both a country and a continent (Oceania)."
            ),
            DebateQuestion(
                question_id="cqa_10",
                question="Would it take longer to drive across Australia or the United States?",
                answer="Australia",
                difficulty="medium",
                source="strategy_qa",
                context="Australia is broader east-west (~4000 km) vs US (~4500 km) but depends on route."
            ),
        ]
        return questions
    
    @staticmethod
    def get_fact_verification_sample() -> List[DebateQuestion]:
        """Get sample of fact verification questions"""
        questions = [
            DebateQuestion(
                question_id="fv_1",
                question="Vitamin C supplementation prevents the common cold in the general population.",
                answer="No",
                difficulty="medium",
                source="scifact",
                context="Meta-analyses show no statistically significant prevention effect in general population."
            ),
            DebateQuestion(
                question_id="fv_2",
                question="Coffee consumption increases the risk of heart disease.",
                answer="No",
                difficulty="medium",
                source="scifact",
                context="Recent studies show moderate coffee consumption is not associated with increased heart disease risk."
            ),
            DebateQuestion(
                question_id="fv_3",
                question="Vaccines can cause autism.",
                answer="No",
                difficulty="easy",
                source="scifact",
                context="The original fraudulent study has been retracted. Hundreds of studies have found no link."
            ),
            DebateQuestion(
                question_id="fv_4",
                question="GMO foods are inherently dangerous to human health.",
                answer="No",
                difficulty="medium",
                source="scifact",
                context="Major scientific organizations confirm GMOs are safe; no credible evidence of harm."
            ),
            DebateQuestion(
                question_id="fv_5",
                question="Climate change is primarily caused by human activities.",
                answer="Yes",
                difficulty="medium",
                source="scifact",
                context="97%+ of climate scientists agree human activities are the primary cause of recent warming."
            ),
        ]
        return questions
    
    @staticmethod
    def get_all_samples() -> List[DebateQuestion]:
        """Get combined sample dataset"""
        return SampleDatasets.get_commonsense_qa_sample() + SampleDatasets.get_fact_verification_sample()


# ============================================================================
# DATASET FACTORY
# ============================================================================

def create_dataset(dataset_type: str = "commonsense_qa", 
                  sample_size: int = 200,
                  seed: Optional[int] = None) -> List[DebateQuestion]:
    """
    Factory function to create datasets
    
    Args:
        dataset_type: "commonsense_qa" (loads from GitHub), "fact_verification", or "mixed"
        sample_size: Number of questions to return
        seed: Random seed for reproducibility
    
    Returns:
        List of DebateQuestion objects
    """
    
    if dataset_type == "commonsense_qa":
        # Load from GitHub StrategyQA
        questions = SampleDatasets.load_strategy_qa_from_github(num_questions=sample_size)
    elif dataset_type == "fact_verification":
        questions = SampleDatasets.get_fact_verification_sample()
    elif dataset_type == "mixed":
        questions = SampleDatasets.get_all_samples()
    else:
        raise ValueError(f"Unknown dataset type: {dataset_type}")
    
    # Sample if needed
    import random
    if seed is not None:
        random.seed(seed)
    
    if sample_size < len(questions):
        questions = random.sample(questions, sample_size)
    
    logger.info(f"Created dataset: {dataset_type} with {len(questions)} questions")
    return questions
