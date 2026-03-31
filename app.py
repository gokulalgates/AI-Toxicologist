"""
AI Toxicologist: Systematic Literature Review for Hepatotoxicity Assessment
Based on "Key Characteristics of Human Hepatotoxicants" (Rusyn et al., 2021)

Systematic Review System with PRISMA compliance, Risk-of-Bias assessment,
and provenance tracking.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

import gradio as gr
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import pubchempy as pcp
import seaborn as sns
from Bio import Entrez
from gradio import Progress
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

HELP_CONTENT_TEMPLATE = """
# AI Toxicologist — Help & Documentation

## 🚀 Getting Started

This application performs a **PRISMA-compliant systematic literature review** to assess the hepatotoxicity potential of chemicals based on the [Key Characteristics of Human Hepatotoxicants](https://doi.org/10.1093/toxsci/kfab045) (Rusyn et al., 2021).

---

## 🏃 How to Run the Application

### 1. Install and Start Ollama

AI Toxicologist uses [Ollama](https://ollama.ai) to run large language models locally. Download and install it, then ensure the Ollama server is running in the background.

### 2. Pull Required Models

Open a terminal and pull the models you wish to use:

```bash
ollama pull llama3.1
ollama pull llama3.2
ollama pull mixtral
# Optional additional models:
# ollama pull mistral
# ollama pull phi3
# ollama pull gemma2
# ollama pull qwen2.5
```

> **Recommended:** Use 2–3 models (e.g., `llama3.2`, `mixtral`, `mistral`) for Multi-Reviewer Mode.

### 3. Launch the Application

Navigate to the project root and run:

```bash
python app.py
```

A Gradio web server will start. Open the displayed link (usually `http://127.0.0.1:7860/`) in your browser.

---

## ✅ Features

| Feature | Description |
|---|---|
| **PRISMA 2020 Compliance** | Flow diagrams and structured reporting |
| **Enhanced Search** | MeSH-aware queries with CAS/CID support |
| **Evidence Quotes** | Sentence-level evidence extraction per KC |
| **Provenance Tracking** | Complete audit trail for reproducibility |
| **Risk-of-Bias Assessment** | LLM-based OHAT/ROBINS-I assessment with visualizations |
| **Certainty Grading** | GRADE/OHAT-style certainty ratings per KC |
| **Evidence Profile Cards** | Human-readable evidence summaries |
| **Causal Pathway Analysis** | Directed graphs showing mechanistic relationships |
| **Multi-Reviewer Mode** | Multiple models as independent reviewers with consensus |
| **Configurable Limits** | Adjustable literature retrieval and analysis limits |

---

## ⚙️ Current Configuration

| Parameter | Value |
|---|---|
| Initial PubMed Fetch | Up to **{MAX_ABSTRACTS_INITIAL}** abstracts |
| Analysis Limit | Up to **{MAX_ABSTRACTS_ANALYZE}** relevant abstracts |
| Search Terms | Up to **{MAX_SEARCH_TERMS}** synonyms |
| Parallel Processing | {PARALLEL_PROCESSING_STATUS} |
| GPU Acceleration | {GPU_ACCELERATION_STATUS} ({GPU_COUNT} GPU(s) detected) |
| MPI Support | {MPI_SUPPORT_STATUS} |

---

## 🔄 How It Works

1. **The Librarian** — Standardizes the chemical name via PubChem, fetches PubMed abstracts with MeSH terms
2. **The Gatekeeper** — Filters abstracts for liver toxicity relevance using the LLM
3. **The Analyst** — Analyzes each abstract against the 12 Key Characteristics, extracting evidence quotes
4. **Multi-Reviewer** — Each selected model independently reviews all papers
5. **Consensus** — Results are consolidated using majority voting; Cohen's κ calculated
6. **Ranking** — Papers ranked by consensus strength and evidence quality
7. **The Architect** — Generates Evidence Matrix, Causal Pathway Network, and PRISMA flow diagram

---

## 🤝 Using the Interface

1. **Enter a Chemical Name** — Type the chemical you want to analyze (e.g., `acetaminophen`, `carbon tetrachloride`)
2. **Select Models** — Choose one or more Ollama models from the checkbox group
   - Selecting multiple models activates **Multi-Reviewer Mode**
3. **Enable Optional Features**
   - *Risk-of-Bias Assessment* — Assess study-level risk of bias
   - *Certainty Grading* — Calculate certainty of evidence per KC
4. **Click "🔍 Analyze Chemical"** to start the review
5. **Review Outputs**
   - Analysis Summary
   - Evidence Matrix Heatmap
   - Mechanistic Pathway Network
   - PRISMA 2020 Flow Diagram
   - Risk-of-Bias Heatmap & Summary *(if enabled)*
   - Evidence Profile Cards
   - Risk-of-Bias Assessments table *(click a row to view the abstract)*
6. **Chat with Abstracts** — Use the chatbot to query the analyzed literature

---

## ✨ Multi-Reviewer Mode

- Higher reliability through consensus across models
- Inter-model agreement statistics (Cohen's κ)
- Papers ranked by consensus strength
- Identifies high-confidence vs. disputed findings

> For best results, use 2–3 models (e.g., `llama3.2`, `mixtral`, `mistral`). Multi-reviewer mode takes longer but produces more reliable results.

---

## 🛠️ Advanced Configuration (Environment Variables)

Set these before running `app.py` to override defaults:

| Variable | Default | Description |
|---|---|---|
| `MAX_ABSTRACTS_INITIAL` | {MAX_ABSTRACTS_INITIAL_DEFAULT} | Initial PubMed fetch limit |
| `MAX_ABSTRACTS_ANALYZE` | {MAX_ABSTRACTS_ANALYZE_DEFAULT} | Analysis limit after relevance filtering |
| `LLM_TEMPERATURE` | {LLM_TEMPERATURE_DEFAULT} | LLM creativity/randomness |
"""

# Import enhanced modules
from certainty_grading import assess_certainty_per_kc
from evidence_models import (
    PRISMARecord,
)
from evidence_profiles import create_all_evidence_profiles
from fulltext_retrieval import fetch_fulltext, has_fulltext_available
from hepatotoxicity_agent import HepatotoxicityAgent
from multi_reviewer import (
    consolidate_kc_analyses,
    rank_papers_by_consensus,
)
from plot_utils import save_all_plots
from prisma import create_prisma_flow_diagram, generate_prisma_text_summary
from provenance import (
    create_provenance_record,
    hash_prompt,
    save_provenance,
    save_search_log,
    save_study_record,
)
from risk_of_bias import (
    assess_rob_with_llm,
    assess_roh_ohat,
    calculate_rob_summary_stats,
)
from rob_visualization import create_rob_heatmap_figure, create_rob_summary_figure
from search_enhanced import fetch_pubmed_enhanced, get_chemical_synonyms_enhanced

# Load prompt mode from file BEFORE importing config (so env vars are set)
# Note: os is already imported above, no need to import again
env_file = ".prompt_mode"
if os.path.exists(env_file):
    try:
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    except Exception:
        pass  # Ignore errors, use defaults

from config import get_config, reset_config

# Reset config singleton to ensure env vars are picked up
reset_config()
from active_learning import select_abstracts_for_analysis
from calibration import calibrate_predictions, get_calibration_model
from causal_reasoning import enhance_causal_reasoning_prompt, validate_all_causal_links

# Import new enhancement modules
from confidence_scoring import filter_low_confidence_predictions
from exceptions import (
    AnalysisError,
    ChemicalStandardizationError,
    LLMError,
    LLMParseError,
    LLMTimeoutError,
    SearchError,
)
from gpu_utils import check_gpu_available, get_gpu_count, get_optimal_workers, setup_gpu_environment
from hierarchical_processing import prioritize_text_for_analysis
from prompt_improvements import (
    get_acetaminophen_specific_prompt,
    get_enhanced_prompt_with_synonyms,
    get_liberal_prompt,
)
from prompt_templates import get_prompt_for_abstract
from rag_system import add_to_example_database, get_rag_system
from utils import retry_with_backoff

# Optional DSPy optimized classifier (Phase 1 RL)
_dspy_classifier = None
_dspy_available = False
try:
    from dspy_optimizer import (
        is_optimized_program_available,
        load_optimized_program,
        predict_with_optimized,
    )
    _dspy_available = True
except ImportError:
    pass  # DSPy not installed — use standard prompts

# Optional MPI support
try:
    from mpi_support import get_mpi_rank, get_mpi_size, is_mpi_available, print_mpi_info
    MPI_ENABLED = is_mpi_available()
except (ImportError, OSError, RuntimeError, Exception) as e:
    # Catch all MPI-related errors including missing libmpi.so (OSError)
    MPI_ENABLED = False
    def print_mpi_info():
        print("MPI not available or failed to load. Running in single-process mode.")
    # Only print warning if it's not a simple ImportError (module not installed)
    if not isinstance(e, ImportError):
        print(f"⚠️  MPI support disabled: {type(e).__name__}: {e}")

# Configure matplotlib for non-interactive backend
plt.switch_backend('Agg')

# Get global configuration
config = get_config()

# Set up logging
logger = logging.getLogger(__name__)
if not logger.handlers:

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO if not config.debug else logging.DEBUG)

# Load DSPy optimized classifier if available (Phase 1 RL)
def _load_dspy_classifier():
    global _dspy_classifier
    if not _dspy_available:
        return
    if not is_optimized_program_available():
        return
    try:
        model_name = config.llm.model_name
        _dspy_classifier = load_optimized_program(model_name)
        if _dspy_classifier:
            print(f"✅ DSPy optimized KC classifier loaded (model: {model_name})")
    except Exception as e:
        logger.warning(f"Could not load DSPy classifier: {e}")

_load_dspy_classifier()

# Only override if not set via environment variable
if os.getenv("MAX_ABSTRACTS_ANALYZE") is None:
    # Default to 500 if not configured, but respect user config
    if config.search.max_abstracts_analyze == 20:  # Default value
        config.search.max_abstracts_analyze = 500

# Setup GPU environment if available
gpu_info = check_gpu_available()
gpu_count = get_gpu_count()
if gpu_info['available'] and config.llm.use_gpu:
    setup_gpu_environment()
    print(f"GPU detected: {gpu_info}, Count: {gpu_count}")
    print("GPU acceleration enabled for Ollama")
    # Set GPU layers for Ollama
    os.environ['OLLAMA_GPU_LAYERS'] = str(config.llm.gpu_layers)
else:
    print("No GPU detected or GPU disabled, using CPU")

# Print MPI info if available
if MPI_ENABLED:
    print_mpi_info()

# KC Definitions (Source of Truth)
KC_DEFINITIONS = {
    "KC1": "Is reactive and/or is metabolized (bioactivated) to reactive moieties.",
    "KC2": "Causes death (apoptosis and/or necrosis) of liver cells.",
    "KC3": "Affects liver cell proliferation and/or tissue regeneration.",
    "KC4": "Disrupts transport function.",
    "KC5": "Induces oxidative stress (imbalance between ROS and antioxidants).",
    "KC6": "Triggers immune-mediated responses in liver.",
    "KC7": "Causes mitochondrial dysfunction.",
    "KC8": "Activates stress signaling pathways.",
    "KC9": "Causes cholestasis.",
    "KC10": "Disrupts cellular cytoskeleton.",
    "KC11": "Causes liver fibrosis.",
    "KC12": "Disrupts liver metabolism, including of lipids and proteins."
}

KC_NAMES = {
    "KC1": "Reactive/Bioactivation",
    "KC2": "Cell Death",
    "KC3": "Proliferation/Regeneration",
    "KC4": "Transport Disruption",
    "KC5": "Oxidative Stress",
    "KC6": "Immune Response",
    "KC7": "Mitochondrial Dysfunction",
    "KC8": "Stress Signaling",
    "KC9": "Cholestasis",
    "KC10": "Cytoskeleton Disruption",
    "KC11": "Liver Fibrosis",
    "KC12": "Metabolism Disruption"
}

# Pydantic models for structured output (keeping backward compatibility)
class CausalLink(BaseModel):
    """Represents a causal relationship between two KCs"""
    source: str = Field(description="Source KC (e.g., 'KC1')")
    target: str = Field(description="Target KC (e.g., 'KC5')")
    evidence: str = Field(description="Text evidence from abstract supporting this causal link")
    strength: str = Field(default="MODERATE", description="Strength: 'STRONG', 'MODERATE', or 'WEAK'")


class KCAnalysis(BaseModel):
    """Analysis of an abstract against Key Characteristics with causal reasoning"""
    # KC presence with status: SUPPORTED, REFUTED, or NOT_MENTIONED
    kc1_status: str = Field(default="NOT_MENTIONED", description="KC1: Reactive/Bioactivation - Values: 'SUPPORTED', 'REFUTED', or 'NOT_MENTIONED'")
    kc2_status: str = Field(default="NOT_MENTIONED", description="KC2: Cell Death - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc3_status: str = Field(default="NOT_MENTIONED", description="KC3: Proliferation/Regeneration - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc4_status: str = Field(default="NOT_MENTIONED", description="KC4: Transport Disruption - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc5_status: str = Field(default="NOT_MENTIONED", description="KC5: Oxidative Stress - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc6_status: str = Field(default="NOT_MENTIONED", description="KC6: Immune Response - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc7_status: str = Field(default="NOT_MENTIONED", description="KC7: Mitochondrial Dysfunction - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc8_status: str = Field(default="NOT_MENTIONED", description="KC8: Stress Signaling - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc9_status: str = Field(default="NOT_MENTIONED", description="KC9: Cholestasis - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc10_status: str = Field(default="NOT_MENTIONED", description="KC10: Cytoskeleton Disruption - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc11_status: str = Field(default="NOT_MENTIONED", description="KC11: Liver Fibrosis - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")
    kc12_status: str = Field(default="NOT_MENTIONED", description="KC12: Metabolism Disruption - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'")

    # Chain-of-thought reasoning for each KC
    reasoning: Union[str, Dict[str, List[str]]] = Field(default="No reasoning provided", description="Step-by-step reasoning explaining the biological mechanisms described and how they relate to KCs")

    # Causal links between KCs
    causal_links: List[CausalLink] = Field(default_factory=list, description="List of causal relationships between KCs explicitly stated in the text")

    # Dose-response information
    dose_response: List[str] = Field(
        default_factory=list,
        description="Dose-response information extracted from text (e.g., '50 mg/kg')"
    )

    # Enhanced: Evidence quotes (optional for backward compatibility)
    evidence_quotes: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Evidence quotes keyed by KC (e.g., 'KC1': ['quote1', 'quote2'])"
    )


def standardize_chemical_name(chemical_name: str) -> Tuple[str, Optional[str], List[str]]:
    """
    Step A.1: Standardize chemical name using PubChem and get synonyms
    Returns: (standardized_name, pubchem_cid, search_terms)
    
    Raises:
        ChemicalStandardizationError: If PubChem lookup fails critically
    """
    chemical_name = chemical_name.lower()
    try:
        compounds = pcp.get_compounds(chemical_name, 'name')
        if compounds:
            compound = compounds[0]
            standardized_name = compound.iupac_name or compound.synonyms[0] if compound.synonyms else chemical_name
            cid = str(compound.cid)

            # Get synonyms for better PubMed searching
            search_terms = [chemical_name]  # Always include original name

            # Get common names from synonyms (prefer shorter, common names)
            if compound.synonyms:
                # Filter for common names (avoid very long IUPAC names, prefer shorter names)
                # Prioritize names that look like common chemical names (not IUPAC)
                common_names = []
                for s in compound.synonyms[:30]:
                    # Skip very long names, IUPAC-style names, and CAS numbers
                    if (len(s) < 80 and
                        not s.startswith('4-[') and
                        not s.startswith('(') and
                        not s.replace('.', '').replace('-', '').isdigit() and  # Not CAS number
                        s not in search_terms):
                        common_names.append(s)
                        if len(common_names) >= 5:
                            break
                search_terms.extend(common_names)

            # Add standardized name if different
            if standardized_name != chemical_name and standardized_name not in search_terms:
                search_terms.append(standardized_name)

            # Use configurable limit
            max_terms = config.search.max_search_terms
            return standardized_name, cid, search_terms[:max_terms]
        return chemical_name, None, [chemical_name]
    except Exception as e:
        error_msg = f"Error standardizing chemical name: {e}"
        print(error_msg)
        if config.debug:
            raise ChemicalStandardizationError(error_msg) from e
        return chemical_name, None, [chemical_name]


def fetch_pubmed_abstracts(search_terms: List[str], max_results: Optional[int] = None) -> Tuple[List[Dict[str, str]], Dict]:
    """
    Step A.2: Fetch abstracts from PubMed using enhanced MeSH-aware search
    Returns: (List of dicts with 'title', 'abstract', 'pmid', 'year', 'authors', 'journal'), search_log dict
    
    Args:
        search_terms: List of chemical names/synonyms to search
        max_results: Maximum number of results to fetch (uses config default if None)
    
    Raises:
        SearchError: If PubMed search fails critically
    """
    if max_results is None:
        max_results = config.search.max_abstracts_initial

    Entrez.email = config.search.entrez_email  # Required by NCBI

    # Use enhanced search with MeSH terms
    try:
        # Get enhanced synonyms
        synonyms = get_chemical_synonyms_enhanced(search_terms[0] if search_terms else "")

        # Use enhanced PubMed search
        search_result = fetch_pubmed_enhanced(search_terms[0] if search_terms else "", max_results=max_results)
        pmids = search_result.get("pmids", [])
        search_log = search_result.get("search_log", {})

        if not pmids:
            # Fallback to original method if enhanced search fails
            print("Enhanced search returned no results, trying fallback...")
            search_names = [name for name in search_terms if len(name) < 80]
            if not search_names:
                search_names = search_terms[:3]

            name_query = " OR ".join([f'"{name}"[Title/Abstract]' for name in search_names[:5]])
            query = f'({name_query}) AND (liver OR hepatotoxicity)'

            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            handle.close()
            pmids = record["IdList"]
            search_log = {"query": query, "method": "fallback"}

        if not pmids:
            return [], search_log

        # Fetch abstracts with enhanced metadata
        handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml")
        records = Entrez.read(handle)
        handle.close()

        abstracts = []
        for record in records["PubmedArticle"]:
            try:
                article = record["MedlineCitation"]["Article"]
                title = article["ArticleTitle"]

                # Extract abstract
                abstract_text = ""
                if "Abstract" in article:
                    abstract_list = article["Abstract"]["AbstractText"]
                    if isinstance(abstract_list, list):
                        abstract_text = " ".join([str(item) for item in abstract_list])
                    else:
                        abstract_text = str(abstract_list)

                pmid = str(record["MedlineCitation"]["PMID"])

                # Extract additional metadata
                year = None
                authors = None
                journal = None

                try:
                    if "PubDate" in article:
                        pub_date = article["PubDate"]
                        if "Year" in pub_date:
                            year = int(pub_date["Year"])
                except:
                    pass

                try:
                    if "AuthorList" in article:
                        author_list = article["AuthorList"]
                        if author_list:
                            authors = ", ".join([f"{a.get('LastName', '')}, {a.get('ForeName', '')}"
                                               for a in author_list[:3]])
                except:
                    pass

                try:
                    if "Journal" in article:
                        journal = article["Journal"].get("Title", "")
                except:
                    pass

                # Only include abstracts with content
                if abstract_text.strip():
                    abstracts.append({
                        "title": title,
                        "abstract": abstract_text,
                        "pmid": pmid,
                        "year": year,
                        "authors": authors,
                        "journal": journal
                    })
            except Exception as e:
                print(f"Error parsing article: {e}")
                continue

        return abstracts, search_log

    except Exception as e:
        error_msg = f"Error fetching PubMed abstracts: {e}"
        print(error_msg)
        if config.debug:
            raise SearchError(error_msg) from e
        return [], {"error": str(e)}


def check_relevance(abstract_text: str, title: str, chemical_name: str, model_name: str = "llama3.1") -> bool:
    """
    Gatekeeper: Check if abstract is relevant to liver toxicity of the chemical
    Returns: True if relevant, False otherwise
    
    Raises:
        LLMError: If LLM call fails (only in debug mode)
    """
    try:
        # Use deterministic temperature (0.0) for relevance checks
        llm = ChatOllama(model=model_name, temperature=config.llm.temperature_relevance)

        SYSTEM_PROMPT_GATEKEEPER = """### TASK
Determine if the following abstract describes **ADVERSE EFFECTS**, **TOXICITY**, or **SAFETY HAZARDS** of the chemical '{chemical_name}' specifically in the **LIVER**.

### CRITERIA
- **YES**: Abstract discusses hepatotoxicity, liver injury, DILI, liver enzyme elevation, steatosis, fibrosis, or mechanisms of liver damage caused by the chemical.
- **NO**: Abstract discusses the chemical TREATING liver cancer (efficacy), metabolism without toxicity, or toxicity in other organs (kidney, heart) but not liver.

### OUTPUT
Answer with a single word: "YES" or "NO".

Title: {title}
Abstract: {abstract_text}"""

        truncate_len = config.search.relevance_check_truncate
        prompt = SYSTEM_PROMPT_GATEKEEPER.format(
            chemical_name=chemical_name,
            title=title,
            abstract_text=abstract_text[:truncate_len]
        )

        response = llm.invoke(prompt)
        answer = response.content.strip().upper()

        # Extract YES/NO from response (handle cases where model adds explanation)
        is_relevant = "YES" in answer and "NO" not in answer[:10]  # Check first 10 chars to avoid false positives
        if not is_relevant:
            is_relevant = answer.startswith("Y") and not answer.startswith("NO")

        print(f"Relevance check for '{title[:50]}...': {answer[:20]} -> {is_relevant}")
        return is_relevant

    except Exception as e:
        error_msg = f"Error checking relevance for abstract '{title[:50]}...': {e}"
        logger.warning(error_msg)
        if config.debug:
            logger.debug(f"Full error details: {error_msg}", exc_info=True)
            raise LLMError(error_msg) from e
        # Default to including if check fails (conservative approach)
        # Log warning but don't fail the entire analysis
        logger.warning(f"Relevance check failed for '{title[:50]}...', including abstract by default (conservative approach)")
        return True


@retry_with_backoff(exceptions=(LLMError, LLMTimeoutError, Exception))
def analyze_abstract_with_llm(abstract_text: str, title: str, model_name: str = "llama3.1",
                              prompt_hash: Optional[str] = None, fulltext: Optional[str] = None,
                              chemical_name: Optional[str] = None, use_rag: bool = True,
                              use_hierarchical: bool = True, search_terms: Optional[List[str]] = None) -> Tuple[Dict, str]:
    """
    Step B: Analyze abstract against 12 KC definitions using LLM with enhanced features
    Returns: (Dict with KC analysis results including causal links, prompt_hash)
    
    Args:
        abstract_text: Abstract text to analyze
        title: Paper title
        model_name: Model to use
        prompt_hash: Optional prompt hash for provenance
        fulltext: Optional full-text for hierarchical processing
        chemical_name: Optional chemical name for RAG
        use_rag: Whether to use RAG for context
        use_hierarchical: Whether to use hierarchical processing
    
    Raises:
        LLMError: If LLM processing fails after retries
        LLMParseError: If response parsing fails
    """
    # --- Phase 1 RL: Try DSPy optimized classifier first ---
    if _dspy_classifier is not None and chemical_name:
        try:
            dspy_kcs = predict_with_optimized(_dspy_classifier, abstract_text, chemical_name)
            if dspy_kcs and len(dspy_kcs) >= 12:
                print(f"   🤖 DSPy optimized classifier used for '{title[:50]}'")
                result_dict = {f"kc{i}_status": dspy_kcs.get(f"KC{i}", "NOT_MENTIONED") for i in range(1, 13)}
                result_dict.update({"reasoning": "DSPy optimized classifier", "causal_links": [], "evidence_quotes": {}, "dose_response": []})
                prompt_hash_val = prompt_hash or "dspy_optimized"
                return result_dict, prompt_hash_val
        except Exception as e:
            logger.warning(f"DSPy classifier failed, falling back to standard pipeline: {e}")
    # --------------------------------------------------------

    try:
        llm = ChatOllama(
            model=model_name,
            temperature=config.llm.temperature,
        )

        # Build the prompt with KC definitions
        kc_definitions_text = "\n".join([f"{kc}: {definition}" for kc, definition in KC_DEFINITIONS.items()])

        parser = PydanticOutputParser(pydantic_object=KCAnalysis)
        format_instructions = parser.get_format_instructions()

        # CRITICAL FIX: The prompt templates use f-strings which insert format_instructions directly
        # When f-strings process {format_instructions}, they insert the value as-is
        # But LangChain's ChatPromptTemplate will then interpret JSON schema braces like {"properties"}
        # as template variables. We need to escape AFTER the f-string processing.
        # So we'll format the prompt first, then escape the format_instructions in the final string
        format_instructions_escaped = format_instructions  # Will escape after f-string processing

        # Get RAG context if enabled
        rag_context = None
        if use_rag and chemical_name:
            try:
                rag_system = get_rag_system()
                rag_context = rag_system.build_rag_context(abstract_text, chemical_name)
            except Exception as e:
                print(f"Warning: RAG context generation failed: {e}")

        # Use enhanced prompts with better synonym recognition (if enabled)
        if config.analysis.enable_enhanced_prompts:
            prompt_mode = getattr(config.analysis, 'prompt_mode', 'enhanced')

            # For well-known chemicals like Acetaminophen, use chemical-specific prompts
            # Check both the chemical_name and search_terms to catch acetaminophen even if standardized name is IUPAC
            chemical_lower = (chemical_name or "").lower()
            search_terms_lower = [s.lower() for s in (search_terms or [])]
            acetaminophen_names = ["acetaminophen", "paracetamol", "apap", "tylenol", "n-acetyl-p-aminophenol"]
            is_acetaminophen = (chemical_lower in acetaminophen_names or
                               any(term in acetaminophen_names for term in search_terms_lower) or
                               any(apap_name in term for apap_name in acetaminophen_names for term in search_terms_lower))

            if is_acetaminophen:
                logger.debug(f"Acetaminophen detected: chemical_name='{chemical_name}', prompt_mode='{prompt_mode}'")
                if prompt_mode == "liberal":
                    # Use liberal mode for Acetaminophen if still missing mechanisms
                    base_prompt = get_liberal_prompt(kc_definitions_text, format_instructions_escaped, chemical_name)
                    # Add Acetaminophen context
                    acetaminophen_context = "\n\n### ACETAMINOPHEN CONTEXT: Known mechanisms include KC1 (NAPQI), KC2 (necrosis), KC5 (glutathione depletion), KC7 (mitochondrial dysfunction), KC8 (JNK signaling), KC12 (steatosis)."
                    base_prompt = base_prompt.replace(format_instructions_escaped, acetaminophen_context + "\n\n" + format_instructions_escaped)
                else:
                    base_prompt = get_acetaminophen_specific_prompt(kc_definitions_text, format_instructions_escaped, chemical_name)
            else:
                logger.debug(f"Prompt selection: chemical='{chemical_name}', mode='{prompt_mode}'")
                if prompt_mode == "liberal":
                    # Use liberal prompt for other chemicals
                    base_prompt = get_liberal_prompt(kc_definitions_text, format_instructions_escaped, chemical_name)
                else:
                    # Use enhanced prompt with synonym recognition
                    base_prompt = get_enhanced_prompt_with_synonyms(kc_definitions_text, format_instructions_escaped, chemical_name)
        else:
            # Use standard variable complexity prompts
            base_prompt = get_prompt_for_abstract(
                abstract_text, fulltext, kc_definitions_text, format_instructions_escaped, rag_context, chemical_name
            )

        # Enhance with causal reasoning
        base_prompt_enhanced = enhance_causal_reasoning_prompt(base_prompt)

        # CRITICAL FIX: The prompt templates use f-strings, so format_instructions is already inserted
        # Now we need to escape the JSON schema braces in format_instructions so LangChain
        # doesn't interpret them as template variables
        # Find where format_instructions appears in the prompt and escape its braces
        # We'll replace {"properties"} with {{"properties"}}, etc.
        # But we need to be careful - the format_instructions might appear multiple times

        # Escape format_instructions in the final prompt string
        # Replace all occurrences of JSON schema patterns that LangChain would interpret as variables
        import re
        # Pattern to match JSON schema braces like {"properties"}, {"$defs"}, {"foo"}
        # But only if they're part of the format_instructions (not other parts of the prompt)
        # Since format_instructions contains these patterns, we'll escape them globally in the prompt
        # where they appear as part of JSON schema examples

        # More targeted: escape braces that appear in JSON schema context
        # Look for patterns like: {"properties": or {"$defs": or schema {"properties"
        SYSTEM_PROMPT_ANALYST = base_prompt_enhanced

        # CRITICAL FIX: The prompt templates use f-strings which insert format_instructions directly
        # After f-string processing, format_instructions contains JSON schema like {"properties"}
        # LangChain's ChatPromptTemplate will interpret these as template variables
        # Solution: Escape ALL braces in the final prompt, then unescape only the LangChain variables we need

        # Check if there are placeholders that need formatting (some prompts may still have them)
        if "{kc_definitions}" in SYSTEM_PROMPT_ANALYST or "{format_instructions}" in SYSTEM_PROMPT_ANALYST:
            SYSTEM_PROMPT_ANALYST = SYSTEM_PROMPT_ANALYST.format(
                kc_definitions=kc_definitions_text,
                format_instructions=format_instructions
            )

        # Now escape ALL braces to prevent LangChain from interpreting JSON schema as variables
        # Then unescape only the LangChain template variables we need: {title} and {abstract}
        SYSTEM_PROMPT_ANALYST = SYSTEM_PROMPT_ANALYST.replace("{", "{{").replace("}", "}}")
        # Unescape LangChain template variables
        SYSTEM_PROMPT_ANALYST = SYSTEM_PROMPT_ANALYST.replace("{{title}}", "{title}")
        SYSTEM_PROMPT_ANALYST = SYSTEM_PROMPT_ANALYST.replace("{{abstract}}", "{abstract}")

        # Use hierarchical processing if enabled and fulltext available
        text_to_analyze = abstract_text
        if use_hierarchical and fulltext:
            try:
                text_to_analyze, _ = prioritize_text_for_analysis(abstract_text, fulltext)
            except Exception as e:
                print(f"Warning: Hierarchical processing failed: {e}")

        # Enhanced system prompt with evidence quote extraction and few-shot examples
        # (Keeping old prompt as fallback, but using new variable prompt system)
        SYSTEM_PROMPT_ANALYST_FALLBACK = """### ROLE
You are an Expert Toxicologist and Systematic Reviewer. Your task is to extract structured mechanistic data from scientific abstracts regarding chemical hepatotoxicity.

### KEY CHARACTERISTICS (KCs) DEFINITIONS
{kc_definitions}

### INSTRUCTIONS
Analyze the provided abstract text step-by-step using this reasoning process:

**For EACH KC, follow this chain:**
1. **Scan**: Identify all mentions related to this KC mechanism in the text
2. **Evaluate**: Determine if the text explicitly states the chemical causes this effect
3. **Quote**: Extract the exact sentence(s) that support your conclusion
4. **Link**: If another KC is mentioned as causing this one, note the causal relationship
5. **Decide**: Assign status: SUPPORTED, REFUTED, or NOT_MENTIONED

**Detailed Requirements:**

1. **Assess KC Status**: For EACH of the 12 KCs, determine its status based strictly on the text:
   - "SUPPORTED": The text explicitly states the chemical causes/induces this effect. Provide exact quotes in evidence_quotes.
   - "REFUTED": The text explicitly states the chemical DOES NOT cause this effect (e.g., "no evidence of fibrosis was found").
   - "NOT_MENTIONED": The text does not discuss this mechanism.

2. **Extract Evidence Quotes**: For each SUPPORTED KC, provide 1-2 exact sentence quotes from the text that support this conclusion.
   - Store quotes in evidence_quotes dict: {{"KC1": ["quote1", "quote2"], "KC5": ["quote3"]}}
   - Quotes should be verbatim from the abstract.

3. **Extract Causal Links**: Identify mechanistic pathways where one KC triggers another.
   - Format: Source KC -> Target KC.
   - CRITICAL: Only extract links EXPLICITLY stated (e.g., "Metabolism (KC1) led to Oxidative Stress (KC5)").
   - Do not infer links that are not written in the text.
   - Include exact quotes supporting each causal link.
   - Assess strength: STRONG (directly stated), MODERATE (implied but clear), WEAK (tenuous connection).

4. **Extract Dose-Response Data**: Identify and extract any mentions of dose, concentration, or exposure levels related to observed effects.
   - Examples: "at a dose of 50 mg/kg", "concentrations of 10-100 μM", "following exposure to 25 ppm".
   - Store these as a list of strings in the `dose_response` field.

5. **Reasoning**: Provide a concise biological explanation for your decisions, showing your reasoning chain for at least 3 KCs.

### FEW-SHOT EXAMPLES

**EXAMPLE 1: KC1 (Reactive/Bioactivation) - SUPPORTED**
Abstract: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine that depletes glutathione and causes liver injury."
Analysis:
- KC1_status: SUPPORTED
- Evidence Quote: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"
- Reasoning: Explicitly states bioactivation to reactive metabolite (NAPQI)

**EXAMPLE 2: KC5 (Oxidative Stress) - SUPPORTED with Causal Link**
Abstract: "Metabolism of the compound led to glutathione depletion, resulting in increased ROS levels and oxidative stress in hepatocytes."
Analysis:
- KC5_status: SUPPORTED
- Evidence Quote: "increased ROS levels and oxidative stress in hepatocytes"
- Causal Link: KC1 -> KC5 (Metabolism -> Oxidative Stress), strength: STRONG
- Reasoning: Clear causal pathway from bioactivation (KC1) to oxidative stress (KC5)

**EXAMPLE 3: KC11 (Liver Fibrosis) - REFUTED**
Abstract: "Histological examination revealed hepatocellular necrosis but no evidence of fibrosis was observed after 28 days of treatment."
Analysis:
- KC11_status: REFUTED
- Evidence Quote: "no evidence of fibrosis was observed"
- Reasoning: Explicitly states absence of fibrosis

**EXAMPLE 4: Multiple KCs with Causal Chain**
Abstract: "The chemical undergoes bioactivation via CYP450, generating reactive metabolites that deplete glutathione. This leads to mitochondrial dysfunction and ultimately triggers apoptosis in liver cells."
Analysis:
- KC1_status: SUPPORTED (bioactivation)
- KC7_status: SUPPORTED (mitochondrial dysfunction)
- KC2_status: SUPPORTED (apoptosis/cell death)
- Causal Links: KC1 -> KC7 (bioactivation -> mitochondrial dysfunction), KC7 -> KC2 (mitochondrial dysfunction -> apoptosis)
- Reasoning: Clear mechanistic cascade from bioactivation through mitochondrial effects to cell death

### JSON OUTPUT REQUIREMENTS
You must return a valid JSON object. Do not include markdown formatting (```json).
- Keys for KCs: "kc1_status", "kc2_status"... values must be "SUPPORTED", "REFUTED", or "NOT_MENTIONED".
- Key for Evidence Quotes: "evidence_quotes" as a dict: {{"KC1": ["quote1"], "KC5": ["quote2", "quote3"]}}
- Key for Causal Links: "causal_links" as a list of objects: {{"source": "KC1", "target": "KC5", "evidence": "quote...", "strength": "STRONG"}}.
- Key for Dose-Response: "dose_response" as a list of strings: ["50 mg/kg", "10-100 μM"].
- Key for Reasoning: "reasoning".

{format_instructions}"""

        # SYSTEM_PROMPT_ANALYST already has format_instructions_escaped embedded (with {{ and }})
        # and kc_definitions formatted, so we can use it directly in ChatPromptTemplate
        # The only remaining variables are {title} and {abstract} which we'll pass when invoking

        prompt_template_with_format = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_ANALYST),
            ("human", """Chemical being analyzed: {chemical_name_input}\n\nTitle: {title}\n\nAbstract: {abstract}\n\nAnalyze this abstract against the 12 Key Characteristics for **{chemical_name_input}** only. Return ONLY the raw JSON."""),
        ])

        # Hash prompt for provenance
        full_prompt_text = SYSTEM_PROMPT_ANALYST
        current_prompt_hash = prompt_hash or hash_prompt(full_prompt_text)

        # Archive prompt for reproducibility
        try:
            from reproducibility import archive_prompt, save_prompt_archive
            prompt_archive = archive_prompt(
                prompt_text=full_prompt_text,
                prompt_type="kc_analysis",
                prompt_name=f"{chemical_name or 'unknown'}_{model_name}",
                metadata={
                    "chemical_name": chemical_name,
                    "model_name": model_name,
                    "temperature": config.llm.temperature,
                    "prompt_mode": getattr(config.analysis, 'prompt_mode', 'enhanced'),
                    "use_rag": use_rag,
                    "use_hierarchical": use_hierarchical
                }
            )
            save_prompt_archive(prompt_archive, archive_dir="prompt_archives")
        except Exception as e:
            # Don't fail if archiving fails
            if config.debug:
                print(f"Warning: Prompt archiving failed: {e}")

        chain = prompt_template_with_format | llm

        # First get raw response for debugging
        raw_response = chain.invoke({
            "title": title,
            "abstract": text_to_analyze,
            "chemical_name_input": chemical_name or "the chemical under study"
        })

        response_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
        logger.debug(f"LLM Response preview: {response_text[:300]}")

        # Detect model refusals before attempting to parse
        REFUSAL_PATTERNS = [
            "i can't help",
            "i cannot help",
            "i can't provide",
            "i cannot provide",
            "i'm not able to",
            "i am not able to",
            "i don't have information",
            "i cannot assist",
            "i can't assist",
        ]
        response_lower = response_text.strip().lower()
        if any(response_lower.startswith(p) or (len(response_text) < 200 and p in response_lower)
               for p in REFUSAL_PATTERNS):
            raise LLMError(
                f"Model refused to analyze abstract ('{response_text[:100]}'). "
                "Retrying — model may need clearer instructions."
            )

        # Clean response: Remove markdown code blocks if present
        # Remove markdown code fences
        cleaned_text = re.sub(r'```json\s*', '', response_text)
        cleaned_text = re.sub(r'```\s*', '', cleaned_text)
        cleaned_text = cleaned_text.strip()

        # Try parsing with Pydantic
        result = None
        json_data = None
        try:
            result = parser.parse(cleaned_text)
        except Exception as parse_error:
            print(f"Pydantic parsing failed: {parse_error}")
            print(f"Cleaned response preview: {cleaned_text[:500]}...")

            # Fallback: Try to extract JSON from response
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                try:
                    json_str = json_match.group()
                    json_data = json.loads(json_str)
                    print(f"Successfully extracted JSON with {len(json_data)} keys")

                    # Validate that we got KC analysis, not paper metadata
                    # Validate that we got KC analysis, not paper metadata
                    # Check if it looks like paper metadata (Title, Authors, Journal, etc.)
                    metadata_keys = {"Title", "Authors", "Journal", "Year", "Volume", "Issue", "Page", "Abstract", "Affiliations", "Corresponding Author", "Publication Year", "CorrespondingAuthor"}
                    kc_status_keys = [f"kc{i}_status" for i in range(1, 13)]
                    has_kc_fields = any(key in json_data for key in kc_status_keys)
                    has_metadata_fields = bool(metadata_keys.intersection(set(json_data.keys())))

                    if has_metadata_fields and not has_kc_fields:
                        print(f"   ⚠️  Warning: LLM returned paper metadata instead of KC analysis. Detected keys: {list(metadata_keys.intersection(set(json_data.keys())))}")
                        print("   💡 This indicates the model misunderstood the task. The response should contain kc1_status, kc2_status, etc., not paper metadata.")
                        # This is definitely wrong format - raise error to trigger retry
                        raise ValueError("LLM returned paper metadata format instead of KC analysis format. Expected kc1_status, kc2_status, etc., but got paper metadata fields.")
                    elif has_metadata_fields and has_kc_fields:
                        # Has both - remove metadata fields and keep only KC analysis fields
                        print("   ⚠️  Warning: LLM returned both paper metadata and KC analysis. Removing metadata fields...")
                        for key in list(json_data.keys()):
                            if key in metadata_keys:
                                del json_data[key]
                        print(f"   ✓ Cleaned JSON - removed {len(metadata_keys.intersection(set(json_data.keys())))} metadata fields")

                    # Fix causal_links format BEFORE trying to create KCAnalysis
                    # Normalize KC names to uppercase (KC1, KC2, etc.)
                    def normalize_kc_name(kc_str: str) -> str:
                        """Normalize KC name to uppercase format (KC1, KC2, etc.)"""
                        if not kc_str:
                            return ""
                        kc_str = str(kc_str).strip().upper()
                        # If it's just a number, add "KC" prefix
                        if kc_str.isdigit():
                            return f"KC{kc_str}"
                        # If it starts with "KC" (case-insensitive), ensure uppercase
                        if kc_str.startswith("KC"):
                            return kc_str
                        # If it starts with just "K" and a number, fix it
                        if kc_str.startswith("K") and len(kc_str) > 1 and kc_str[1:].isdigit():
                            return f"KC{kc_str[1:]}"
                        return kc_str

                    if "causal_links" in json_data and isinstance(json_data["causal_links"], list):
                        fixed_causal_links = []
                        for link in json_data["causal_links"]:
                            if isinstance(link, dict):
                                # Check if it's in the wrong format (cause/effect instead of source/target)
                                if "cause" in link or "effect" in link:
                                    # Transform cause/effect to source/target and normalize
                                    source = normalize_kc_name(link.get("cause", link.get("source", "")))
                                    target = normalize_kc_name(link.get("effect", link.get("target", "")))
                                    # Only include if both are valid KC names
                                    if source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                                        fixed_link = {
                                            "source": source,
                                            "target": target,
                                            "evidence": link.get("evidence", source + " -> " + target),
                                            "strength": link.get("strength", "MODERATE")
                                        }
                                        fixed_causal_links.append(fixed_link)
                                elif "source" in link and "target" in link:
                                    # Already in correct format, normalize KC names
                                    source = normalize_kc_name(link.get("source", ""))
                                    target = normalize_kc_name(link.get("target", ""))
                                    # Only include if both are valid KC names
                                    if source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                                        fixed_link = {
                                            "source": source,
                                            "target": target,
                                            "evidence": link.get("evidence", source + " -> " + target),
                                            "strength": link.get("strength", "MODERATE")
                                        }
                                        fixed_causal_links.append(fixed_link)
                                else:
                                    # Invalid format, skip
                                    continue
                        json_data["causal_links"] = fixed_causal_links
                        if len(fixed_causal_links) > 0:
                            print(f"   🔧 Fixed {len(fixed_causal_links)} causal links format")

                    # Fix reasoning field - handle list, dict, or string formats
                    if "reasoning" in json_data:
                        reasoning_val = json_data["reasoning"]
                        if isinstance(reasoning_val, list):
                            # Check if it's a list of dicts (e.g., [{"KC": "...", "Evidence": "..."}])
                            if len(reasoning_val) > 0 and isinstance(reasoning_val[0], dict):
                                # Convert list of dicts to formatted string
                                reasoning_lines = []
                                for item in reasoning_val:
                                    if isinstance(item, dict):
                                        # Format: "KC: Evidence"
                                        kc = item.get("KC", item.get("kc", item.get("key", "")))
                                        evidence = item.get("Evidence", item.get("evidence", item.get("text", "")))
                                        if kc and evidence:
                                            reasoning_lines.append(f"{kc}: {evidence}")
                                        elif evidence:
                                            reasoning_lines.append(evidence)
                                        else:
                                            reasoning_lines.append(str(item))
                                    else:
                                        reasoning_lines.append(str(item))
                                json_data["reasoning"] = "\n".join(reasoning_lines)
                                print(f"   🔧 Fixed reasoning format: converted list of {len(reasoning_val)} dicts to string")
                            else:
                                # Convert list of strings/other to string (join with newlines)
                                json_data["reasoning"] = "\n".join(str(item) for item in reasoning_val)
                                print("   🔧 Fixed reasoning format: converted list to string")
                        elif isinstance(reasoning_val, dict):
                            # Handle dict format (e.g., {"text": ["line1", "line2"]})
                            if 'text' in reasoning_val and isinstance(reasoning_val['text'], list):
                                json_data["reasoning"] = "\n".join(str(item) for item in reasoning_val['text'])
                                print("   🔧 Fixed reasoning format: extracted text from dict")
                            else:
                                # Convert dict to JSON string
                                import json as json_module
                                json_data["reasoning"] = json_module.dumps(reasoning_val)
                                print("   🔧 Fixed reasoning format: converted dict to JSON string")
                        elif not isinstance(reasoning_val, str):
                            # Convert any other type to string
                            json_data["reasoning"] = str(reasoning_val)
                            print("   🔧 Fixed reasoning format: converted to string")
                    else:
                        json_data["reasoning"] = "No reasoning provided (extracted from JSON fallback)"
                        print("   ⚠️  Warning: 'reasoning' field missing in LLM response, using default")

                    # Ensure causal_links and evidence_quotes exist
                    if "causal_links" not in json_data:
                        json_data["causal_links"] = []
                    if "evidence_quotes" not in json_data:
                        json_data["evidence_quotes"] = {}
                    if "dose_response" not in json_data:
                        json_data["dose_response"] = []

                    # Reject responses with NO KC keys — wrong format entirely
                    # (e.g. LLM returned chemical facts, paper metadata, or study summary)
                    kc_status_keys_present = [f"kc{i}_status" for i in range(1, 13) if f"kc{i}_status" in json_data]
                    if not kc_status_keys_present:
                        raise ValueError(
                            f"LLM returned JSON with no KC status fields (got keys: {list(json_data.keys())[:8]}). "
                            "Model ignored the output format. Retrying."
                        )

                    # Fill in any missing KC statuses as NOT_MENTIONED
                    for i in range(1, 13):
                        kc_key = f"kc{i}_status"
                        if kc_key not in json_data:
                            json_data[kc_key] = "NOT_MENTIONED"

                    # Fix causal_links format if needed (handle cause/effect vs source/target)
                    # Note: This is a duplicate section - normalization already done above, but ensure consistency
                    if "causal_links" in json_data and isinstance(json_data["causal_links"], list):
                        # Use the normalize_kc_name function defined above
                        fixed_causal_links = []
                        for link in json_data["causal_links"]:
                            if isinstance(link, dict):
                                # Check if it's in the wrong format (cause/effect instead of source/target)
                                if "cause" in link or "effect" in link:
                                    # Transform cause/effect to source/target and normalize
                                    source = normalize_kc_name(link.get("cause", link.get("source", "")))
                                    target = normalize_kc_name(link.get("effect", link.get("target", "")))
                                    # Only include if both are valid KC names
                                    if source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                                        fixed_link = {
                                            "source": source,
                                            "target": target,
                                            "evidence": link.get("evidence", source + " -> " + target),
                                            "strength": link.get("strength", "MODERATE")
                                        }
                                        fixed_causal_links.append(fixed_link)
                                elif "source" in link and "target" in link:
                                    # Already in correct format, normalize KC names
                                    source = normalize_kc_name(link.get("source", ""))
                                    target = normalize_kc_name(link.get("target", ""))
                                    # Only include if both are valid KC names
                                    if source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                                        fixed_link = {
                                            "source": source,
                                            "target": target,
                                            "evidence": link.get("evidence", source + " -> " + target),
                                            "strength": link.get("strength", "MODERATE")
                                        }
                                        fixed_causal_links.append(fixed_link)
                                else:
                                    # Invalid format, skip
                                    continue
                        json_data["causal_links"] = fixed_causal_links
                        if len(fixed_causal_links) > 0:
                            print(f"   🔧 Fixed {len(fixed_causal_links)} causal links format (cause/effect -> source/target)")

                    # Manually construct result from JSON
                    try:
                        result = KCAnalysis(**json_data)
                    except Exception as pydantic_error:
                        # Last resort: Create a minimal valid KCAnalysis with extracted KC statuses
                        print(f"   ⚠️  Warning: Could not create full KCAnalysis object: {pydantic_error}")
                        print("   💡 Attempting to preserve extracted KC statuses...")

                        # Extract KC statuses that were successfully parsed
                        extracted_statuses = {}
                        for i in range(1, 13):
                            kc_key = f"kc{i}_status"
                            if kc_key in json_data:
                                extracted_statuses[kc_key] = json_data[kc_key]

                        # Use fixed causal_links if available (already fixed above)
                        causal_links_fixed = json_data.get("causal_links", [])
                        # Convert to CausalLink objects if needed
                        try:
                            causal_links_objects = []
                            for link in causal_links_fixed:
                                if isinstance(link, dict):
                                    # Ensure we have the correct format
                                    source = link.get("source", link.get("cause", ""))
                                    target = link.get("target", link.get("effect", ""))
                                    evidence = link.get("evidence", source + " -> " + target)
                                    strength = link.get("strength", "MODERATE")

                                    if source and target:  # Only add if both are present
                                        causal_links_objects.append(CausalLink(
                                            source=source,
                                            target=target,
                                            evidence=evidence,
                                            strength=strength
                                        ))
                            causal_links_fixed = causal_links_objects
                        except Exception as e:
                            # If conversion fails, use empty list
                            print(f"   ⚠️  Warning: Could not convert causal_links: {e}")
                            import traceback
                            traceback.print_exc()
                            causal_links_fixed = []

                        # Fix reasoning format for minimal data
                        reasoning_val = json_data.get("reasoning", "Partial extraction: Some fields failed validation")
                        if isinstance(reasoning_val, list):
                            # Check if it's a list of dicts (e.g., [{"KC": "...", "Evidence": "..."}])
                            if len(reasoning_val) > 0 and isinstance(reasoning_val[0], dict):
                                # Convert list of dicts to formatted string
                                reasoning_lines = []
                                for item in reasoning_val:
                                    if isinstance(item, dict):
                                        # Format: "KC: Evidence"
                                        kc = item.get("KC", item.get("kc", item.get("key", "")))
                                        evidence = item.get("Evidence", item.get("evidence", item.get("text", "")))
                                        if kc and evidence:
                                            reasoning_lines.append(f"{kc}: {evidence}")
                                        elif evidence:
                                            reasoning_lines.append(evidence)
                                        else:
                                            reasoning_lines.append(str(item))
                                    else:
                                        reasoning_lines.append(str(item))
                                reasoning_val = "\n".join(reasoning_lines)
                            else:
                                # Convert list of strings/other to string (join with newlines)
                                reasoning_val = "\n".join(str(item) for item in reasoning_val)
                        elif isinstance(reasoning_val, dict):
                            if 'text' in reasoning_val and isinstance(reasoning_val['text'], list):
                                reasoning_val = "\n".join(str(item) for item in reasoning_val['text'])
                            else:
                                import json as json_module
                                reasoning_val = json_module.dumps(reasoning_val)
                        elif not isinstance(reasoning_val, str):
                            reasoning_val = str(reasoning_val)

                        # Create minimal valid result with extracted statuses
                        minimal_data = {
                            "reasoning": reasoning_val,
                            "causal_links": causal_links_fixed,
                            "evidence_quotes": json_data.get("evidence_quotes", {}),
                            "dose_response": json_data.get("dose_response", [])
                        }
                        # Add all KC statuses (use extracted if available, otherwise NOT_MENTIONED)
                        for i in range(1, 13):
                            kc_key = f"kc{i}_status"
                            minimal_data[kc_key] = extracted_statuses.get(kc_key, "NOT_MENTIONED")

                        result = KCAnalysis(**minimal_data)
                        print(f"   ✓ Successfully preserved {len([k for k, v in extracted_statuses.items() if v != 'NOT_MENTIONED'])} KC statuses")

                except (ValueError, json.JSONDecodeError) as json_error:
                    # Check if it's a format issue (wrong structure) vs parsing issue
                    error_msg = str(json_error)
                    if "paper metadata" in error_msg.lower() or "kc analysis" in error_msg.lower():
                        # Wrong format - retry with more explicit prompt
                        print("   🔄 Retrying with more explicit prompt...")
                        try:
                            # Create a more explicit prompt emphasizing the required format
                            # Escape the prompt for LangChain template
                            explicit_prompt_text = f"""{base_prompt_enhanced}

### CRITICAL REMINDER: YOU MUST RETURN KC ANALYSIS, NOT PAPER METADATA

DO NOT return paper metadata fields like:
- Title, Authors, Journal, Year, Volume, Issue, Page
- Abstract, Affiliations, Corresponding Author, Publication Year

YOU MUST return ONLY KC analysis fields:
- kc1_status, kc2_status, kc3_status, ... kc12_status (each with value: SUPPORTED, ASSOCIATED, CAUSALLY_LINKED, REFUTED, or NOT_MENTIONED)
- reasoning (as a STRING, not a list or dict)
- causal_links (list of objects with source, target, evidence, strength)
- evidence_quotes (dict with KC keys and quote lists)
- dose_response (list of strings)

The JSON must start with kc1_status, kc2_status, etc. NOT with Title, Authors, or any paper metadata fields.

Example correct format:
{{
  "kc1_status": "SUPPORTED",
  "kc2_status": "NOT_MENTIONED",
  ...
  "reasoning": "KC1 is supported because...",
  "evidence_quotes": {{"KC1": ["quote1"]}},
  "causal_links": [],
  "dose_response": []
}}"""

                            # Escape braces for LangChain template
                            explicit_prompt_escaped = explicit_prompt_text.replace("{", "{{").replace("}", "}}")
                            explicit_prompt_escaped = explicit_prompt_escaped.replace("{{title}}", "{title}")
                            explicit_prompt_escaped = explicit_prompt_escaped.replace("{{abstract}}", "{abstract}")

                            # Create new chain with explicit prompt
                            retry_prompt_template = ChatPromptTemplate.from_messages([
                                ("system", explicit_prompt_escaped),
                                ("human", "Title: {title}\n\nAbstract: {abstract}")
                            ])
                            retry_chain = retry_prompt_template | llm

                            retry_response = retry_chain.invoke({
                                "title": title,
                                "abstract": text_to_analyze[:2000]  # Limit for retry
                            })
                            retry_text = retry_response.content if hasattr(retry_response, 'content') else str(retry_response)
                            retry_cleaned = re.sub(r'```json\s*', '', retry_text)
                            retry_cleaned = re.sub(r'```\s*', '', retry_cleaned)
                            retry_cleaned = retry_cleaned.strip()

                            # Try parsing retry response
                            try:
                                result = parser.parse(retry_cleaned)
                                print("   ✓ Retry successful - got valid KC analysis")
                                # Success - result is set, will be used below
                            except Exception as retry_parse_error:
                                # Try JSON extraction on retry
                                retry_json_match = re.search(r'\{.*\}', retry_cleaned, re.DOTALL)
                                if retry_json_match:
                                    try:
                                        retry_json_data = json.loads(retry_json_match.group())
                                        # Check again for metadata
                                        retry_has_kc = any(key in retry_json_data for key in kc_status_keys)
                                        retry_has_metadata = bool(metadata_keys.intersection(set(retry_json_data.keys())))

                                        if retry_has_metadata and not retry_has_kc:
                                            print("   ⚠️  Retry also returned wrong format. Will use fallback.")
                                            json_data = retry_json_data  # Will be handled by fallback logic
                                        elif retry_has_kc:
                                            # Has KC fields - use it
                                            json_data = retry_json_data
                                            retry_success = True
                                        else:
                                            json_data = retry_json_data
                                            retry_success = True
                                    except json.JSONDecodeError:
                                        print(f"   ⚠️  Retry JSON parsing failed: {retry_parse_error}")
                                        pass

                        except Exception as retry_error:
                            print(f"   ⚠️  Retry failed: {retry_error}")
                            # Continue to fallback extraction below

                    # Check if we have a result from retry - if so, skip fallback processing
                    if result is not None:
                        # Retry succeeded with Pydantic parsing, continue to use result
                        pass
                    elif json_data is not None:
                        # We have json_data to process (either from original extraction or retry)
                        # Continue with fallback processing below
                        pass
                    else:
                        # No valid data from retry or original extraction
                        print(f"JSON fallback also failed: {json_error}")
                        if 'json_str' in locals():
                            print(f"JSON string attempted: {json_str[:200]}...")
                        if config.debug:
                            raise LLMParseError(f"Failed to parse LLM response: {json_error}") from parse_error
                        raise parse_error

            # If no JSON was found at all, raise error
            if json_match is None and result is None:
                print("No JSON object found in response")
                if config.debug:
                    raise LLMParseError("No JSON object found in LLM response") from parse_error
                raise parse_error

        # Convert to dict with backward compatibility
        kc_dict = {}
        for i in range(1, 13):
            kc_key = f"KC{i}"
            status_key = f"kc{i}_status"  # Pydantic model uses lowercase
            status = getattr(result, status_key, "NOT_MENTIONED")
            # Convert status to boolean for backward compatibility, but keep status
            # IMPROVEMENT #2: Include all positive evidence types
            kc_dict[kc_key] = status in ["SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"]
            kc_dict[status_key] = status  # Use lowercase status_key, not uppercase kc_key

        reasoning_val = getattr(result, "reasoning", "No reasoning provided")
        # Handle different reasoning formats: list, dict, or string
        if isinstance(reasoning_val, list):
            # Convert list to string (join with newlines)
            kc_dict["reasoning"] = "\n".join(str(item) for item in reasoning_val)
        elif isinstance(reasoning_val, dict):
            # Handle dict format (e.g., {"text": ["line1", "line2"]})
            if 'text' in reasoning_val and isinstance(reasoning_val['text'], list):
                kc_dict["reasoning"] = "\n".join(str(item) for item in reasoning_val['text'])
            else:
                # If it's a dict but not in the expected format, convert to JSON string
                kc_dict["reasoning"] = json.dumps(reasoning_val)
        else:
            kc_dict["reasoning"] = str(reasoning_val)

        causal_links = getattr(result, "causal_links", [])

        # Normalize KC names in causal links to uppercase (KC1, KC2, etc.)
        def normalize_kc_name(kc_str: str) -> str:
            """Normalize KC name to uppercase format (KC1, KC2, etc.)"""
            if not kc_str:
                return ""
            kc_str = str(kc_str).strip().upper()
            # If it's just a number, add "KC" prefix
            if kc_str.isdigit():
                return f"KC{kc_str}"
            # If it starts with "KC" (case-insensitive), ensure uppercase
            if kc_str.startswith("KC"):
                return kc_str
            # If it starts with just "K" and a number, fix it
            if kc_str.startswith("K") and len(kc_str) > 1 and kc_str[1:].isdigit():
                return f"KC{kc_str[1:]}"
            return kc_str

        normalized_causal_links = []
        for link in causal_links:
            source = normalize_kc_name(getattr(link, "source", ""))
            target = normalize_kc_name(getattr(link, "target", ""))
            # Only include links with valid KC names
            if source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                normalized_causal_links.append({
                    "source": source,
                    "target": target,
                    "evidence": getattr(link, "evidence", ""),
                    "strength": getattr(link, "strength", "MODERATE")
                })

        kc_dict["causal_links"] = normalized_causal_links

        # Extract evidence quotes
        evidence_quotes = getattr(result, "evidence_quotes", {})
        kc_dict["evidence_quotes"] = evidence_quotes

        # Extract dose-response data
        dose_response = getattr(result, "dose_response", [])
        kc_dict["dose_response"] = dose_response

        # Validate causal links
        try:
            kc_dict = validate_all_causal_links(kc_dict, text_to_analyze)
        except Exception as e:
            print(f"Warning: Causal link validation failed: {e}")

        print(f"Extracted {len([k for k, v in kc_dict.items() if k.startswith('KC') and v])} supported KCs and {len(normalized_causal_links)} causal links")

        return kc_dict, current_prompt_hash

    except (LLMError, LLMTimeoutError, LLMParseError) as e:
        error_msg = f"Error analyzing abstract with LLM: {e}"
        print(error_msg)
        if config.debug:
            raise
        # Return empty analysis on error (graceful degradation)
        error_dict = dict.fromkeys(KC_DEFINITIONS.keys(), False) | {f"{kc.lower()}_status": "NOT_MENTIONED" for kc in KC_DEFINITIONS} | {"reasoning": f"Error: {str(e)}", "causal_links": [], "evidence_quotes": {}, "dose_response": []}
        return error_dict, prompt_hash or "error"
    except Exception as e:
        error_msg = f"Unexpected error analyzing abstract: {e}"
        print(error_msg)
        if config.debug:
            raise AnalysisError(error_msg) from e
        # Return empty analysis on error
        error_dict = dict.fromkeys(KC_DEFINITIONS.keys(), False) | {f"{kc.lower()}_status": "NOT_MENTIONED" for kc in KC_DEFINITIONS} | {"reasoning": f"Error: {str(e)}", "causal_links": [], "evidence_quotes": {}, "dose_response": []}
        return error_dict, prompt_hash or "error"


def create_evidence_matrix(abstracts: List[Dict], kc_analyses: List[Dict]) -> pd.DataFrame:
    """
    Step C.1: Create Evidence Matrix (Papers x KCs) with negative evidence support
    Values: 1 = SUPPORTED, 0.7 = ASSOCIATED, 0.5 = CAUSALLY_LINKED, -1 = REFUTED, 0 = NOT_MENTIONED
    """
    data = []
    for i, (abstract, analysis) in enumerate(zip(abstracts, kc_analyses)):
        row = {
            "Paper": f"Paper {i+1}",
            "PMID": abstract.get("pmid", "N/A"),
            "Title": abstract.get("title", "")[:50] + "..." if len(abstract.get("title", "")) > 50 else abstract.get("title", ""),
            "Dose-Response": "; ".join(analysis.get("dose_response", [])),
        }
        # Add KC columns with status encoding (IMPROVEMENT #2: Multi-level evidence)
        for kc in KC_DEFINITIONS:
            # Status keys are stored as lowercase (kc1_status, kc2_status, etc.)
            status = analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED")
            if status == "SUPPORTED":
                row[kc] = 1
            elif status == "ASSOCIATED":
                row[kc] = 0.7  # IMPROVEMENT #2: Associated evidence
            elif status == "CAUSALLY_LINKED":
                row[kc] = 0.5  # IMPROVEMENT #2: Indirect causation
            elif status == "REFUTED":
                row[kc] = -1
            else:
                row[kc] = 0
        data.append(row)

    df = pd.DataFrame(data)
    return df


def create_network_graph(kc_analyses: List[Dict], rob_assessments: Optional[List] = None) -> plt.Figure:
    """
    Step C.2: Create NetworkX Directed Acyclic Graph (DAG) showing CAUSAL pathways between KCs
    Uses explicit causal links extracted from abstracts, not just co-occurrence
    """
    G = nx.DiGraph()

    # Add nodes for all KCs
    for kc, name in KC_NAMES.items():
        G.add_node(kc, label=f"{kc}\n{name}")

    # IMPROVEMENT #5: Create RoB weight map for down-weighting high RoB studies
    rob_weights = {}
    if rob_assessments:
        for i, rob in enumerate(rob_assessments):
            if i < len(kc_analyses):
                # Map RoB judgment to weight (High RoB = lower weight)
                rob_judgment = rob.overall_judgment if hasattr(rob, 'overall_judgment') else "Some concerns"
                if rob_judgment == "Low":
                    rob_weights[i] = 1.0  # Full weight
                elif rob_judgment == "Some concerns":
                    rob_weights[i] = 0.75  # Slight down-weight
                elif rob_judgment == "High":
                    rob_weights[i] = 0.5  # Significant down-weight (IMPROVEMENT #5)
                elif rob_judgment == "Critical":
                    rob_weights[i] = 0.25  # Heavy down-weight
                else:
                    rob_weights[i] = 0.5  # Default for insufficient info
            else:
                rob_weights[i] = 1.0  # Default if no RoB assessment

    # Aggregate causal links from all analyses
    edge_data = {}  # (source, target) -> {count, evidence_list, strengths, weighted_count}

    for idx, analysis in enumerate(kc_analyses):
        causal_links = analysis.get("causal_links", [])
        # Get RoB weight for this study (IMPROVEMENT #5)
        study_weight = rob_weights.get(idx, 1.0)

        for link in causal_links:
            source_raw = link.get("source", "")
            target_raw = link.get("target", "")
            evidence = link.get("evidence", "")
            strength = link.get("strength", "MODERATE")

            # Normalize KC names to uppercase (KC1, KC2, etc.) to match KC_DEFINITIONS keys
            # Handle formats like "kc1", "KC1", "1", etc.
            def normalize_kc_name(kc_str: str) -> str:
                """Normalize KC name to uppercase format (KC1, KC2, etc.)"""
                if not kc_str:
                    return ""
                kc_str = str(kc_str).strip().upper()
                # If it's just a number, add "KC" prefix
                if kc_str.isdigit():
                    return f"KC{kc_str}"
                # If it starts with "KC" (case-insensitive), ensure uppercase
                if kc_str.startswith("KC"):
                    return kc_str
                # If it starts with just "K" and a number, fix it
                if kc_str.startswith("K") and len(kc_str) > 1 and kc_str[1:].isdigit():
                    return f"KC{kc_str[1:]}"
                # If it's lowercase "kc" followed by number, convert to uppercase
                if kc_str.startswith("KC"):
                    return kc_str
                return kc_str

            source = normalize_kc_name(source_raw)
            target = normalize_kc_name(target_raw)

            if source and target and source in KC_DEFINITIONS and target in KC_DEFINITIONS:
                edge_key = (source, target)

                if edge_key not in edge_data:
                    edge_data[edge_key] = {
                        "count": 0,
                        "weighted_count": 0.0,  # IMPROVEMENT #5: Weighted count
                        "evidence_list": [],
                        "strengths": []
                    }

                edge_data[edge_key]["count"] += 1
                edge_data[edge_key]["weighted_count"] += study_weight  # IMPROVEMENT #5: Add weighted contribution
                if evidence:
                    edge_data[edge_key]["evidence_list"].append(evidence[:50])  # Truncate long evidence
                edge_data[edge_key]["strengths"].append(strength)

    # Add edges to graph with aggregated data
    for (source, target), data in edge_data.items():
        # IMPROVEMENT #5: Weight based on frequency, strength, AND RoB (weighted_count)
        # Use weighted_count instead of raw count to down-weight high RoB studies
        base_weight = data["weighted_count"]  # IMPROVEMENT #5: Use weighted count
        strength_bonus = {"STRONG": 2, "MODERATE": 1, "WEAK": 0.5}.get(
            max(data["strengths"], key=lambda s: {"STRONG": 2, "MODERATE": 1, "WEAK": 0.5}.get(s, 1)), 1
        )
        weight = base_weight * strength_bonus

        # Store evidence for tooltip (though matplotlib doesn't support tooltips, we can show in labels)
        evidence_summary = "; ".join(data["evidence_list"][:2])  # Show first 2 evidence snippets

        G.add_edge(source, target, weight=weight, count=data["count"],
                  evidence=evidence_summary, strength=max(data["strengths"], key=len))

    # Create visualization
    fig, ax = plt.subplots(figsize=(16, 12))

    # Use hierarchical layout for DAG (better for causal pathways)
    try:
        # Try topological sort layout if graph is acyclic
        if nx.is_directed_acyclic_graph(G):
            pos = nx.nx_agraph.graphviz_layout(G, prog='dot') if hasattr(nx, 'nx_agraph') else \
                  nx.spring_layout(G, k=3, iterations=50, seed=42)
        else:
            pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    except:
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)

    # Color nodes based on their role in the pathway
    # Entry points (no incoming edges) in one color, exit points (no outgoing) in another
    in_degree = dict(G.in_degree())
    out_degree = dict(G.out_degree())

    node_colors = []
    for node in G.nodes():
        if in_degree[node] == 0 and out_degree[node] > 0:
            node_colors.append('#4ECDC4')  # Entry point (upstream) - teal
        elif out_degree[node] == 0 and in_degree[node] > 0:
            node_colors.append('#FF6B6B')  # Exit point (downstream) - red
        elif in_degree[node] > 0 and out_degree[node] > 0:
            node_colors.append('#95E1D3')  # Intermediate - light teal
        else:
            node_colors.append('#CCCCCC')  # Isolated - gray

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2500,
                          alpha=0.9, ax=ax, edgecolors='black', linewidths=2)

    # Draw edges with weights and colors based on strength
    edges = G.edges()
    if edges:
        edge_colors = []
        edge_widths = []
        for u, v in edges:
            edge_data = G[u][v]
            weight = edge_data.get('weight', 1)
            strength = edge_data.get('strength', 'MODERATE')

            edge_widths.append(weight * 1.5)

            # Color by strength
            if strength == 'STRONG':
                edge_colors.append('#2C3E50')  # Dark blue-black
            elif strength == 'MODERATE':
                edge_colors.append('#34495E')  # Medium gray-blue
            else:
                edge_colors.append('#95A5A6')  # Light gray

        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.7,
                              edge_color=edge_colors, arrows=True, arrowsize=25,
                              arrowstyle='->', ax=ax, connectionstyle='arc3,rad=0.1')

    # Draw labels
    labels = {node: G.nodes[node]['label'] for node in G.nodes()}
    nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='bold', ax=ax)

    # Add edge labels for counts (frequency of causal link)
    if edges:
        edge_labels = {}
        for u, v in edges:
            count = G[u][v].get('count', 1)
            edge_labels[(u, v)] = f"×{count}"

        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8,
                                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7), ax=ax)

    ax.set_title("Causal Pathway Network (DAG)\n(Arrows show causal relationships: Source → Target)\n" +
                 "Teal=Upstream, Light Teal=Intermediate, Red=Downstream",
                 fontsize=14, fontweight='bold', pad=20)
    ax.axis('off')

    plt.tight_layout()
    return fig


def create_heatmap(df: pd.DataFrame) -> plt.Figure:
    """
    Create seaborn heatmap of Evidence Matrix
    """
    # Check if dataframe is empty
    if df.empty or len(df) == 0:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No data available for evidence matrix",
                ha='center', va='center', fontsize=14)
        ax.axis('off')
        return fig

    # Extract only KC columns for heatmap
    kc_cols = [kc for kc in KC_DEFINITIONS if kc in df.columns]

    if not kc_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No Key Characteristics columns found",
                ha='center', va='center', fontsize=14)
        ax.axis('off')
        return fig

    heatmap_data = df[kc_cols].copy()  # Make explicit copy to avoid SettingWithCopyWarning

    # Ensure numeric data types
    for col in kc_cols:
        heatmap_data[col] = pd.to_numeric(heatmap_data[col], errors='coerce').fillna(0)

    # Create custom labels for y-axis (Paper number + truncated title)
    y_labels = [f"{row['Paper']}\n{row['Title']}" for _, row in df.iterrows()]

    # Create custom labels for x-axis (KC names)
    x_labels = [KC_NAMES[kc] for kc in kc_cols]

    fig, ax = plt.subplots(figsize=(14, max(8, len(df) * 0.8)))

    # Use diverging colormap: red for negative (REFUTED), white for neutral, green for positive (SUPPORTED)
    # Use '.1f' format to handle float values (0.7, 0.5) properly
    sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                cbar_kws={'label': 'Evidence: 1=SUPPORTED, 0.7=ASSOCIATED, 0.5=CAUSALLY_LINKED, 0=NOT_MENTIONED, -1=REFUTED'},
                xticklabels=x_labels, yticklabels=y_labels,
                linewidths=0.5, linecolor='gray', ax=ax, vmin=-1, vmax=1)

    ax.set_title("Evidence Matrix: Papers vs Key Characteristics\n" +
                 "(Green=Supported, White=Not Mentioned, Red=Refuted)",
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel("Key Characteristics", fontsize=12, fontweight='bold')
    ax.set_ylabel("Papers", fontsize=12, fontweight='bold')

    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()

    return fig


def analyze_chemical(
    chemical_name: str,
    model_names: List[str] = None,  # Changed to support multiple models
    enable_rob: bool = True,
    enable_certainty: bool = True,
    progress: Optional[Progress] = None
) -> Tuple[str, plt.Figure, plt.Figure, Optional[plt.Figure], Optional[plt.Figure], Optional[plt.Figure], Optional[str], Optional[pd.DataFrame], List[Dict], Dict]:
    """
    Main analysis function that orchestrates all steps with PRISMA compliance and provenance tracking
    Returns: (summary_text, heatmap_fig, network_fig, prisma_fig, rob_heatmap_fig, rob_summary_fig, evidence_profiles_text)
    """
    chemical_name = chemical_name.lower()
    start_time = time.time()

    if not chemical_name.strip():
        return "Please enter a chemical name.", None, None, None, None, None, None

    # Normalize model names (fix common typos/old names)
    def normalize_model_name(model_name: str) -> str:
        """Fix common model name typos and old names"""
        model_name = model_name.strip()
        # Fix common typos
        if model_name == "llama3" or model_name == "lamma3" or model_name == "lamma3.2":
            return "llama3.2"
        if model_name == "lamma3.1":
            return "llama3.1"
        # Handle deepseek-r1 variations
        if model_name.startswith("deepseek-r1") or model_name == "deepseek-r1":
            return "deepseek-r1:671b"  # Use specific tag if available
        return model_name

    # Handle model selection (single or multiple)
    if model_names is None or len(model_names) == 0:
        model_names = ["llama3.2"]  # Updated default to llama3.2
    elif isinstance(model_names, str):
        model_names = [model_names]

    # Filter out empty strings and normalize model names
    model_names = [normalize_model_name(m) for m in model_names if m.strip()]
    if not model_names:
        model_names = ["llama3.2"]  # Updated default to llama3.2

    use_multi_reviewer = len(model_names) > 1

    # Initialize PRISMA record
    prisma_record = PRISMARecord(
        chemical_name=chemical_name,
        search_date=datetime.now(),
        databases_searched=["PubMed"]
    )

    try:
        # ============================================================================
        # ANALYSIS START BANNER
        # ============================================================================
        print("\n" + "="*80)
        print("🔬 AI TOXICOLOGIST: HEPATOTOXICITY ASSESSMENT")
        print("="*80)
        print(f"📋 Chemical Name: {chemical_name}")
        print(f"🤖 Models: {', '.join(model_names)} {'(Multi-Reviewer Mode)' if use_multi_reviewer else '(Single Reviewer)'}")
        print("⚙️  Settings:")
        print(f"   • Risk-of-Bias Assessment: {'✅ Enabled' if enable_rob else '❌ Disabled'}")
        print(f"   • Certainty Grading: {'✅ Enabled' if enable_certainty else '❌ Disabled'}")
        print(f"   • Parallel Processing: {'✅ Enabled' if config.llm.enable_parallel else '❌ Disabled'}")
        print(f"   • GPU Acceleration: {'✅ Enabled' if (gpu_info['available'] and config.llm.use_gpu) else '❌ Disabled'}")
        print("="*80 + "\n")

        # Step A: The Librarian
        if progress:
            progress(0.05, desc="Step 1/6: Standardizing chemical name and searching PubMed...")
        step_start = time.time()
        standardized_name, cid, search_terms = standardize_chemical_name(chemical_name)

        # Store original chemical name for prompt selection (before standardization changes it)
        original_chemical_name = chemical_name.lower()

        # Print Step 1: Chemical Standardization results
        print("📝 STEP 1: CHEMICAL STANDARDIZATION")
        print("-" * 80)
        print(f"   ✓ Standardized Name: {standardized_name}")
        print(f"   ✓ PubChem CID: {cid if cid else 'Not found'}")
        print(f"   ✓ Search Terms: {len(search_terms)} terms")
        print(f"      {', '.join(search_terms[:5])}{'...' if len(search_terms) > 5 else ''}")
        print()

        # Use configurable limit for initial fetch
        print(f"🔍 Searching PubMed with {len(search_terms)} search terms...")
        all_abstracts, search_log = fetch_pubmed_abstracts(
            search_terms,
            max_results=config.search.max_abstracts_initial
        )
        step_elapsed = time.time() - step_start
        print(f"   ✓ Found {len(all_abstracts)} abstracts in {step_elapsed:.1f}s")
        print()
        if progress:
            progress(0.10, desc=f"Step 1/6: Found {len(all_abstracts)} abstracts ({step_elapsed:.1f}s)")

        # Update PRISMA record
        prisma_record.total_records_identified = len(all_abstracts)
        prisma_record.duplicates_removed = 0  # Single database for now

        # Save search log
        try:
            save_search_log(search_log, chemical_name=chemical_name)
        except Exception as e:
            print(f"Warning: Could not save search log: {e}")

        if not all_abstracts:
            search_terms_display = ", ".join(search_terms[:5])
            return f"""Chemical: {standardized_name}
PubChem CID: {cid if cid else 'Not found'}

No abstracts found in PubMed for this chemical.

Search terms tried: {search_terms_display}

Suggestions:
- Try using a different common name for this chemical
- Check if the chemical name spelling is correct
- The chemical may not have published research on liver/hepatotoxicity""", None, None, None, None, None, None

        # Relevance Gatekeeper: Filter abstracts for liver toxicity relevance
        print("🔍 STEP 2: RELEVANCE FILTERING")
        print("-" * 80)
        print(f"   📊 Filtering {len(all_abstracts)} abstracts for liver toxicity relevance...")
        if progress:
            progress(0.15, desc=f"Step 2/6: Filtering {len(all_abstracts)} abstracts for relevance...")
        step_start = time.time()
        relevant_abstracts = []
        excluded_title_abstract = []

        for idx, abstract in enumerate(all_abstracts):
            if progress:
                elapsed = time.time() - step_start
                remaining = (elapsed / (idx + 1)) * (len(all_abstracts) - idx - 1) if idx > 0 else 0
                progress(0.15 + 0.15 * (idx / len(all_abstracts)),
                        desc=f"Step 2/6: Checking relevance ({idx+1}/{len(all_abstracts)}) | Est. remaining: {remaining:.1f}s")

            # Use first model for relevance checking (or could use consensus)
            if check_relevance(abstract.get("abstract", ""), abstract.get("title", ""),
                            standardized_name, model_names[0]):
                relevant_abstracts.append(abstract)
            else:
                excluded_title_abstract.append(abstract)
            # Use configurable limit for analysis
            if len(relevant_abstracts) >= config.search.max_abstracts_analyze:
                print(f"Reached analysis limit ({config.search.max_abstracts_analyze}), stopping relevance filtering")
                break

        step_elapsed = time.time() - step_start
        print(f"   ✓ Relevant: {len(relevant_abstracts)} abstracts")
        print(f"   ✗ Excluded: {len(excluded_title_abstract)} abstracts")
        print(f"   ⏱️  Filtering completed in {step_elapsed:.1f}s")
        print()
        if progress:
            progress(0.30, desc=f"Step 2/6: Found {len(relevant_abstracts)} relevant abstracts ({step_elapsed:.1f}s)")

        # Update PRISMA record
        prisma_record.records_screened_title_abstract = len(all_abstracts)
        prisma_record.records_excluded_title_abstract = len(excluded_title_abstract)
        prisma_record.records_sought_full_text = len(relevant_abstracts)
        prisma_record.records_not_retrieved = 0  # We have abstracts

        if not relevant_abstracts:
            return f"""Chemical: {standardized_name}
PubChem CID: {cid if cid else 'Not found'}

Found {len(all_abstracts)} abstracts, but none were relevant to liver toxicity of this chemical.
The abstracts may discuss other aspects (e.g., cancer efficacy, metabolism elsewhere) but not hepatotoxicity.""", None, None, None, None, None, None

        # Active Learning: Select most informative abstracts (if enabled)
        if config.analysis.enable_active_learning and len(relevant_abstracts) > config.search.max_abstracts_analyze:
            print("🎯 STEP 2.5: ACTIVE LEARNING SELECTION")
            print("-" * 80)
            print(f"   📊 Selecting most informative abstracts from {len(relevant_abstracts)} relevant abstracts...")
            if progress:
                progress(0.30, desc="Step 2.5/6: Active learning selection...")

            try:
                selected_abstracts = select_abstracts_for_analysis(
                    relevant_abstracts,
                    existing_analyses=None,  # No prior analyses for this chemical
                    max_select=config.search.max_abstracts_analyze
                )
                print(f"   ✓ Selected {len(selected_abstracts)} abstracts using active learning")
                print("      (Prioritized by uncertainty, information gain, and impact)")
                abstracts = selected_abstracts
            except Exception as e:
                print(f"   ⚠️  Warning: Active learning failed, using all relevant abstracts: {e}")
                abstracts = relevant_abstracts[:config.search.max_abstracts_analyze]
        else:
            abstracts = relevant_abstracts[:config.search.max_abstracts_analyze]

        # Attempt full-text retrieval for abstracts (optional, but improves RoB assessment)
        print("📄 STEP 2.5: FULL-TEXT RETRIEVAL")
        print("-" * 80)

        # Check if full-text retrieval is enabled
        if not config.search.enable_fulltext_retrieval:
            print("   ⏭️  Full-text retrieval disabled in config. Using abstracts only.")
            print("   💡 To enable, set config.search.enable_fulltext_retrieval = True")
        else:
            print(f"   🔍 Attempting full-text retrieval for {len(abstracts)} studies...")
            if progress:
                progress(0.30, desc="Step 2.5/6: Attempting full-text retrieval...")

            fulltext_count = 0
            retrieval_attempts = 0
            for abstract in abstracts:
                pmid = abstract.get("pmid", "")
                if pmid and pmid != "unknown":
                    retrieval_attempts += 1
                    try:
                        # Check if full-text is available
                        if has_fulltext_available(pmid):
                            # Try with institutional/VPN access first (works without API keys),
                            # then pybliometrics if available, then DOI-based methods
                            full_text, source = fetch_fulltext(
                                pmid,
                                use_pybliometrics=True,  # Will skip if no API key configured
                                use_institutional_access=True  # Works with VPN access
                            )
                            if full_text:
                                # Replace abstract with full-text (keep original abstract as fallback)
                                abstract["fulltext"] = full_text
                                abstract["fulltext_source"] = source
                                fulltext_count += 1
                                print(f"   ✓ Retrieved full-text for PMID {pmid} from {source}")
                    except Exception as e:
                        # Don't fail entire analysis if full-text retrieval fails
                        if config.search.skip_fulltext_on_error:
                            if config.debug:
                                print(f"   ⚠️  Full-text retrieval failed for PMID {pmid}: {e}")
                        else:
                            raise

            coverage_pct = (fulltext_count / len(abstracts) * 100) if abstracts else 0
            print("   📊 Retrieval Results:")
            print(f"      • Attempts: {retrieval_attempts}")
            print(f"      • Success: {fulltext_count}/{len(abstracts)} studies")
            print(f"      • Coverage: {coverage_pct:.1f}%")
            if fulltext_count == 0:
                print("      ⚠️  Using abstracts only (RoB assessment may be limited)")
                print("      💡 Note: Full-text retrieval may require institutional access or VPN.")
                print("      💡 You can disable full-text retrieval by setting config.search.enable_fulltext_retrieval = False")
            print()

        # Create experiment snapshot for reproducibility
        try:
            from reproducibility import create_experiment_snapshot, save_experiment_snapshot

            config_dict = {
                "search": {
                    "max_abstracts_initial": config.search.max_abstracts_initial,
                    "max_abstracts_analyze": config.search.max_abstracts_analyze,
                },
                "llm": {
                    "default_models": config.llm.default_models,
                    "temperature": config.llm.temperature,
                    "temperature_relevance": config.llm.temperature_relevance,
                },
                "analysis": {
                    "enable_rob": enable_rob,
                    "enable_certainty": enable_certainty,
                    "enable_rag": config.analysis.enable_rag,
                    "enable_hierarchical": config.analysis.enable_hierarchical,
                    "prompt_mode": getattr(config.analysis, 'prompt_mode', 'enhanced'),
                    "enable_enhanced_prompts": config.analysis.enable_enhanced_prompts,
                }
            }

            experiment_snapshot = create_experiment_snapshot(
                chemical_name=standardized_name,
                model_names=model_names,
                config_dict=config_dict,
                additional_metadata={
                    "search_query": search_log.get("query", ""),
                    "total_pmids": len(pmids) if pmids else 0,
                }
            )
            snapshot_path = save_experiment_snapshot(experiment_snapshot, output_dir="experiment_snapshots")
            print(f"   📸 Experiment snapshot saved: {snapshot_path}")
        except Exception as e:
            if config.debug:
                print(f"Warning: Experiment snapshot creation failed: {e}")

        # Create provenance record
        prompt_hash = None  # Will be set during first analysis
        provenance_record = create_provenance_record(
            chemical_name=chemical_name,
            model_name=", ".join(model_names) if use_multi_reviewer else model_names[0],
            temperature=config.llm.temperature,
            search_query=search_log.get("query", ""),
            pmids=[a.get("pmid") for a in abstracts]
        )

        # Step B: The Analyst (with causal extraction and CoT reasoning)
        print("🧠 STEP 3: KEY CHARACTERISTICS ANALYSIS")
        print("-" * 80)
        print(f"   📚 Analyzing {len(abstracts)} abstracts against 12 Key Characteristics...")
        print()

        # Multi-reviewer: Run analysis with each model
        all_model_analyses = []  # List of lists: one list per model
        study_records = []
        excluded_full_text = []
        rob_assessments = []
        study_metadata_list = []
        prompt_hash = None

        # Helper function for parallel processing
        def analyze_single_abstract(args):
            """Helper for parallel abstract analysis with enhanced features"""
            abstract, model_name, idx, total = args
            try:
                # Use full-text if available, otherwise use abstract
                abstract_text = abstract.get("abstract", "")
                fulltext = abstract.get("fulltext")

                analysis, _ = analyze_abstract_with_llm(
                    abstract_text,
                    abstract.get("title", ""),
                    model_name,
                    None,  # Don't share prompt_hash across parallel calls
                    fulltext=fulltext,
                    chemical_name=original_chemical_name,  # Use original name for prompt selection
                    use_rag=config.analysis.enable_rag,
                    use_hierarchical=config.analysis.enable_hierarchical,
                    search_terms=search_terms  # Pass search terms for better acetaminophen detection
                )
                analysis["pmid"] = abstract.get("pmid", "unknown")
                analysis["title"] = abstract.get("title", "")
                analysis["fulltext_used"] = "fulltext" in abstract

                # Add to RAG example database if analysis is good
                if config.analysis.enable_rag:
                    try:
                        add_to_example_database(
                            abstract_text,
                            analysis,
                            {"pmid": abstract.get("pmid", ""), "title": abstract.get("title", "")}
                        )
                    except Exception as e:
                        print(f"Warning: Could not add to RAG database: {e}")

                return idx, analysis
            except Exception as e:
                print(f"Error analyzing abstract {idx+1} with {model_name}: {e}")
                # Return empty analysis on error
                error_analysis = dict.fromkeys(KC_DEFINITIONS.keys(), False) | {f"{kc.lower()}_status": "NOT_MENTIONED" for kc in KC_DEFINITIONS} | {"reasoning": f"Error: {str(e)}", "causal_links": [], "evidence_quotes": {}, "pmid": abstract.get("pmid", "unknown"), "title": abstract.get("title", ""), "fulltext_used": False}
                return idx, error_analysis

        # Use parallel processing if enabled
        use_parallel = config.llm.enable_parallel and len(abstracts) > 1

        # Calculate optimal workers based on GPU availability
        optimal_workers = get_optimal_workers(len(abstracts), len(model_names), gpu_count)

        for model_idx, model_name in enumerate(model_names):
            print(f"   🤖 Model {model_idx+1}/{len(model_names)}: {model_name}")
            if progress:
                progress(0.35 + 0.25 * (model_idx / len(model_names)),
                        desc=f"Step 3/6: Model {model_idx+1}/{len(model_names)} ({model_name}) analyzing {len(abstracts)} abstracts...")

            step_start = time.time()

            if use_parallel and optimal_workers > 1:
                # Parallel processing with optimal worker count
                max_workers = optimal_workers
                model_analyses = [None] * len(abstracts)  # Pre-allocate list

                # Use ThreadPoolExecutor for I/O-bound LLM calls (better for Ollama)
                # ProcessPoolExecutor would be better for CPU-bound tasks, but LLM calls are I/O-bound
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all tasks
                    tasks = [
                        (abstract, model_name, i, len(abstracts))
                        for i, abstract in enumerate(abstracts)
                    ]
                    futures = {executor.submit(analyze_single_abstract, task): task for task in tasks}

                    completed = 0
                    for future in as_completed(futures):
                        idx, analysis = future.result()
                        model_analyses[idx] = analysis
                        completed += 1

                        if progress:
                            elapsed = time.time() - step_start
                            avg_time = elapsed / completed if completed > 0 else 5.0
                            remaining = avg_time * (len(abstracts) - completed)
                            model_progress = 0.35 + 0.25 * (model_idx / len(model_names)) + 0.25 * (completed / len(abstracts)) / len(model_names)
                            progress(model_progress,
                                    desc=f"Step 3/6: [{model_name}] Analyzing {completed}/{len(abstracts)} | Workers: {max_workers} | Elapsed: {elapsed:.1f}s | Est. remaining: {remaining:.1f}s")
            else:
                # Sequential processing (original method)
                model_analyses = []
                for i, abstract in enumerate(abstracts):
                    if (i + 1) % max(1, len(abstracts) // 10) == 0 or i == 0:
                        print(f"      📄 Progress: {i+1}/{len(abstracts)} abstracts analyzed...")
                    if progress:
                        elapsed = time.time() - step_start
                        avg_time = elapsed / (i + 1) if i > 0 else 5.0
                        remaining = avg_time * (len(abstracts) - i - 1)
                        model_progress = 0.35 + 0.25 * (model_idx / len(model_names)) + 0.25 * (i / len(abstracts)) / len(model_names)
                        progress(model_progress,
                                desc=f"Step 3/6: [{model_name}] Analyzing KC {i+1}/{len(abstracts)} | Elapsed: {elapsed:.1f}s | Est. remaining: {remaining:.1f}s")

                    # Use full-text if available, otherwise use abstract
                    abstract_text = abstract.get("abstract", "")
                    fulltext = abstract.get("fulltext")

                    analysis, prompt_hash = analyze_abstract_with_llm(
                        abstract_text,
                        abstract.get("title", ""),
                        model_name,
                        prompt_hash,
                        fulltext=fulltext,
                        chemical_name=original_chemical_name,  # Use original name for prompt selection
                        use_rag=config.analysis.enable_rag,
                        use_hierarchical=config.analysis.enable_hierarchical,
                        search_terms=search_terms  # Pass search terms for better acetaminophen detection
                    )

                    # Add to RAG example database if analysis is good
                    if config.analysis.enable_rag:
                        try:
                            add_to_example_database(
                                abstract_text,
                                analysis,
                                {"pmid": abstract.get("pmid", ""), "title": abstract.get("title", "")}
                            )
                        except Exception as e:
                            print(f"Warning: Could not add to RAG database: {e}")

                    # Add metadata to analysis
                    analysis["pmid"] = abstract.get("pmid", "unknown")
                    analysis["title"] = abstract.get("title", "")
                    analysis["fulltext_used"] = "fulltext" in abstract
                    model_analyses.append(analysis)

            step_elapsed = time.time() - step_start
            print(f"      ✓ Completed analysis in {step_elapsed:.1f}s")
            print()
            all_model_analyses.append(model_analyses)

        # Consolidate multi-reviewer results if using multiple models
        if use_multi_reviewer:
            print("   🔄 Consolidating multi-reviewer results...")
            if progress:
                progress(0.60, desc="Step 3.5/6: Consolidating multi-reviewer results...")
            # Use weighted consensus if configured
            consensus_method = config.analysis.consensus_method
            consolidated_analyses, agreement_stats = consolidate_kc_analyses(
                all_model_analyses, model_names, consensus_method=consensus_method
            )
            ranked_papers = rank_papers_by_consensus(consolidated_analyses, ranking_method="combined")
            print("      ✓ Consensus analysis complete")
            print()

            # Convert consolidated format back to standard format for compatibility
            kc_analyses = []
            for consolidated in consolidated_analyses:
                # Extract consensus statuses
                analysis_dict = {}
                for kc in [f"KC{i}" for i in range(1, 13)]:
                    kc_data = consolidated["consensus"].get(kc, {})
                    if isinstance(kc_data, dict):
                        analysis_dict[f"{kc.lower()}_status"] = kc_data.get("status", "NOT_MENTIONED")
                    else:
                        analysis_dict[f"{kc.lower()}_status"] = "NOT_MENTIONED"

                # Preserve other important fields from original analyses
                # Use the first model's analysis as base (or merge from all models)
                reviewer_analyses = consolidated.get("reviewer_analyses", {})
                if reviewer_analyses:
                    # Use first model's analysis for fields like causal_links, evidence_quotes, reasoning
                    first_model_analysis = list(reviewer_analyses.values())[0]

                    # Preserve causal_links and evidence_quotes (these are typically consistent across models)
                    if "causal_links" in first_model_analysis:
                        analysis_dict["causal_links"] = first_model_analysis["causal_links"]
                    if "evidence_quotes" in first_model_analysis:
                        analysis_dict["evidence_quotes"] = first_model_analysis["evidence_quotes"]
                    if "reasoning" in first_model_analysis:
                        analysis_dict["reasoning"] = first_model_analysis["reasoning"]

                analysis_dict["pmid"] = consolidated.get("pmid", "unknown")
                analysis_dict["title"] = consolidated.get("title", "")
                kc_analyses.append(analysis_dict)
        else:
            # Single model: use first (and only) model's analyses
            kc_analyses = all_model_analyses[0] if all_model_analyses else []
            consolidated_analyses = None
            agreement_stats = None
            ranked_papers = None

        # Apply confidence scoring and calibration if enabled
        if config.analysis.enable_confidence_scoring:
            print("   📊 Applying confidence scoring and calibration...")
            try:
                # Calibrate predictions
                calibration_model = get_calibration_model()
                kc_analyses = calibrate_predictions(kc_analyses, calibration_model)
                print(f"      ✓ Calibrated {len(kc_analyses)} analyses")
            except Exception as e:
                print(f"      ⚠️  Warning: Calibration failed: {e}")

        # Filter low-confidence predictions if configured
        if config.analysis.enable_confidence_scoring and config.analysis.filter_low_confidence:
            try:
                high_conf, low_conf = filter_low_confidence_predictions(
                    kc_analyses,
                    confidence_threshold=config.analysis.confidence_threshold
                )
                print(f"      📊 Confidence filtering: {len(high_conf)} high-confidence, {len(low_conf)} low-confidence")
                # Optionally use only high-confidence, or flag low-confidence
                if config.analysis.use_only_high_confidence:
                    kc_analyses = high_conf
                    abstracts = [ab for i, ab in enumerate(abstracts) if i < len(high_conf)]
            except Exception as e:
                print(f"      ⚠️  Warning: Confidence filtering failed: {e}")

        # Create study metadata and Risk-of-Bias assessments
        print("⚖️  STEP 4: RISK-OF-BIAS ASSESSMENT")
        print("-" * 80)
        if enable_rob:
            print(f"   📊 Assessing risk-of-bias for {len(abstracts)} studies...")
        else:
            print("   ⏭️  Risk-of-Bias assessment disabled")
        print()

        for i, abstract in enumerate(abstracts):
            study_metadata_list.append({
                "pmid": abstract.get("pmid", "unknown"),
                "study_type": "Toxicology",
                "species": None
            })

            # Risk-of-Bias Assessment (use first model for RoB)
            # Use full-text if available for better RoB assessment
            if enable_rob:
                try:
                    if (i + 1) % max(1, len(abstracts) // 10) == 0 or i == 0:
                        print(f"      📄 Progress: {i+1}/{len(abstracts)} studies assessed...")
                    if progress:
                        progress(0.65 + 0.10 * (i / len(abstracts)),
                                desc=f"Step 4/6: Assessing Risk-of-Bias {i+1}/{len(abstracts)}...")

                    # Use full-text if available, otherwise abstract
                    # Prioritize fulltext over abstract for better RoB assessment
                    fulltext_content = abstract.get("fulltext", "")
                    abstract_content = abstract.get("abstract", "")
                    text_for_rob = fulltext_content if fulltext_content else abstract_content

                    # Log what we're using for RoB assessment
                    if fulltext_content:
                        print(f"      📄 Using full-text for RoB assessment (PMID {abstract.get('pmid', 'unknown')}, {len(fulltext_content)} chars)")
                    else:
                        print(f"      📄 Using abstract only for RoB assessment (PMID {abstract.get('pmid', 'unknown')}, {len(abstract_content)} chars)")

                    # Use first model for RoB, with fallback for invalid model names
                    rob_model = model_names[0] if model_names else "llama3.2"
                    # Fix common typos/old model names
                    if rob_model == "llama3":
                        rob_model = "llama3.2"  # Fix typo: llama3 -> llama3.2

                    rob_assessment = assess_rob_with_llm(
                        text_for_rob,
                        abstract.get("title", ""),
                        abstract.get("pmid", "unknown"),
                        rob_model,
                        instrument="OHAT"
                    )
                    rob_assessments.append(rob_assessment)
                except Exception as e:
                    print(f"      ⚠️  Warning: RoB assessment failed for study {i+1}: {e}")
                    rob_assessments.append(assess_roh_ohat(
                        {"pmid": abstract.get("pmid", "unknown")},
                        abstract.get("abstract", "")
                    ))
            else:
                rob_assessments.append(assess_roh_ohat(
                    {"pmid": abstract.get("pmid", "unknown")},
                    abstract.get("abstract", "")
                ))

            # Create study record for provenance (use consolidated analysis if available)
            analysis_for_record = kc_analyses[i] if i < len(kc_analyses) else {}
            study_record = {
                "metadata": {
                    "pmid": abstract.get("pmid", "unknown"),
                    "title": abstract.get("title", ""),
                    "year": abstract.get("year"),
                    "authors": abstract.get("authors"),
                    "journal": abstract.get("journal")
                },
                "kc_analysis": analysis_for_record,
                "risk_of_bias": rob_assessments[-1].model_dump() if rob_assessments else None,
                "screening_stage": "included",
                "extraction_date": datetime.now().isoformat(),
                "provenance": {
                    "models": model_names,
                    "prompt_hash": prompt_hash,
                    "multi_reviewer": use_multi_reviewer
                }
            }

            if use_multi_reviewer and i < len(consolidated_analyses):
                study_record["multi_reviewer_consensus"] = consolidated_analyses[i].get("consensus", {})
                study_record["agreement_scores"] = consolidated_analyses[i].get("agreement_scores", {})

            try:
                save_study_record(study_record, chemical_name=chemical_name)
            except Exception as e:
                print(f"Warning: Could not save study record: {e}")

            study_records.append(study_record)

        if enable_rob and rob_assessments:
            # Print overall RoB judgments summary
            rob_summary = {}
            for rob in rob_assessments:
                overall = rob.overall_judgment if hasattr(rob, 'overall_judgment') else "Unknown"
                rob_summary[overall] = rob_summary.get(overall, 0) + 1
            print("   ✓ Risk-of-Bias assessment complete:")
            for judgment, count in rob_summary.items():
                print(f"      • {judgment}: {count} studies")
            print()

        # Update PRISMA record
        prisma_record.records_assessed_full_text = len(abstracts)
        prisma_record.records_excluded_full_text = len(excluded_full_text)
        prisma_record.studies_included = len(abstracts)
        prisma_record.studies_included_list = [a.get("pmid") for a in abstracts]

        # Update provenance with prompt hash
        provenance_record["prompt"]["hash"] = prompt_hash or "unknown"

        # Save provenance
        try:
            save_provenance(provenance_record, chemical_name=chemical_name)
        except Exception as e:
            print(f"Warning: Could not save provenance: {e}")

        # Step C: The Architect
        print("📊 STEP 5: VISUALIZATIONS")
        print("-" * 80)
        if progress:
            progress(0.80, desc="Step 5/6: Generating visualizations (Evidence Matrix, Network Graph, PRISMA)...")
        step_start = time.time()

        print("   🎨 Creating visualizations...")
        print("      • Evidence Matrix Heatmap...")
        print(f"         Creating matrix for {len(abstracts)} abstracts and {len(kc_analyses)} analyses...")
        evidence_matrix = create_evidence_matrix(abstracts, kc_analyses)
        print(f"         Matrix created: {len(evidence_matrix)} rows, {len(evidence_matrix.columns)} columns")
        print(f"         KC columns: {[col for col in evidence_matrix.columns if col.startswith('KC')]}")
        print("         Generating heatmap visualization...")
        heatmap_fig = create_heatmap(evidence_matrix)
        print("         ✓ Heatmap created")
        print("      • Causal Pathway Network...")
        network_fig = create_network_graph(kc_analyses, rob_assessments if enable_rob else None)
        print("      • PRISMA Flow Diagram...")
        prisma_fig = create_prisma_flow_diagram(prisma_record)

        # Risk-of-Bias Visualizations
        rob_heatmap_fig = None
        rob_summary_fig = None
        if enable_rob and rob_assessments:
            try:
                print("      • Risk-of-Bias Heatmap...")
                if progress:
                    progress(0.85, desc="Step 5/6: Creating Risk-of-Bias visualizations...")
                rob_heatmap_fig = create_rob_heatmap_figure(
                    rob_assessments, list(KC_DEFINITIONS.keys()), kc_analyses
                )
                print("      • Risk-of-Bias Summary...")
                rob_summary_fig = create_rob_summary_figure(rob_assessments)
            except Exception as e:
                print(f"      ⚠️  Warning: RoB visualization failed: {e}")

        step_elapsed = time.time() - step_start
        print(f"   ✓ All visualizations created in {step_elapsed:.1f}s")
        print()

        # Certainty Grading
        print("📈 STEP 6: CERTAINTY GRADING")
        print("-" * 80)
        certainty_assessments = []
        evidence_profiles_text = None
        if enable_certainty:
            try:
                print("   📊 Assessing certainty of evidence for 12 Key Characteristics...")
                if progress:
                    progress(0.90, desc="Step 6/6: Assessing certainty of evidence per KC...")
                for idx, kc in enumerate(KC_DEFINITIONS.keys()):
                    if progress:
                        progress(0.90 + 0.05 * (idx / len(KC_DEFINITIONS.keys())),
                                desc=f"Step 6/6: Assessing certainty for {kc} ({idx+1}/{len(KC_DEFINITIONS.keys())})...")
                    certainty = assess_certainty_per_kc(
                        kc, kc_analyses, rob_assessments, study_metadata_list
                    )
                    certainty_assessments.append(certainty)
                    if (idx + 1) % 3 == 0 or idx == 0:
                        print(f"      📄 Progress: {idx+1}/12 KCs assessed...")

                # Create evidence profile cards
                print("      📋 Generating evidence profile cards...")
                if progress:
                    progress(0.95, desc="Step 6/6: Generating evidence profile cards...")
                evidence_profiles_text = create_all_evidence_profiles(
                    kc_analyses, certainty_assessments, KC_NAMES
                )
                print("   ✓ Certainty grading complete for all 12 KCs")
                print()
            except Exception as e:
                print(f"   ⚠️  Warning: Certainty grading failed: {e}")
                evidence_profiles_text = "Certainty assessment could not be completed."
                print()
        else:
            print("   ⏭️  Certainty grading disabled")
            print()

        step_elapsed = time.time() - step_start
        total_elapsed = time.time() - start_time

        # ============================================================================
        # COMPLETION SUMMARY
        # ============================================================================
        print("="*80)
        print("✅ ANALYSIS COMPLETE")
        print("="*80)

        # Calculate summary statistics
        total_papers = len(abstracts)
        kc_supported = {kc: sum(1 for analysis in kc_analyses
                                if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") in ["SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"])
                        for kc in KC_DEFINITIONS}
        total_causal_links = sum(len(analysis.get("causal_links", [])) for analysis in kc_analyses)
        total_quotes = sum(len(quotes) for analysis in kc_analyses
                          for quotes in analysis.get("evidence_quotes", {}).values())

        print("📊 Summary Statistics:")
        print(f"   • Papers Analyzed: {total_papers}")
        print(f"   • Key Characteristics Supported: {sum(kc_supported.values())} total instances")
        print(f"   • Causal Links Identified: {total_causal_links}")
        print(f"   • Evidence Quotes Extracted: {total_quotes}")
        if enable_rob and rob_assessments:
            rob_stats = calculate_rob_summary_stats(rob_assessments)
            print(f"   • Risk-of-Bias Assessments: {len(rob_assessments)} studies")
        if enable_certainty and certainty_assessments:
            print(f"   • Certainty Assessments: {len(certainty_assessments)} KCs")
        print(f"\n⏱️  Total Processing Time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
        print(f"📁 Results Location: results/{chemical_name.replace(' ', '_')}/")
        print("="*80 + "\n")

        if progress:
            progress(1.0, desc=f"Complete! Total time: {total_elapsed:.1f}s")

        # Create summary text with enhanced statistics
        # (total_papers, kc_supported, total_causal_links, total_quotes already calculated above)
        kc_refuted = {kc: sum(1 for analysis in kc_analyses
                              if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "REFUTED")
                      for kc in KC_DEFINITIONS}

        # Show search terms used
        search_terms_display = ", ".join(search_terms[:3])
        if len(search_terms) > 3:
            search_terms_display += f" (+{len(search_terms)-3} more)"

        # Generate PRISMA text summary
        prisma_summary = generate_prisma_text_summary(prisma_record)

        # Build summary with certainty ratings
        models_display = ", ".join(model_names) if len(model_names) <= 3 else f"{', '.join(model_names[:2])} (+{len(model_names)-2} more)"
        summary = f"""Chemical Analysis Summary
{'='*60}
Input Name: {chemical_name}
Standardized Name: {standardized_name}
PubChem CID: {cid if cid else 'Not found'}
Models Used: {models_display} {'(Multi-Reviewer Mode)' if use_multi_reviewer else '(Single Reviewer)'}
Search Terms Used: {search_terms_display}
Total Papers Analyzed: {total_papers} (filtered from {len(all_abstracts)} retrieved)
Total Causal Links Identified: {total_causal_links}
Total Evidence Quotes Extracted: {total_quotes}

{prisma_summary}
"""

        # Add multi-reviewer agreement statistics
        if use_multi_reviewer and agreement_stats:
            summary += f"""
Multi-Reviewer Agreement Statistics:
{'-'*60}
Overall Agreement: {agreement_stats['overall_agreement']['mean_agreement']:.1%} 
  (Range: {agreement_stats['overall_agreement']['min_agreement']:.1%} - {agreement_stats['overall_agreement']['max_agreement']:.1%})

Inter-Model Agreement (Cohen's κ):
"""
            if "inter_model_agreement" in agreement_stats:
                for pair in agreement_stats["inter_model_agreement"]["pairwise_kappa"]:
                    summary += f"  • {pair['model_1']} vs {pair['model_2']}: κ = {pair['kappa']:.3f} ({pair['interpretation']})\n"
                summary += f"  Mean κ: {agreement_stats['inter_model_agreement']['mean_kappa']:.3f}\n"

            if ranked_papers:
                summary += "\nTop Ranked Papers (by Consensus Strength):\n"
                for i, paper in enumerate(ranked_papers[:5]):  # Top 5
                    summary += f"  {i+1}. PMID {paper.get('pmid', 'N/A')}: Agreement={paper['agreement_scores']['overall']:.1%}, Score={paper['ranking_score']:.3f}\n"

            summary += "\n"

        summary += "Key Characteristics Evidence:\n"
        for kc, name in KC_NAMES.items():
            supported = kc_supported.get(kc, 0)
            refuted = kc_refuted.get(kc, 0)
            summary += f"  {kc} ({name}):\n"
            summary += f"    ✓ Supported: {supported}/{total_papers} papers\n"
            if refuted > 0:
                summary += f"    ✗ Refuted: {refuted}/{total_papers} papers\n"

            # Add certainty rating if available
            if enable_certainty and certainty_assessments:
                certainty = next((c for c in certainty_assessments if c.kc == kc), None)
                if certainty:
                    summary += f"    📊 Certainty: {certainty.final_certainty}\n"

        # Add RoB summary if available
        if enable_rob and rob_assessments:
            rob_stats = calculate_rob_summary_stats(rob_assessments)
            summary += "\nRisk-of-Bias Summary:\n"
            summary += f"  • Low Risk: {rob_stats.get('overall_distribution', {}).get('Low', 0)}/{rob_stats.get('total_studies', 0)} studies\n"
            summary += f"  • Some Concerns: {rob_stats.get('overall_distribution', {}).get('Some concerns', 0)}/{rob_stats.get('total_studies', 0)} studies\n"
            summary += f"  • High Risk: {rob_stats.get('overall_distribution', {}).get('High', 0)}/{rob_stats.get('total_studies', 0)} studies\n"
            summary += f"  • Insufficient Information: {rob_stats.get('insufficient_info_count', 0)}/{rob_stats.get('total_studies', 0)} studies\n"
            summary += f"  • Full-text Used: {rob_stats.get('fulltext_used_count', 0)}/{rob_stats.get('total_studies', 0)} studies ({rob_stats.get('fulltext_percentage', 0):.1f}%)\n"

        total_elapsed = time.time() - start_time
        summary += "\nAnalysis complete. The causal pathway network shows mechanistic relationships between KCs."
        summary += f"\n\n⏱️ Total processing time: {total_elapsed:.1f} seconds"

        # Add full-text retrieval summary
        if fulltext_count > 0:
            summary += f"\n\n📄 Full-text retrieval: {fulltext_count}/{len(abstracts)} studies had full-text available"
            summary += "\n   (Full-text improves risk-of-bias assessment quality)"

        # Save all plots to disk
        saved_plots_info = {}
        try:
            print("Saving plots to disk...")
            saved_plots = save_all_plots(
                heatmap_fig=heatmap_fig,
                network_fig=network_fig,
                prisma_fig=prisma_fig,
                rob_heatmap_fig=rob_heatmap_fig,
                rob_summary_fig=rob_summary_fig,
                output_dir="results",
                chemical_name=chemical_name,
                dpi=300
            )
            saved_plots_info = saved_plots
            plot_summary = "\n\nPlots saved to:"
            for plot_type, files in saved_plots.items():
                if files and 'png' in files:
                    plot_summary += f"\n  • {plot_type}: {files['png']}"
            summary += plot_summary
        except Exception as e:
            print(f"Warning: Could not save plots: {e}")

        summary += f"\n\nResults saved to: results/{chemical_name.replace(' ', '_')}/"

        # Create interactive Risk-of-Bias table
        rob_table_df = None
        if enable_rob and rob_assessments and abstracts:
            rob_table_data = []
            for i, (rob, abstract) in enumerate(zip(rob_assessments, abstracts)):
                rob_table_data.append({
                    "Study #": i + 1,
                    "PMID": abstract.get("pmid", "unknown"),
                    "Title": abstract.get("title", "")[:80] + "..." if len(abstract.get("title", "")) > 80 else abstract.get("title", ""),
                    "Overall Judgment": rob.overall_judgment if hasattr(rob, 'overall_judgment') else "Unknown",
                    "Full-text": "Yes" if abstract.get("fulltext") else "No"
                })
            rob_table_df = pd.DataFrame(rob_table_data)

        # Store saved_plots_info in a way that can be accessed later
        # We'll pass it through a state variable
        return summary, heatmap_fig, network_fig, prisma_fig, rob_heatmap_fig, rob_summary_fig, evidence_profiles_text, rob_table_df, abstracts, saved_plots_info

    except Exception as e:
        models_str = ", ".join(model_names) if model_names else "selected model"
        error_msg = f"Error during analysis: {str(e)}\n\nPlease ensure Ollama is running and the model(s) are installed.\n\nTo install Ollama: https://ollama.ai\nTo pull models: ollama pull {models_str}"
        return error_msg, None, None, None, None, None, None, None, [], {}


# Gradio Interface
def create_interface():
    with gr.Blocks(title="AI Toxicologist") as app:
        with gr.Tabs():
            # Tab 1: Help Section
            with gr.Tab("❓ Help"):
                HELP_CONTENT = HELP_CONTENT_TEMPLATE.format(
                    MAX_ABSTRACTS_INITIAL=config.search.max_abstracts_initial,
                    MAX_ABSTRACTS_ANALYZE=config.search.max_abstracts_analyze,
                    MAX_SEARCH_TERMS=config.search.max_search_terms,
                    PARALLEL_PROCESSING_STATUS=('Enabled' if config.llm.enable_parallel else 'Disabled'),
                    GPU_ACCELERATION_STATUS=('Enabled' if (gpu_info['available'] and config.llm.use_gpu) else 'Disabled'),
                    GPU_COUNT=gpu_count,
                    MPI_SUPPORT_STATUS=('Available' if MPI_ENABLED else 'Not Available'),
                    MAX_ABSTRACTS_INITIAL_DEFAULT=config.search.max_abstracts_initial,
                    MAX_ABSTRACTS_ANALYZE_DEFAULT=config.search.max_abstracts_analyze,
                    LLM_TEMPERATURE_DEFAULT=config.llm.temperature
                )
                gr.Markdown(HELP_CONTENT)

            # Tab 2: Systematic Review Analysis
            with gr.Tab("🔬 Systematic Review"):
                gr.Markdown("""
        # 🔬 AI Toxicologist: Hepatotoxicity Assessment

        Welcome to the AI Toxicologist application! This tool performs a **PRISMA-compliant systematic literature review** to assess the hepatotoxicity potential of chemicals. For detailed features, configuration, and instructions on how to run and use the application, please navigate to the **"Help" tab**.
        """)

                with gr.Row():
                    with gr.Column(scale=2):
                        chemical_input = gr.Textbox(
                            label="Chemical Name",
                            placeholder="e.g., acetaminophen, carbon tetrachloride, ethanol",
                            value=""
                        )
                    with gr.Column(scale=1):
                        model_checkboxes = gr.CheckboxGroup(
                            label="Ollama Models (Multi-Reviewer Mode)",
                            choices=config.llm.available_models,
                            value=config.llm.default_models if config.llm.default_models else ["llama3.2"],
                            info="Select 1+ models. Multiple models = Multi-Reviewer mode with consensus"
                        )

                analyze_btn = gr.Button("🔍 Analyze Chemical", variant="primary", size="lg")

                with gr.Accordion("🤖 RL Prompt Optimization (Phase 1)", open=False):
                    dspy_status = gr.Textbox(
                        label="Optimizer Status",
                        value=(
                            "✅ Optimized prompts loaded — using DSPy classifier"
                            if _dspy_classifier is not None
                            else ("⚙️ DSPy installed — run optimization to improve KC accuracy"
                                  if _dspy_available
                                  else "ℹ️ Install dspy-ai to enable prompt optimization")
                        ),
                        interactive=False,
                        lines=1,
                    )
                    with gr.Row():
                        optimize_btn = gr.Button(
                            "⚡ Optimize Prompts",
                            variant="secondary",
                            interactive=_dspy_available,
                        )
                        optimizer_choice = gr.Radio(
                            choices=["bootstrap", "mipro"],
                            value="bootstrap",
                            label="Optimizer",
                            info="bootstrap=fast (~5 min), mipro=thorough (~30 min)",
                        )
                    optimize_output = gr.Textbox(
                        label="Optimization Log", lines=6, interactive=False
                    )

                    def run_prompt_optimization(model_list, opt_type):
                        if not _dspy_available:
                            return "❌ dspy-ai not installed. Run: pip install dspy-ai"
                        try:
                            from dspy_optimizer import run_optimization, save_optimized_program
                            from training_data_builder import load_training_examples
                            examples = load_training_examples()
                            if not examples:
                                return "❌ No training examples found. Analyze some chemicals first."
                            model = model_list[0] if model_list else "llama3.2"
                            log = [f"Starting optimization with {len(examples)} examples on {model}..."]
                            optimized, score = run_optimization(
                                training_examples=examples,
                                model_name=model,
                                optimizer_type=opt_type,
                            )
                            save_optimized_program(optimized, score, {"model": model, "optimizer": opt_type})
                            _load_dspy_classifier()
                            log.append(f"✅ Done! Score: {score:.3f}")
                            log.append("Optimized prompts saved and loaded. Restart app to apply.")
                            return "\n".join(log)
                        except Exception as e:
                            return f"❌ Optimization failed: {e}"

                    optimize_btn.click(
                        fn=run_prompt_optimization,
                        inputs=[
                            gr.State(config.llm.default_models),
                            optimizer_choice,
                        ],
                        outputs=optimize_output,
                    )

                gr.Markdown("---")

                with gr.Row():
                    summary_output = gr.Textbox(
                        label="Analysis Summary",
                        lines=15,
                        interactive=False
                    )

                with gr.Row():
                    heatmap_output = gr.Plot(label="Evidence Matrix Heatmap")
                    network_output = gr.Plot(label="Mechanistic Pathway Network")

                with gr.Row():
                    prisma_output = gr.Plot(label="PRISMA 2020 Flow Diagram")

                with gr.Row():
                    rob_heatmap_output = gr.Plot(label="Risk-of-Bias Heatmap (by KC and Domain)")
                    rob_summary_output = gr.Plot(label="Risk-of-Bias Summary")

                with gr.Row():
                    with gr.Column(scale=1):
                        rob_table_output = gr.Dataframe(
                            label="Risk-of-Bias Assessments (Click a row to view abstract)",
                            interactive=True,
                            wrap=True,
                            visible=False
                        )
                    with gr.Column(scale=1):
                        abstract_viewer = gr.Textbox(
                            label="Abstract (Click a row above to view)",
                            lines=15,
                            interactive=True,  # Make interactive so users can copy manually
                            visible=False
                        )

                with gr.Row():
                    evidence_profiles_output = gr.Textbox(
                        label="Evidence Profile Cards",
                        lines=30,
                        interactive=False,
                        visible=True
                    )

                with gr.Row():
                    enable_rob_checkbox = gr.Checkbox(
                        label="Enable Risk-of-Bias Assessment (LLM-based)",
                        value=True,
                        info="Assess risk-of-bias for each study using LLM"
                    )
                    enable_certainty_checkbox = gr.Checkbox(
                        label="Enable Certainty Grading (GRADE/OHAT)",
                        value=True,
                        info="Calculate certainty of evidence per KC"
                    )

                def analyze_with_progress(chem, models, rob, cert, progress=gr.Progress()):
                    # Convert checkbox selections to list and normalize model names
                    def normalize_model_name(model_name: str) -> str:
                        """Fix common model name typos and old names"""
                        model_name = model_name.strip()
                        if model_name == "llama3" or model_name == "lamma3" or model_name == "lamma3.2":
                            return "llama3.2"
                        if model_name == "lamma3.1":
                            return "llama3.1"
                        return model_name

                    if not models or len(models) == 0:
                        models = ["llama3.2"]  # Updated default fallback
                    else:
                        # Normalize model names to fix typos
                        models = [normalize_model_name(m) if isinstance(m, str) else m for m in models]
                    return analyze_chemical(chem, models, rob, cert, progress)

                # Store abstracts for interactive viewing (using Gradio's state)
                abstracts_state = gr.State(value=[])

                def show_abstract_from_table(evt: gr.SelectData, abstracts_list):
                    """Show abstract when a row in the RoB table is clicked"""
                    try:
                        if evt is None or abstracts_list is None or len(abstracts_list) == 0:
                            return ""

                        # Gradio SelectData for Dataframe has index attribute that is a tuple (row, col)
                        # Get the row index from the event
                        row_idx = None
                        if hasattr(evt, 'index'):
                            if isinstance(evt.index, (list, tuple)) and len(evt.index) > 0:
                                row_idx = evt.index[0]
                            elif isinstance(evt.index, int):
                                row_idx = evt.index

                        if row_idx is None or row_idx >= len(abstracts_list):
                            return "Please select a row from the table above."

                        abstract = abstracts_list[row_idx]
                        title = abstract.get("title", "No title")
                        pmid = abstract.get("pmid", "unknown")
                        abstract_text = abstract.get("abstract", "No abstract available")
                        authors = abstract.get("authors", "Unknown authors")
                        journal = abstract.get("journal", "Unknown journal")
                        year = abstract.get("year", "Unknown year")

                        # Format the display
                        formatted = f"""Title: {title}
PMID: {pmid}
Authors: {authors}
Journal: {journal}
Year: {year}

Abstract:
{abstract_text}"""

                        return formatted
                    except Exception as e:
                        import traceback
                        return f"Error displaying abstract: {str(e)}\n{traceback.format_exc()}"

                def update_rob_table_visibility(rob_df, abstracts):
                    """Update visibility of RoB table and abstract viewer"""
                    has_data = rob_df is not None and len(rob_df) > 0 if isinstance(rob_df, pd.DataFrame) else False
                    return (
                        gr.update(visible=has_data, value=rob_df),
                        gr.update(visible=has_data),
                        abstracts if abstracts else []
                    )

                def show_analysis_chatbot(abstracts):
                    """Show chatbot when analysis completes"""
                    has_abstracts = abstracts is not None and len(abstracts) > 0
                    welcome_msg = []
                    if has_abstracts:
                        welcome_msg = [[None, f"✅ Analysis complete! I can now answer questions about the {len(abstracts)} analyzed abstracts.\n\nAsk me about:\n- Key Characteristics (KC1-KC12)\n- Specific mechanisms or pathways\n- Evidence from particular studies\n- Overall findings\n\nExample: 'What evidence supports KC5 (oxidative stress) for this chemical?'"]]
                    return (
                        gr.update(visible=has_abstracts, value=welcome_msg),
                        gr.update(visible=has_abstracts),
                        gr.update(visible=has_abstracts),
                        gr.update(visible=has_abstracts)
                    )

                gr.Markdown("""
                ---
                ## 💬 Ask Questions About the Analyzed Abstracts
                
                Use the chatbot below to ask questions about the abstracts that were just analyzed.
                The chatbot uses RAG (Retrieval-Augmented Generation) to find relevant information from the analyzed abstracts.
                
                **💡 Tip:** The system automatically searches the `results/` folder and prepares all available analyses. 
                Select any analysis from the dropdown below to load all results (summary, plots, tables, and enable chat).
                """)

                # Function to save all analysis results for later reload
                def save_complete_analysis_results(chemical_name, abstracts, summary_text,
                                                  evidence_profiles, rob_table_df, saved_plots_info):
                    """Save all analysis results to file for later reload"""
                    if not abstracts or len(abstracts) == 0:
                        return None

                    try:
                        import os
                        results_dir = f"results/{chemical_name.replace(' ', '_')}"
                        os.makedirs(results_dir, exist_ok=True)

                        # Save abstracts as JSON (for chat)
                        abstracts_file = os.path.join(results_dir, "abstracts_for_chat.json")
                        with open(abstracts_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                "chemical_name": chemical_name,
                                "abstracts": abstracts,
                                "saved_at": datetime.now().isoformat(),
                                "num_abstracts": len(abstracts)
                            }, f, indent=2, ensure_ascii=False)

                        # Convert plot paths to relative paths for portability
                        relative_plots = {}
                        if saved_plots_info:
                            for plot_type, files in saved_plots_info.items():
                                if files and 'png' in files:
                                    plot_path = files['png']
                                    # Convert to relative path if absolute
                                    if os.path.isabs(plot_path):
                                        try:
                                            relative_path = os.path.relpath(plot_path, results_dir)
                                            relative_plots[plot_type] = {'png': relative_path}
                                        except:
                                            # If relpath fails, keep absolute
                                            relative_plots[plot_type] = {'png': plot_path}
                                    else:
                                        relative_plots[plot_type] = {'png': plot_path}

                        # Save complete analysis results
                        results_file = os.path.join(results_dir, "analysis_results.json")
                        results_data = {
                            "chemical_name": chemical_name,
                            "saved_at": datetime.now().isoformat(),
                            "num_abstracts": len(abstracts),
                            "summary_text": summary_text or "",
                            "evidence_profiles": evidence_profiles or "",
                            "saved_plots": relative_plots
                        }

                        # Save RoB table if available
                        if rob_table_df is not None and not rob_table_df.empty:
                            rob_table_file = os.path.join(results_dir, "rob_table.json")
                            try:
                                rob_table_df.to_json(rob_table_file, orient='records', indent=2)
                                results_data["rob_table_file"] = "rob_table.json"  # Relative path
                            except Exception as e:
                                print(f"Warning: Could not save RoB table: {e}")

                        with open(results_file, 'w', encoding='utf-8') as f:
                            json.dump(results_data, f, indent=2, ensure_ascii=False)

                        print(f"✅ Saved complete analysis results: {results_file}")
                        return results_file
                    except Exception as e:
                        print(f"Warning: Could not save analysis results: {e}")
                        import traceback
                        traceback.print_exc()
                        return None

                def load_complete_analysis_results(selected_label):
                    """Load all analysis results from selected analysis file"""
                    if not selected_label:
                        return None, None, None, None, None, None, None, None, []

                    try:
                        # Find the file path from the label
                        analyses = get_available_analyses()
                        selected_file = None
                        for a in analyses:
                            if a["label"] == selected_label:
                                # Get the results directory
                                abstracts_file = a["value"]
                                results_dir = os.path.dirname(abstracts_file)
                                selected_file = os.path.join(results_dir, "analysis_results.json")
                                break

                        if not selected_file or not os.path.exists(selected_file):
                            return None, None, None, None, None, None, None, None, []

                        # Load analysis results
                        with open(selected_file, encoding='utf-8') as f:
                            results_data = json.load(f)

                        # Load abstracts
                        abstracts_file = os.path.join(os.path.dirname(selected_file), "abstracts_for_chat.json")
                        if os.path.exists(abstracts_file):
                            with open(abstracts_file, encoding='utf-8') as f:
                                abstracts_data = json.load(f)
                            abstracts = abstracts_data.get("abstracts", [])
                        else:
                            abstracts = []

                        summary_text = results_data.get("summary_text", "")
                        evidence_profiles = results_data.get("evidence_profiles", "")
                        saved_plots = results_data.get("saved_plots", {})

                        # Load plots from saved files
                        import matplotlib.image as mpimg
                        import matplotlib.pyplot as plt

                        plots_dir = os.path.join(os.path.dirname(selected_file), "plots")
                        results_dir = os.path.dirname(selected_file)
                        heatmap_fig = None
                        network_fig = None
                        prisma_fig = None
                        rob_heatmap_fig = None
                        rob_summary_fig = None

                        # Helper function to resolve plot path (handle relative paths)
                        def resolve_plot_path(path):
                            if not path:
                                return None
                            # If absolute path, use as-is
                            if os.path.isabs(path):
                                return path if os.path.exists(path) else None
                            # If relative, try multiple locations
                            # 1. Relative to results_dir (e.g., "plots/file.png")
                            full_path = os.path.join(results_dir, path)
                            if os.path.exists(full_path):
                                return full_path
                            # 2. Relative to plots_dir (if path is just filename)
                            filename = os.path.basename(path)
                            full_path = os.path.join(plots_dir, filename)
                            if os.path.exists(full_path):
                                return full_path
                            # 3. Try in plots_dir with full relative path
                            if path.startswith("plots/"):
                                full_path = os.path.join(results_dir, path)
                                if os.path.exists(full_path):
                                    return full_path
                            return None

                        # Load images as figures
                        def load_image_as_figure(img_path):
                            resolved_path = resolve_plot_path(img_path) if img_path else None
                            if resolved_path is None:
                                return None
                            try:
                                img = mpimg.imread(resolved_path)
                                fig, ax = plt.subplots(figsize=(12, 8))
                                ax.imshow(img)
                                ax.axis('off')
                                plt.tight_layout()
                                return fig
                            except Exception as e:
                                print(f"Warning: Could not load image {resolved_path}: {e}")
                                return None

                        # Try to load from saved_plots first
                        plot_files = {}
                        for plot_type in ['heatmap', 'network', 'prisma', 'rob_heatmap', 'rob_summary']:
                            if plot_type in saved_plots and 'png' in saved_plots[plot_type]:
                                plot_path = saved_plots[plot_type]['png']
                                resolved = resolve_plot_path(plot_path)
                                if resolved:
                                    plot_files[plot_type] = resolved

                        # If missing plots, search for them in plots directory
                        if os.path.exists(plots_dir):
                            # Find most recent files for missing plot types
                            all_files = sorted([f for f in os.listdir(plots_dir) if f.endswith('.png')], reverse=True)

                            for filename in all_files:
                                filepath = os.path.join(plots_dir, filename)
                                filename_lower = filename.lower()

                                if 'heatmap' in filename_lower and 'evidence' in filename_lower and 'heatmap' not in plot_files:
                                    plot_files['heatmap'] = filepath
                                elif ('network' in filename_lower or 'causal' in filename_lower) and 'network' not in plot_files:
                                    plot_files['network'] = filepath
                                elif 'prisma' in filename_lower and 'prisma' not in plot_files:
                                    plot_files['prisma'] = filepath
                                elif 'rob' in filename_lower and 'heatmap' in filename_lower and 'rob_heatmap' not in plot_files:
                                    plot_files['rob_heatmap'] = filepath
                                elif 'rob' in filename_lower and 'summary' in filename_lower and 'rob_summary' not in plot_files:
                                    plot_files['rob_summary'] = filepath

                        # Load all plots
                        heatmap_fig = load_image_as_figure(plot_files.get('heatmap'))
                        network_fig = load_image_as_figure(plot_files.get('network'))
                        prisma_fig = load_image_as_figure(plot_files.get('prisma'))
                        rob_heatmap_fig = load_image_as_figure(plot_files.get('rob_heatmap'))
                        rob_summary_fig = load_image_as_figure(plot_files.get('rob_summary'))

                        # Load RoB table
                        rob_table_df = None
                        rob_table_file = results_data.get("rob_table_file")
                        if rob_table_file:
                            # Handle relative paths
                            if not os.path.isabs(rob_table_file):
                                rob_table_file = os.path.join(results_dir, rob_table_file)
                            if os.path.exists(rob_table_file):
                                try:
                                    rob_table_df = pd.read_json(rob_table_file, orient='records')
                                except Exception as e:
                                    print(f"Warning: Could not load RoB table: {e}")

                        return (summary_text, heatmap_fig, network_fig, prisma_fig,
                               rob_heatmap_fig, rob_summary_fig, evidence_profiles,
                               rob_table_df, abstracts)

                    except Exception as e:
                        import traceback
                        error_msg = f"Error loading analysis: {str(e)}\n{traceback.format_exc()}"
                        print(error_msg)
                        return None, None, None, None, None, None, None, None, []

                # Function to load available analyses
                def auto_prepare_analysis(chemical_name, records_file, results_dir):
                    """Automatically prepare an analysis from study_records.jsonl"""
                    try:
                        import json
                        from datetime import datetime

                        import pandas as pd

                        # Load abstracts from study_records.jsonl
                        abstracts = []
                        rob_data = []
                        with open(records_file, encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    try:
                                        record = json.loads(line)
                                        metadata = record.get('metadata', {})

                                        abstract_data = {
                                            "pmid": metadata.get('pmid', 'unknown'),
                                            "title": metadata.get('title', ''),
                                            "abstract": metadata.get('abstract', ''),
                                            "authors": metadata.get('authors', ''),
                                            "journal": metadata.get('journal', ''),
                                            "year": metadata.get('year', ''),
                                            "fulltext": record.get('fulltext', '')
                                        }

                                        if abstract_data.get('title') or abstract_data.get('abstract'):
                                            abstracts.append(abstract_data)

                                        # Extract RoB data
                                        rob = record.get('risk_of_bias', {})
                                        if rob:
                                            rob_data.append({
                                                "Study #": len(rob_data) + 1,
                                                "PMID": metadata.get('pmid', 'unknown'),
                                                "Title": metadata.get('title', '')[:80] + "..." if len(metadata.get('title', '')) > 80 else metadata.get('title', ''),
                                                "Overall Judgment": rob.get('overall_judgment', 'Unknown'),
                                                "Full-text": "Yes" if record.get('fulltext') else "No"
                                            })
                                    except:
                                        continue

                        if len(abstracts) == 0:
                            return False

                        # Save abstracts for chat
                        abstracts_file = os.path.join(results_dir, "abstracts_for_chat.json")
                        with open(abstracts_file, 'w', encoding='utf-8') as f:
                            json.dump({
                                "chemical_name": chemical_name,
                                "abstracts": abstracts,
                                "saved_at": datetime.now().isoformat(),
                                "num_abstracts": len(abstracts)
                            }, f, indent=2, ensure_ascii=False)

                        # Find plot files (use relative paths)
                        plots_dir = os.path.join(results_dir, "plots")
                        saved_plots = {}
                        if os.path.exists(plots_dir):
                            plot_files = sorted(os.listdir(plots_dir), reverse=True)
                            for filename in plot_files:
                                if filename.endswith('.png'):
                                    relative_path = os.path.join("plots", filename).replace("\\", "/")
                                    filename_lower = filename.lower()
                                    if 'heatmap' in filename_lower and 'evidence' in filename_lower and 'heatmap' not in saved_plots:
                                        saved_plots['heatmap'] = {'png': relative_path}
                                    elif ('network' in filename_lower or 'causal' in filename_lower) and 'network' not in saved_plots:
                                        saved_plots['network'] = {'png': relative_path}
                                    elif 'prisma' in filename_lower and 'prisma' not in saved_plots:
                                        saved_plots['prisma'] = {'png': relative_path}
                                    elif 'rob' in filename_lower and 'heatmap' in filename_lower and 'rob_heatmap' not in saved_plots:
                                        saved_plots['rob_heatmap'] = {'png': relative_path}
                                    elif 'rob' in filename_lower and 'summary' in filename_lower and 'rob_summary' not in saved_plots:
                                        saved_plots['rob_summary'] = {'png': relative_path}

                        # Save RoB table if available
                        rob_table_file = None
                        if rob_data:
                            rob_table_file = os.path.join(results_dir, "rob_table.json")
                            try:
                                rob_df = pd.DataFrame(rob_data)
                                rob_df.to_json(rob_table_file, orient='records', indent=2)
                            except:
                                pass

                        # Generate basic summary
                        summary_text = f"""Chemical Analysis Summary
{'='*60}
Input Name: {chemical_name}
Total Papers Analyzed: {len(abstracts)}

Results saved to: {results_dir}/
"""

                        # Save analysis results
                        results_file = os.path.join(results_dir, "analysis_results.json")
                        results_data = {
                            "chemical_name": chemical_name,
                            "saved_at": datetime.now().isoformat(),
                            "num_abstracts": len(abstracts),
                            "summary_text": summary_text,
                            "evidence_profiles": "",
                            "saved_plots": saved_plots,
                            "rob_table_file": "rob_table.json" if rob_table_file and os.path.exists(rob_table_file) else None
                        }

                        with open(results_file, 'w', encoding='utf-8') as f:
                            json.dump(results_data, f, indent=2, ensure_ascii=False)

                        print(f"✅ Auto-prepared {chemical_name}: {len(abstracts)} abstracts")
                        return True
                    except Exception as e:
                        print(f"Warning: Could not auto-prepare {chemical_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        return False

                def get_available_analyses():
                    """Get list of available saved analyses - automatically prepares if needed"""
                    try:
                        import os
                        results_base = "results"
                        if not os.path.exists(results_base):
                            return []

                        analyses = []
                        for chemical_dir in os.listdir(results_base):
                            chemical_path = os.path.join(results_base, chemical_dir)
                            if not os.path.isdir(chemical_path):
                                continue

                            abstracts_file = os.path.join(chemical_path, "abstracts_for_chat.json")
                            records_file = os.path.join(chemical_path, "study_records.jsonl")

                            # Check if abstracts_for_chat.json exists
                            if os.path.exists(abstracts_file):
                                try:
                                    with open(abstracts_file, encoding='utf-8') as f:
                                        data = json.load(f)
                                        analyses.append({
                                            "label": f"{data.get('chemical_name', chemical_dir)} ({data.get('num_abstracts', 0)} abstracts)",
                                            "value": abstracts_file,
                                            "chemical": data.get('chemical_name', chemical_dir)
                                        })
                                except Exception as e:
                                    print(f"Warning: Could not load {abstracts_file}: {e}")

                            # If not found, check for study_records.jsonl and AUTO-PREPARE it
                            elif os.path.exists(records_file):
                                try:
                                    # Count abstracts first
                                    num_abstracts = 0
                                    with open(records_file, encoding='utf-8') as f:
                                        for line in f:
                                            if line.strip():
                                                num_abstracts += 1

                                    if num_abstracts > 0:
                                        chemical_name = chemical_dir.replace('_', ' ')
                                        # Auto-prepare the analysis
                                        if auto_prepare_analysis(chemical_name, records_file, chemical_path):
                                            # Now load the prepared file
                                            if os.path.exists(abstracts_file):
                                                with open(abstracts_file, encoding='utf-8') as f:
                                                    data = json.load(f)
                                                    analyses.append({
                                                        "label": f"{data.get('chemical_name', chemical_dir)} ({data.get('num_abstracts', 0)} abstracts)",
                                                        "value": abstracts_file,
                                                        "chemical": data.get('chemical_name', chemical_dir)
                                                    })
                                except Exception as e:
                                    print(f"Warning: Could not process {records_file}: {e}")
                                    import traceback
                                    traceback.print_exc()

                        # Sort by chemical name
                        analyses.sort(key=lambda x: x.get("chemical", "").lower())
                        return analyses
                    except Exception as e:
                        print(f"Error loading analyses: {e}")
                        import traceback
                        traceback.print_exc()
                        return []

                # Dropdown to load previous analyses
                with gr.Row():
                    load_analysis_dropdown = gr.Dropdown(
                        label="Load Previous Analysis",
                        choices=[],
                        value=None,
                        interactive=True,
                        info="Select a previous analysis to load ALL results (summary, plots, tables, and enable chat)"
                    )
                    load_analysis_btn = gr.Button("📂 Load All Results", variant="primary")
                    refresh_analyses_btn = gr.Button("🔄 Refresh List", variant="secondary")

                def refresh_analyses_list():
                    """Refresh the list of available analyses"""
                    analyses = get_available_analyses()
                    choices = [a["label"] for a in analyses]
                    return gr.update(choices=choices, value=None)

                def load_analysis_from_file(selected_label):
                    """Load all analysis results from selected analysis file"""
                    if not selected_label:
                        return (None, None, None, None, None, None, None, None, [],
                               gr.update(visible=False), gr.update(visible=False),
                               gr.update(visible=False), gr.update(visible=False))

                    # Load complete results
                    results = load_complete_analysis_results(selected_label)
                    if results[0] is None:  # Check if summary_text is None
                        return (None, None, None, None, None, None, None, None, [],
                               gr.update(visible=False), gr.update(visible=False),
                               gr.update(visible=False), gr.update(visible=False))

                    summary_text, heatmap_fig, network_fig, prisma_fig, \
                    rob_heatmap_fig, rob_summary_fig, evidence_profiles, \
                    rob_table_df, abstracts = results

                    # Show chatbot if abstracts available
                    has_abstracts = abstracts and len(abstracts) > 0
                    welcome_msg = []
                    if has_abstracts:
                        chemical_name = selected_label.split(' (')[0]  # Extract chemical name
                        num_abstracts = len(abstracts)
                        welcome_msg = [[None, f"✅ Loaded analysis for {chemical_name}!\n\nI can now answer questions about {num_abstracts} analyzed abstracts.\n\nAsk me about:\n- Key Characteristics (KC1-KC12)\n- Specific mechanisms or pathways\n- Evidence from particular studies\n- Overall findings\n\nExample: 'What evidence supports KC1 for {chemical_name}?'"]]

                    # Update RoB table visibility
                    has_rob_table = rob_table_df is not None and not rob_table_df.empty

                    return (
                        summary_text or "",
                        heatmap_fig,
                        network_fig,
                        prisma_fig,
                        rob_heatmap_fig,
                        rob_summary_fig,
                        evidence_profiles or "",
                        rob_table_df if has_rob_table else None,
                        abstracts,
                        gr.update(visible=has_abstracts, value=welcome_msg),
                        gr.update(visible=has_abstracts),
                        gr.update(visible=has_abstracts),
                        gr.update(visible=has_abstracts)
                    )

                # Initialize dropdown on page load and when refresh button is clicked
                def init_load_analysis_dropdown():
                    """Initialize dropdown when page loads - automatically searches and prepares"""
                    print("🔍 Auto-detecting analyses in results folder...")
                    analyses = get_available_analyses()  # This auto-prepares any missing ones
                    choices = [a["label"] for a in analyses]
                    print(f"✅ Found {len(choices)} analyses: {', '.join([a.get('chemical', '') for a in analyses])}")
                    return gr.update(choices=choices, value=None)

                def refresh_analyses_list():
                    """Refresh the list of available analyses - auto-prepares if needed"""
                    print("🔄 Refreshing analyses list...")
                    analyses = get_available_analyses()  # This auto-prepares any missing ones
                    choices = [a["label"] for a in analyses]
                    print(f"✅ Found {len(choices)} analyses")
                    return gr.update(choices=choices, value=None)

                refresh_analyses_btn.click(
                    fn=refresh_analyses_list,
                    outputs=[load_analysis_dropdown]
                )

                # Initialize on page load - automatically searches results folder
                app.load(
                    fn=init_load_analysis_dropdown,
                    outputs=[load_analysis_dropdown]
                )

                # Chatbot for asking questions about analyzed abstracts
                analysis_chatbot = gr.Chatbot(
                    label="Ask Questions About Analyzed Abstracts",
                    height=400,
                    show_label=True,
                    container=True,
                    visible=False  # Hidden until analysis completes
                )

                # State for RAG system and chat history
                analysis_rag_state = gr.State(value=None)  # Will store AgentRAGSystem instance
                analysis_chat_history = gr.State(value=[])  # Chat history

                with gr.Row():
                    analysis_msg_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., 'What evidence supports KC1 for this chemical?' or 'Which studies mention oxidative stress?'",
                        lines=2,
                        scale=4,
                        visible=False
                    )
                    analysis_send_btn = gr.Button("Send", variant="primary", scale=1, visible=False)
                    analysis_reset_btn = gr.Button("Reset", variant="secondary", scale=1, visible=False)

                load_analysis_btn.click(
                    fn=load_analysis_from_file,
                    inputs=[load_analysis_dropdown],
                    outputs=[
                        summary_output,
                        heatmap_output,
                        network_output,
                        prisma_output,
                        rob_heatmap_output,
                        rob_summary_output,
                        evidence_profiles_output,
                        rob_table_output,
                        abstracts_state,
                        analysis_chatbot,
                        analysis_msg_input,
                        analysis_send_btn,
                        analysis_reset_btn
                    ]
                ).then(
                    fn=update_rob_table_visibility,
                    inputs=[rob_table_output, abstracts_state],
                    outputs=[rob_table_output, abstract_viewer, abstracts_state]
                )

                # State to store saved plots info
                saved_plots_state = gr.State(value={})

                analyze_btn.click(
                    fn=analyze_with_progress,
                    inputs=[chemical_input, model_checkboxes, enable_rob_checkbox, enable_certainty_checkbox],
                    outputs=[
                        summary_output,
                        heatmap_output,
                        network_output,
                        prisma_output,
                        rob_heatmap_output,
                        rob_summary_output,
                        evidence_profiles_output,
                        rob_table_output,
                        abstracts_state,
                        saved_plots_state
                    ],
                    show_progress="full"
                ).then(
                    fn=update_rob_table_visibility,
                    inputs=[rob_table_output, abstracts_state],
                    outputs=[rob_table_output, abstract_viewer, abstracts_state]
                ).then(
                    fn=show_analysis_chatbot,
                    inputs=[abstracts_state],
                    outputs=[analysis_chatbot, analysis_msg_input, analysis_send_btn, analysis_reset_btn]
                ).then(
                    fn=lambda chem, abstracts, summary, evidence, rob_table, plots: save_complete_analysis_results(
                        chem, abstracts, summary, evidence, rob_table, plots
                    ) if abstracts and len(abstracts) > 0 else None,
                    inputs=[chemical_input, abstracts_state, summary_output, evidence_profiles_output, rob_table_output, saved_plots_state],
                    outputs=[],
                    show_progress=False
                )

                # Make table rows clickable - use select event
                rob_table_output.select(
                    fn=show_abstract_from_table,
                    inputs=[abstracts_state],
                    outputs=[abstract_viewer]
                )

                def initialize_analysis_rag(abstracts, model_names):
                    """Initialize RAG system with analyzed abstracts"""
                    if not abstracts or len(abstracts) == 0:
                        return None, "No abstracts available. Please run an analysis first."

                    try:
                        import os
                        import sys
                        scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
                        if scripts_path not in sys.path:
                            sys.path.insert(0, scripts_path)
                        from agent_rag_system import AgentRAGSystem

                        # Prepare abstracts for RAG system
                        rag_abstracts = []
                        for abstract in abstracts:
                            rag_abstract = {
                                "pmid": abstract.get("pmid", "unknown"),
                                "title": abstract.get("title", ""),
                                "abstract": abstract.get("abstract", "") or abstract.get("fulltext", ""),
                                "full_text": f"{abstract.get('title', '')}\n\n{abstract.get('abstract', '') or abstract.get('fulltext', '')}",
                                "year": abstract.get("year", ""),
                                "journal": abstract.get("journal", ""),
                                "authors": abstract.get("authors", [])
                            }
                            rag_abstracts.append(rag_abstract)

                        # Initialize RAG system
                        rag_system = AgentRAGSystem(top_k=5)
                        rag_system.add_abstracts(rag_abstracts)

                        # Generate embeddings (this may take a moment)
                        print(f"Generating embeddings for {len(rag_abstracts)} abstracts...")
                        rag_system.generate_embeddings()

                        return rag_system, f"RAG system initialized with {len(rag_abstracts)} abstracts"
                    except Exception as e:
                        import traceback
                        error_msg = f"Error initializing RAG: {str(e)}\n{traceback.format_exc()}"
                        print(error_msg)
                        return None, error_msg

                def chat_about_analysis(message, history, rag_system, abstracts, model_names):
                    """Handle chat messages about analyzed abstracts"""
                    if not message.strip():
                        return history, rag_system

                    # Try to load abstracts from file if abstracts_state is empty
                    if not abstracts or len(abstracts) == 0:
                        # Try to find the most recent analysis
                        try:
                            analyses = get_available_analyses()
                            if analyses:
                                # Load the most recent one
                                latest_file = analyses[-1]["value"]  # Assuming sorted by date
                                if os.path.exists(latest_file):
                                    with open(latest_file, encoding='utf-8') as f:
                                        data = json.load(f)
                                    abstracts = data.get("abstracts", [])
                                    if abstracts:
                                        print(f"✅ Loaded {len(abstracts)} abstracts from saved analysis")
                        except Exception as e:
                            print(f"Warning: Could not load saved abstracts: {e}")

                    # Initialize RAG if needed
                    if rag_system is None:
                        if not abstracts or len(abstracts) == 0:
                            history.append((message, "Error: No abstracts available. Please run an analysis first or load a previous analysis."))
                            return history, rag_system

                        rag_system, init_msg = initialize_analysis_rag(abstracts, model_names)
                        if rag_system is None:
                            history.append((message, f"Error: {init_msg}"))
                            return history, rag_system
                        # Add initialization message
                        if not any(msg[0] is None for msg in history):
                            history.append((None, f"✅ {init_msg}"))

                    try:
                        # Retrieve relevant abstracts using RAG
                        relevant_abstracts = rag_system.retrieve_relevant_abstracts(message)

                        # Format context from retrieved abstracts
                        context = rag_system.format_context(relevant_abstracts)

                        # Use the first selected model for answering
                        model_name = model_names[0] if model_names and len(model_names) > 0 else "llama3.2"

                        # Normalize model name
                        if model_name == "llama3" or model_name == "lamma3":
                            model_name = "llama3.2"

                        # Create prompt with context
                        system_prompt = """You are an expert toxicologist analyzing research abstracts about chemical hepatotoxicity.
                        
Your task is to answer questions based on the provided research abstracts. Use the retrieved abstracts as evidence for your answers.
Cite specific PMIDs when referencing studies.

Key Characteristics (KCs) of Human Hepatotoxicants:
- KC1: Reactive/Bioactivation
- KC2: Cell Death (apoptosis/necrosis)
- KC3: Proliferation/Regeneration
- KC4: Transport Disruption
- KC5: Oxidative Stress
- KC6: Immune Response
- KC7: Mitochondrial Dysfunction
- KC8: Stress Signaling
- KC9: Cholestasis
- KC10: Cytoskeleton Disruption
- KC11: Liver Fibrosis
- KC12: Metabolism Disruption

Provide clear, evidence-based answers citing the relevant abstracts."""

                        user_prompt = f"{message}\n\n{context}" if context else message

                        # Query the model
                        from langchain_core.messages import HumanMessage, SystemMessage
                        from langchain_ollama import ChatOllama

                        llm = ChatOllama(model=model_name, temperature=0.1)
                        messages = [
                            SystemMessage(content=system_prompt),
                            HumanMessage(content=user_prompt)
                        ]

                        response = llm.invoke(messages)
                        answer = response.content if hasattr(response, 'content') else str(response)

                        # Add to history
                        history.append((message, answer))

                        return history, rag_system

                    except Exception as e:
                        import traceback
                        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
                        print(error_msg)
                        history.append((message, f"Error generating response: {str(e)}"))
                        return history, rag_system

                def reset_analysis_chat(rag_system):
                    """Reset chat history"""
                    return [], rag_system

                # Chat event handlers
                analysis_send_btn.click(
                    fn=chat_about_analysis,
                    inputs=[analysis_msg_input, analysis_chatbot, analysis_rag_state, abstracts_state, model_checkboxes],
                    outputs=[analysis_chatbot, analysis_rag_state]
                ).then(
                    fn=lambda: "",
                    outputs=[analysis_msg_input]
                )

                analysis_msg_input.submit(
                    fn=chat_about_analysis,
                    inputs=[analysis_msg_input, analysis_chatbot, analysis_rag_state, abstracts_state, model_checkboxes],
                    outputs=[analysis_chatbot, analysis_rag_state]
                ).then(
                    fn=lambda: "",
                    outputs=[analysis_msg_input]
                )

                analysis_reset_btn.click(
                    fn=reset_analysis_chat,
                    inputs=[analysis_rag_state],
                    outputs=[analysis_chatbot, analysis_rag_state]
                )

                gr.Markdown("""
                ---
                ### About the Key Characteristics
                
                The 12 Key Characteristics (KCs) are biological mechanisms that indicate liver toxicity:
                - **KC1**: Reactive/Bioactivation
                - **KC2**: Cell Death (apoptosis/necrosis)
                - **KC3**: Proliferation/Regeneration
                - **KC4**: Transport Disruption
                - **KC5**: Oxidative Stress
                - **KC6**: Immune Response
                - **KC7**: Mitochondrial Dysfunction
                - **KC8**: Stress Signaling
                - **KC9**: Cholestasis
                - **KC10**: Cytoskeleton Disruption
                - **KC11**: Liver Fibrosis
                - **KC12**: Metabolism Disruption
                
                *Reference: Rusyn et al. (2021). Key Characteristics of Human Hepatotoxicants. Toxicological Sciences.*
                """)

            # Tab 2: Chat Agent
            with gr.Tab("💬 Chat Agent"):
                gr.Markdown("""
# 💬 Hepatotoxicity Expert Chat Agent

Interactive chatbot agent for querying chemicals and their Key Characteristics.
The agent uses RAG (Retrieval-Augmented Generation) to automatically download and search PubMed abstracts.

**Features:**
- Ask questions about chemicals and their hepatotoxicity mechanisms
- Automatic PubMed abstract retrieval for mentioned chemicals
- Multi-model ensemble for improved accuracy
- RAG-powered context retrieval from research literature

**Example queries:**
- "What are the key characteristics of acetaminophen?"
- "Predict the toxicity of PFOA"
- "Analyze the mechanisms of carbon tetrachloride"
""")

                # Agent state (persists across messages)
                agent_state = gr.State(value=None)

                with gr.Row():
                    with gr.Column(scale=1):
                        agent_model_dropdown = gr.Dropdown(
                            label="Select Model(s)",
                            choices=config.llm.available_models,
                            value=config.llm.default_models[0] if config.llm.default_models else "llama3.1",
                            multiselect=True,
                            info="Select one or more models for ensemble"
                        )
                        enable_rag_checkbox = gr.Checkbox(
                            label="Enable RAG (Retrieval-Augmented Generation)",
                            value=True,
                            info="Automatically download and search PubMed abstracts"
                        )
                        rag_top_k_slider = gr.Slider(
                            label="RAG Top-K",
                            minimum=1,
                            maximum=10,
                            value=5,
                            step=1,
                            info="Number of abstracts to retrieve for context"
                        )
                        reset_btn = gr.Button("🔄 Reset Chat", variant="secondary")

                chatbot = gr.Chatbot(
                    label="Chat",
                    height=500,
                    show_label=True,
                    container=True,
                    value=[[None, "👋 Welcome! I'm your Hepatotoxicity Expert Agent.\n\nAsk me about chemicals and their Key Characteristics, or request toxicity predictions.\n\nExample: 'What are the key characteristics of acetaminophen?'"]]
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Your Message",
                        placeholder="Ask about a chemical or its hepatotoxicity mechanisms...",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)

                def initialize_agent(models, use_rag, top_k):
                    """Initialize the agent with selected settings"""
                    try:
                        # Handle model selection (can be list, single value, or None)
                        if models is None or (isinstance(models, list) and len(models) == 0):
                            model_list = config.llm.default_models
                        elif isinstance(models, list):
                            model_list = models
                        else:
                            model_list = [models]

                        if not model_list:
                            return None, "Error: No models selected. Please select at least one model."

                        agent = HepatotoxicityAgent(
                            model_names=model_list,
                            use_rag=use_rag,
                            rag_top_k=int(top_k),
                            email=config.search.entrez_email,
                            api_key=None  # Can be added via config if needed
                        )
                        return agent, f"Agent initialized successfully with models: {', '.join(model_list)}"
                    except Exception as e:
                        import traceback
                        error_msg = f"Error initializing agent: {str(e)}\n{traceback.format_exc()}"
                        print(error_msg)
                        return None, error_msg

                def chat_with_agent(message, history, agent, models, use_rag, top_k):
                    """Handle chat messages"""
                    # Initialize agent if needed
                    if agent is None:
                        agent, init_msg = initialize_agent(models, use_rag, top_k)
                        if agent is None:
                            history.append((message, f"Error: {init_msg}"))
                            return history, agent

                    try:
                        # Get response from agent
                        response = agent.chat(message)
                        history.append((message, response))
                        return history, agent
                    except Exception as e:
                        import traceback
                        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
                        history.append((message, error_msg))
                        return history, agent

                def reset_chat(agent):
                    """Reset chat history"""
                    if agent is not None:
                        agent.reset_chat()
                    return [], None

                # Event handlers
                send_btn.click(
                    fn=chat_with_agent,
                    inputs=[msg_input, chatbot, agent_state, agent_model_dropdown, enable_rag_checkbox, rag_top_k_slider],
                    outputs=[chatbot, agent_state]
                ).then(
                    fn=lambda: "",  # Clear input
                    outputs=[msg_input]
                )

                msg_input.submit(
                    fn=chat_with_agent,
                    inputs=[msg_input, chatbot, agent_state, agent_model_dropdown, enable_rag_checkbox, rag_top_k_slider],
                    outputs=[chatbot, agent_state]
                ).then(
                    fn=lambda: "",  # Clear input
                    outputs=[msg_input]
                )

                reset_btn.click(
                    fn=reset_chat,
                    inputs=[agent_state],
                    outputs=[chatbot, agent_state]
                )


    return app


def find_free_port(start_port=7862, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return start_port  # Fallback


if __name__ == "__main__":
    # Show current prompt mode (already loaded at module level)
    config = get_config()
    print(f"📝 Prompt mode: {config.analysis.prompt_mode}")
    print(f"📝 Enhanced prompts: {config.analysis.enable_enhanced_prompts}")

    app = create_interface()
    port = find_free_port(7862)

    # For WSL: bind to 0.0.0.0 to allow access, but print localhost URL
    print(f"\n{'='*70}")
    print(f"Starting Gradio app on port {port}...")
    print(f"{'='*70}")
    print("\n🌐 Access the application at:")
    print(f"   • http://localhost:{port}/")
    print(f"   • http://127.0.0.1:{port}/")
    print("\n💡 Note: If using WSL, use 'localhost' or '127.0.0.1' from Windows browser")
    print("   (Do NOT use 0.0.0.0 - that's only the server bind address)")
    print(f"{'='*70}\n")

    app.launch(share=False, server_name="0.0.0.0", server_port=port)
