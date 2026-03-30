# API Documentation

## Configuration API

### `config.py`

Centralized configuration management for the application.

#### `AppConfig`

Main configuration class containing all sub-configurations.

**Attributes:**
- `search: SearchConfig` - Search and literature retrieval settings
- `llm: LLMConfig` - LLM model and processing settings
- `analysis: AnalysisConfig` - Analysis and processing settings
- `output: OutputConfig` - Output and file management settings
- `ui: UIConfig` - Gradio UI settings
- `debug: bool` - Enable debug mode
- `log_level: str` - Logging level (INFO, DEBUG, etc.)

#### `get_config() -> AppConfig`

Get the global configuration instance (singleton pattern).

**Returns:** Current `AppConfig` instance

**Example:**
```python
from config import get_config

config = get_config()
max_abstracts = config.search.max_abstracts_initial
```

#### `set_config(config: AppConfig) -> None`

Set a custom configuration instance.

**Parameters:**
- `config: AppConfig` - Configuration to use

#### `reset_config() -> None`

Reset configuration to defaults.

## Exception API

### `exceptions.py`

Custom exception classes for better error handling.

#### Exception Hierarchy

```
ToxicologistException (base)
├── SearchError
├── ChemicalStandardizationError
├── LLMError
│   ├── LLMTimeoutError
│   └── LLMParseError
├── AnalysisError
├── ValidationError
├── ConfigurationError
├── ProvenanceError
└── MultiReviewerError
```

**Usage:**
```python
from exceptions import SearchError, LLMError

try:
    abstracts = fetch_pubmed_abstracts(terms)
except SearchError as e:
    print(f"Search failed: {e}")
```

## Utility API

### `utils.py`

Utility functions for retry logic, caching, and performance.

#### `@retry_with_backoff(max_retries=None, delay=None, backoff_factor=2.0, timeout=None, exceptions=(Exception,))`

Decorator for retrying functions with exponential backoff.

**Parameters:**
- `max_retries: Optional[int]` - Maximum retries (uses config if None)
- `delay: Optional[float]` - Initial delay in seconds
- `backoff_factor: float` - Delay multiplier after each retry
- `timeout: Optional[float]` - Maximum time to wait
- `exceptions: tuple` - Exceptions to catch and retry on

**Example:**
```python
from utils import retry_with_backoff

@retry_with_backoff(max_retries=3, delay=1.0)
def call_llm(prompt):
    return llm.invoke(prompt)
```

#### `@cache_result(ttl=None, key_func=None)`

Decorator to cache function results.

**Parameters:**
- `ttl: Optional[float]` - Time-to-live in seconds
- `key_func: Optional[Callable]` - Function to generate cache key

**Example:**
```python
from utils import cache_result

@cache_result(ttl=3600)
def expensive_computation(x):
    return x ** 2
```

#### `clear_cache() -> None`

Clear the in-memory cache.

#### `hash_text(text: str) -> str`

Generate SHA256 hash of text.

#### `truncate_text(text: str, max_length: int, suffix: str = "...") -> str`

Truncate text to max_length with suffix.

## Main Application API

### `app.py`

#### `standardize_chemical_name(chemical_name: str) -> Tuple[str, Optional[str], List[str]]`

Standardize chemical name using PubChem.

**Parameters:**
- `chemical_name: str` - Chemical name to standardize

**Returns:**
- `standardized_name: str` - Standardized IUPAC or common name
- `pubchem_cid: Optional[str]` - PubChem CID
- `search_terms: List[str]` - List of synonyms for searching

**Raises:**
- `ChemicalStandardizationError` - If PubChem lookup fails critically

#### `fetch_pubmed_abstracts(search_terms: List[str], max_results: Optional[int] = None) -> Tuple[List[Dict[str, str]], Dict]`

Fetch abstracts from PubMed using enhanced MeSH-aware search.

**Parameters:**
- `search_terms: List[str]` - List of chemical names/synonyms
- `max_results: Optional[int]` - Max results (uses config if None)

**Returns:**
- `abstracts: List[Dict]` - List of abstract dicts with keys: title, abstract, pmid, year, authors, journal
- `search_log: Dict` - Search log with query and metadata

**Raises:**
- `SearchError` - If PubMed search fails critically

#### `check_relevance(abstract_text: str, title: str, chemical_name: str, model_name: str = "llama3.1") -> bool`

Check if abstract is relevant to liver toxicity.

**Parameters:**
- `abstract_text: str` - Abstract text
- `title: str` - Paper title
- `chemical_name: str` - Chemical name
- `model_name: str` - LLM model to use

**Returns:**
- `bool` - True if relevant, False otherwise

**Raises:**
- `LLMError` - If LLM call fails (only in debug mode)

#### `analyze_abstract_with_llm(abstract_text: str, title: str, model_name: str = "llama3.1", prompt_hash: Optional[str] = None) -> Tuple[Dict, str]`

Analyze abstract against 12 KC definitions using LLM.

**Parameters:**
- `abstract_text: str` - Abstract text
- `title: str` - Paper title
- `model_name: str` - LLM model to use
- `prompt_hash: Optional[str]` - Prompt hash for provenance

**Returns:**
- `analysis_dict: Dict` - KC analysis results with keys:
  - `KC1` through `KC12`: bool (supported or not)
  - `KC1_status` through `KC12_status`: str (SUPPORTED/REFUTED/NOT_MENTIONED)
  - `reasoning: str` - Biological reasoning
  - `causal_links: List[Dict]` - Causal relationships
  - `evidence_quotes: Dict[str, List[str]]` - Evidence quotes per KC
- `prompt_hash: str` - Hash of prompt used

**Raises:**
- `LLMError` - If LLM processing fails after retries
- `LLMParseError` - If response parsing fails

#### `analyze_chemical(chemical_name: str, model_names: List[str] = None, enable_rob: bool = True, enable_certainty: bool = True, progress: Optional[Progress] = None) -> Tuple[str, plt.Figure, plt.Figure, Optional[plt.Figure], Optional[plt.Figure], Optional[plt.Figure], Optional[str]]`

Main analysis function orchestrating all steps.

**Parameters:**
- `chemical_name: str` - Chemical name to analyze
- `model_names: List[str]` - List of LLM models (enables multi-reviewer if >1)
- `enable_rob: bool` - Enable risk-of-bias assessment
- `enable_certainty: bool` - Enable certainty grading
- `progress: Optional[Progress]` - Gradio progress tracker

**Returns:**
- `summary_text: str` - Text summary
- `heatmap_fig: plt.Figure` - Evidence matrix heatmap
- `network_fig: plt.Figure` - Causal pathway network
- `prisma_fig: Optional[plt.Figure]` - PRISMA flow diagram
- `rob_heatmap_fig: Optional[plt.Figure]` - Risk-of-bias heatmap
- `rob_summary_fig: Optional[plt.Figure]` - Risk-of-bias summary
- `evidence_profiles_text: Optional[str]` - Evidence profile cards

## Configuration Reference

### SearchConfig

- `max_abstracts_initial: int = 100` - Initial fetch from PubMed
- `max_abstracts_analyze: int = 20` - Max abstracts to analyze after filtering
- `max_search_terms: int = 10` - Max search terms to use
- `abstract_truncate_length: int = 1500` - Truncate abstract for LLM
- `relevance_check_truncate: int = 800` - Truncate for relevance checking
- `entrez_email: str` - Email for NCBI Entrez API
- `pubmed_retmax: int = 100` - Max results per PubMed query
- `pubmed_timeout: int = 30` - Seconds to wait for PubMed API
- `llm_timeout: int = 120` - Seconds to wait for LLM response

### LLMConfig

- `default_models: List[str]` - Default models to use
- `available_models: List[str]` - Available model options
- `temperature: float = 0.0` - LLM temperature (0 = deterministic)
- `max_retries: int = 3` - Max retries for failed LLM calls
- `retry_delay: float = 1.0` - Seconds between retries
- `enable_parallel: bool = True` - Enable parallel processing
- `max_workers: Optional[int] = None` - Max parallel workers (None = auto)

### AnalysisConfig

- `enable_rob_default: bool = True` - Enable RoB by default
- `rob_instrument: str = "OHAT"` - RoB instrument (OHAT, ROBINS-I, RoB 2)
- `enable_certainty_default: bool = True` - Enable certainty grading by default
- `certainty_framework: str = "GRADE"` - Framework (GRADE or OHAT)
- `max_evidence_quotes_per_kc: int = 5` - Max quotes per KC
- `min_quote_length: int = 20` - Minimum quote length
- `consensus_method: str = "majority"` - Consensus method (majority or weighted)
- `min_agreement_threshold: float = 0.5` - Minimum agreement for consensus

### OutputConfig

- `results_dir: str = "results"` - Results directory
- `save_provenance: bool = True` - Save provenance records
- `save_search_logs: bool = True` - Save search logs
- `save_study_records: bool = True` - Save study records
- `timestamp_format: str = "%Y-%m-%dT%H-%M-%S"` - Timestamp format
- `export_formats: List[str]` - Export formats (json, csv)
- `export_dir: str = "exports"` - Export directory
