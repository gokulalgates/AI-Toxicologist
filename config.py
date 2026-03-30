"""
Configuration management for AI Toxicologist application.

All configurable parameters are centralized here for easy modification.
"""

from typing import List, Optional
from dataclasses import dataclass, field
import os


@dataclass
class SearchConfig:
    """Configuration for PubMed search and literature retrieval"""
    # Literature limits
    # PERFORMANCE: Reduced defaults for faster analysis (can be overridden via env vars)
    max_abstracts_initial: int = 100  # Initial fetch from PubMed
    max_abstracts_analyze: int = 20  # Max abstracts to analyze after relevance filtering
    max_search_terms: int = 10  # Max search terms to use
    
    # Abstract processing
    # IMPROVEMENT: Increased context window - modern models (llama3.2, mixtral) support 128K tokens
    # No need to truncate abstracts - process full text for better accuracy
    abstract_truncate_length: int = 10000  # Increased from 1500 - process full abstracts
    relevance_check_truncate: int = 2000  # Increased from 800 for better relevance detection
    
    # PubMed settings
    entrez_email: str = os.getenv("ENTREZ_EMAIL", "ai.toxicologist@example.com")
    pubmed_retmax: int = 100  # Max results per PubMed query
    
    # Full-text retrieval
    enable_fulltext_retrieval: bool = True  # Enable full-text retrieval (set False if causing issues with VPN/institutional access)
    skip_fulltext_on_error: bool = True  # Skip full-text if retrieval fails (don't fail entire analysis)
    
    # Timeouts
    pubmed_timeout: int = 30  # Seconds to wait for PubMed API
    llm_timeout: int = 120  # Seconds to wait for LLM response
    fulltext_timeout: int = 60  # Seconds to wait for full-text download


@dataclass
class LLMConfig:
    """Configuration for LLM models and processing"""
    # IMPROVEMENT: Use larger, more capable models by default for better accuracy
    default_models: List[str] = field(default_factory=lambda: ["llama3.2", "mixtral"])
    available_models: List[str] = field(default_factory=lambda: [
        "llama3.1", "llama3.2", "llama3", "mistral", "mixtral", 
        "phi3", "gemma2", "qwen2.5"
    ])
    # IMPROVEMENT: Slight temperature increase (0.1-0.2) improves reasoning for ambiguous cases
    # while maintaining reproducibility. Use 0.0 for relevance checks (deterministic).
    temperature: float = 0.1  # Temperature for LLM analysis (0.1 = slight variation for better reasoning)
    temperature_relevance: float = 0.0  # Temperature for relevance checks (0.0 = deterministic)
    max_retries: int = 3  # Max retries for failed LLM calls
    retry_delay: float = 1.0  # Seconds to wait between retries
    
    # Parallel processing
    enable_parallel: bool = True  # Enable parallel processing for multi-reviewer
    max_workers: Optional[int] = None  # Max parallel workers (None = auto, uses GPU count if available)
    use_gpu: bool = True  # Enable GPU acceleration if available
    # PERFORMANCE: Increased default GPU layers for better speed (reduce if OOM errors occur)
    gpu_layers: int = 40  # Number of layers to offload to GPU (increased from 35, reduce if VRAM limited)


@dataclass
class AnalysisConfig:
    """Configuration for analysis and processing"""
    # Risk-of-bias
    enable_rob_default: bool = True
    rob_instrument: str = "OHAT"  # OHAT, ROBINS-I, RoB 2
    
    # Certainty grading
    enable_certainty_default: bool = True
    certainty_framework: str = "GRADE"  # GRADE or OHAT
    
    # Evidence extraction
    max_evidence_quotes_per_kc: int = 5  # Max quotes to extract per KC
    min_quote_length: int = 20  # Minimum quote length in characters
    
    # Multi-reviewer
    consensus_method: str = "weighted"  # majority or weighted (weighted uses model performance)
    min_agreement_threshold: float = 0.5  # Minimum agreement for consensus
    
    # Enhanced features
    enable_rag: bool = True  # Enable Retrieval-Augmented Generation
    enable_hierarchical: bool = True  # Enable hierarchical processing (prioritize sections)
    enable_confidence_scoring: bool = True  # Enable confidence scoring
    enable_active_learning: bool = True  # Enable active learning for abstract selection
    enable_enhanced_prompts: bool = True  # Enable enhanced prompts with better synonym recognition
    prompt_mode: str = "enhanced"  # "standard", "enhanced", or "liberal" (liberal is more permissive)
    filter_low_confidence: bool = False  # Filter out low-confidence predictions
    use_only_high_confidence: bool = False  # Use only high-confidence predictions
    confidence_threshold: float = 0.6  # Minimum confidence to keep


@dataclass
class OutputConfig:
    """Configuration for output and file management"""
    results_dir: str = "results"
    save_provenance: bool = True
    save_search_logs: bool = True
    save_study_records: bool = True
    
    # File naming
    timestamp_format: str = "%Y-%m-%dT%H-%M-%S"
    
    # Export formats
    export_formats: List[str] = field(default_factory=lambda: ["json", "csv"])
    export_dir: str = "exports"


@dataclass
class UIConfig:
    """Configuration for Gradio UI"""
    server_name: str = "0.0.0.0"
    server_port: int = 7862
    share: bool = False
    title: str = "AI Toxicologist: Publication-Grade Hepatotoxicity Assessment"
    
    # UI defaults
    default_chemical: str = ""
    show_advanced: bool = False


@dataclass
class AppConfig:
    """Main application configuration combining all sub-configs"""
    search: SearchConfig = field(default_factory=SearchConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    
    # Debug and logging
    debug: bool = False
    log_level: str = "INFO"
    log_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Load configuration from environment variables"""
        config = cls()
        
        # Override with environment variables if present
        config.search.max_abstracts_initial = int(
            os.getenv("MAX_ABSTRACTS_INITIAL", config.search.max_abstracts_initial)
        )
        config.search.max_abstracts_analyze = int(
            os.getenv("MAX_ABSTRACTS_ANALYZE", config.search.max_abstracts_analyze)
        )
        config.llm.temperature = float(
            os.getenv("LLM_TEMPERATURE", config.llm.temperature)
        )
        config.llm.temperature_relevance = float(
            os.getenv("LLM_TEMPERATURE_RELEVANCE", config.llm.temperature_relevance)
        )
        config.analysis.enable_enhanced_prompts = os.getenv(
            "ENABLE_ENHANCED_PROMPTS", str(config.analysis.enable_enhanced_prompts)
        ).lower() == "true"
        config.analysis.prompt_mode = os.getenv(
            "PROMPT_MODE", config.analysis.prompt_mode
        )
        config.debug = os.getenv("DEBUG", "False").lower() == "true"
        
        return config


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig.from_env()
    return _config


def set_config(config: AppConfig) -> None:
    """Set the global configuration instance"""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to defaults"""
    global _config
    _config = None
