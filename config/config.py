"""
Configuration file for LLM Debate with Judge Pipeline System
Contains all hyperparameters, model settings, and experiment configurations
"""

import os
from typing import Dict, Any
from dataclasses import dataclass

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

@dataclass
class ModelConfig:
    """Configuration for LLM models"""
    # API Provider: "anthropic", "openai", or "mock"
    provider: str = "anthropic"
    
    # Primary models for debaters and judge
    debater_model: str = "claude-3-haiku-20240307"  # Fast & efficient
    judge_model: str = "claude-3-haiku-20240307"  # Lightweight for judgment
    
    # Alternative models for baselines
    baseline_model: str = "claude-3-haiku-20240307"
    
    # Temperature and sampling
    temperature: float = 0.7
    top_p: float = 0.95
    
    # Token limits
    max_tokens_debater: int = 500
    max_tokens_judge: int = 800
    max_tokens_baseline: int = 300
    
    # API Keys
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0


# ============================================================================
# DEBATE CONFIGURATION
# ============================================================================

@dataclass
class DebateConfig:
    """Configuration for debate protocol"""
    # Round configuration
    num_rounds: int = 5  # N >= 3 as per assignment
    min_rounds: int = 3
    max_rounds: int = 10
    
    # Stopping criteria
    enable_early_stopping: bool = True
    convergence_rounds: int = 2  # Stop if both debaters agree for 2 consecutive rounds
    
    # Debate roles
    debater_a_role: str = "proponent"
    debater_b_role: str = "opponent"
    
    # Task domain
    task_domain: str = "commonsense_qa"  # ARC-Challenge from Hugging Face
    
    # Dataset configuration
    sample_size: int = 200  # 100-200 as per assignment (using ARC-Challenge from Hugging Face)
    final_sample_size: int = 200  # 100-200 as per assignment
    dataset_name: str = "arc_challenge"  # ARC-Challenge dataset


# ============================================================================
# JUDGE/JURY CONFIGURATION
# ============================================================================

@dataclass
class JudgeConfig:
    """Configuration for single judge"""
    judge_id: str = "judge_1"
    enable_cot_reasoning: bool = True
    confidence_scale: int = 5  # 1-5 scale as per assignment
    
    # Judge reasoning requirements
    require_strongest_argument: bool = True
    require_weakest_argument: bool = True


@dataclass
class JuryConfig:
    """Configuration for jury panel (BONUS FEATURE)"""
    # Jury composition
    num_judges: int = 3  # 3+ judges as per bonus assignment
    jury_model: str = "gpt-4"
    judges: list = None  # Will be populated dynamically
    
    # Deliberation configuration
    enable_deliberation: bool = True
    deliberation_rounds: int = 2
    deliberation_timeout: int = 120  # seconds
    
    # Voting mechanism
    voting_strategy: str = "majority"  # "majority", "consensus", "weighted"
    disagreement_threshold: float = 0.5  # Flag if disagreement >= threshold
    
    # Analysis
    analyze_panel_disagreement: bool = True
    correlate_with_difficulty: bool = True
    analyze_deliberation_impact: bool = True
    
    def __post_init__(self):
        if self.judges is None:
            self.judges = [f"judge_{i+1}" for i in range(self.num_judges)]


# ============================================================================
# BASELINE CONFIGURATION
# ============================================================================

@dataclass
class BaselineConfig:
    """Configuration for baseline comparisons"""
    # Direct QA baseline
    enable_direct_qa: bool = True
    direct_qa_samples: int = 1  # Single CoT response
    
    # Self-Consistency baseline
    enable_self_consistency: bool = True
    self_consistency_samples: int = 5  # N samples for majority vote
    
    # Few-shot configuration
    num_few_shot_examples: int = 3
    few_shot_enabled: bool = False  # Start with zero-shot


# ============================================================================
# LOGGING & EVALUATION CONFIGURATION
# ============================================================================

@dataclass
class LoggingConfig:
    """Configuration for logging and output"""
    # Log directories
    log_dir: str = "logs"
    output_dir: str = "outputs"
    archive_dir: str = "outputs/archive"
    
    # Log format
    save_transcripts: bool = True
    save_json: bool = True
    save_metrics: bool = True
    transcript_format: str = "json"  # "json", "txt", "markdown"
    
    # Verbosity
    verbose: bool = True
    debug_mode: bool = False
    log_all_llm_calls: bool = True
    
    # Performance tracking
    track_api_costs: bool = True
    track_token_usage: bool = True


@dataclass
class EvaluationConfig:
    """Configuration for evaluation metrics"""
    # Metrics to compute
    compute_accuracy: bool = True
    compute_f1: bool = True
    compute_precision_recall: bool = True
    compute_confidence_calibration: bool = True
    
    # Statistical testing
    enable_significance_testing: bool = True
    significance_level: float = 0.05
    
    # Analysis
    analyze_debate_quality: bool = True
    analyze_argument_strength: bool = True
    min_confidence_score: int = 1
    max_confidence_score: int = 5


# ============================================================================
# UI CONFIGURATION
# ============================================================================

@dataclass
class UIConfig:
    """Configuration for web UI"""
    enable_ui: bool = True
    ui_port: int = 8000
    ui_host: str = "localhost"
    
    # UI features
    show_debate_rounds: bool = True
    show_judge_reasoning: bool = True
    show_jury_deliberation: bool = True
    enable_real_time_updates: bool = True
    
    # Cosmetic settings (vibe coding)
    theme: str = "dark"  # "light", "dark"
    animation_enabled: bool = True
    streaming_enabled: bool = False  # Stream LLM responses


# ============================================================================
# MAIN CONFIGURATION CLASS
# ============================================================================

@dataclass
class Config:
    """Master configuration class combining all sub-configs"""
    
    # Sub-configurations
    model: ModelConfig = None
    debate: DebateConfig = None
    judge: JudgeConfig = None
    jury: JuryConfig = None
    baseline: BaselineConfig = None
    logging: LoggingConfig = None
    evaluation: EvaluationConfig = None
    ui: UIConfig = None
    
    # Experiment metadata
    experiment_name: str = "llm_debate_with_jury"
    experiment_version: str = "1.0"
    timestamp: str = ""
    use_jury: bool = True  # Enable jury panel (bonus feature)
    use_single_judge: bool = True  # Also run single judge for comparison
    
    def __post_init__(self):
        if self.model is None:
            self.model = ModelConfig()
        if self.debate is None:
            self.debate = DebateConfig()
        if self.judge is None:
            self.judge = JudgeConfig()
        if self.jury is None:
            self.jury = JuryConfig()
        if self.baseline is None:
            self.baseline = BaselineConfig()
        if self.logging is None:
            self.logging = LoggingConfig()
        if self.evaluation is None:
            self.evaluation = EvaluationConfig()
        if self.ui is None:
            self.ui = UIConfig()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for serialization"""
        return {
            "model": self.model.__dict__,
            "debate": self.debate.__dict__,
            "judge": self.judge.__dict__,
            "jury": self.jury.__dict__,
            "baseline": self.baseline.__dict__,
            "logging": self.logging.__dict__,
            "evaluation": self.evaluation.__dict__,
            "ui": self.ui.__dict__,
            "experiment_name": self.experiment_name,
            "experiment_version": self.experiment_version,
            "use_jury": self.use_jury,
            "use_single_judge": self.use_single_judge,
        }


# ============================================================================
# DEFAULT CONFIGURATION INSTANCE
# ============================================================================

def get_default_config() -> Config:
    """Get default configuration"""
    return Config()


def get_debug_config() -> Config:
    """Get configuration for debugging (smaller sample sizes)"""
    config = Config()
    config.debate.sample_size = 5
    config.debate.final_sample_size = 5
    config.debate.num_rounds = 3
    config.baseline.self_consistency_samples = 2
    config.logging.debug_mode = True
    config.logging.verbose = True
    return config


def get_production_config() -> Config:
    """Get configuration for production (full experiment with 200 ARC-Challenge questions)"""
    config = Config()
    config.debate.sample_size = 200  # Load 200 questions from ARC-Challenge (Hugging Face)
    config.debate.final_sample_size = 200  # 100-200 as per assignment
    config.debate.num_rounds = 5
    config.baseline.self_consistency_samples = 5
    config.logging.verbose = False
    config.logging.debug_mode = False
    return config
