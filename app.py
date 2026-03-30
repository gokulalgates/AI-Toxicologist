"""
AI Toxicologist: Systematic Literature Review for Hepatotoxicity Assessment
Based on "Key Characteristics of Human Hepatotoxicants" (Rusyn et al., 2021)

Publication-Grade Systematic Review System with PRISMA compliance, 
Risk-of-Bias assessment, and provenance tracking.
"""

import gradio as gr
from gradio import Progress
import pandas as pd
import pubchempy as pcp
from Bio import Entrez
import json
import os
import time
from typing import List, Dict, Tuple, Optional, Set, Union, Any
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from io import BytesIO
import base64
import re
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import multiprocessing
import socket

from core_logic import (
    KCAnalysis,
    KC_DEFINITIONS,
    KC_NAMES,
    standardize_chemical_name,
    fetch_pubmed_abstracts,
    check_relevance,
    analyze_abstract_with_llm
)

HELP_CONTENT_TEMPLATE = """
# AI Toxicologist — Help & Documentation

---

## Getting Started

This application performs a **PRISMA-compliant systematic literature review** to assess the hepatotoxicity potential of chemicals based on the **Key Characteristics of Human Hepatotoxicants** (Rusyn et al., 2021).

---

## Setup Instructions

### 1. Install & Run Ollama

AI Toxicologist uses [Ollama](https://ollama.ai) to run large language models locally.

- Download and install Ollama from [https://ollama.ai](https://ollama.ai)
- Make sure the Ollama server is running in the background before starting the app

### 2. Pull Required Models

Open your terminal and download the models you want to use:

```
ollama pull llama3.1
ollama pull llama3.2
ollama pull mixtral
ollama pull mistral
ollama pull phi3
ollama pull gemma2
ollama pull qwen2.5
```

> **Tip:** For Multi-Reviewer Mode, use 2–3 high-end models such as `llama3.2`, `mixtral`, and `mistral`.

### 3. Start the Application

Navigate to the project directory and run:

```
python app.py
```

A Gradio web server will start. Open the link shown in your terminal (typically `http://127.0.0.1:7860/`) in your browser.

---

## Features

| Feature | Description |
|---|---|
| **PRISMA 2020 Compliance** | Flow diagrams and structured reporting |
| **Enhanced Search** | MeSH-aware PubMed queries with CAS/CID support |
| **Evidence Quotes** | Sentence-level evidence extraction from abstracts |
| **Provenance Tracking** | Complete audit trail for reproducibility |
| **Risk-of-Bias Assessment** | LLM-based OHAT/ROBINS-I assessment with visualizations |
| **Certainty Grading** | GRADE/OHAT-style certainty ratings per Key Characteristic |
| **Evidence Profile Cards** | Human-readable evidence summaries |
| **Causal Pathway Analysis** | Directed graphs showing mechanistic relationships |
| **Multi-Reviewer Mode** | Multiple models as independent reviewers with consensus voting |
| **Configurable Limits** | Adjustable literature retrieval and analysis parameters |

---

## Current Configuration

| Parameter | Value |
|---|---|
| Initial PubMed Fetch | Up to **{MAX_ABSTRACTS_INITIAL}** abstracts |
| Analysis Limit | Up to **{MAX_ABSTRACTS_ANALYZE}** relevant abstracts |
| Search Terms | Up to **{MAX_SEARCH_TERMS}** synonyms |
| Parallel Processing | **{PARALLEL_PROCESSING_STATUS}** |
| GPU Acceleration | **{GPU_ACCELERATION_STATUS}** ({GPU_COUNT} GPU(s) detected) |
| MPI Support | **{MPI_SUPPORT_STATUS}** |

---

## How It Works

The analysis pipeline follows five stages:

1. **The Librarian** — Standardizes the chemical name via PubChem and fetches abstracts from PubMed using MeSH-aware queries
2. **The Gatekeeper** — Filters abstracts for liver toxicity relevance using semantic analysis
3. **The Analyst** — Analyzes each abstract against 12 Key Characteristics with evidence quotes and causal reasoning
4. **Multi-Reviewer & Consensus** — Each selected model independently reviews all papers; results are consolidated using majority voting and ranked by consensus strength
5. **The Architect** — Generates the Evidence Matrix heatmap, Causal Pathway Network, and PRISMA flow diagram

---

## Using the Interface

### Step-by-Step

1. **Enter a Chemical Name** — Type the chemical you want to analyze (e.g., `acetaminophen`, `carbon tetrachloride`)
2. **Select Ollama Models** — Choose one or more models from the checkbox group. Selecting multiple models activates **Multi-Reviewer Mode**
3. **Enable Optional Features:**
   - *Risk-of-Bias Assessment* — Evaluates study quality for each paper
   - *Certainty Grading* — Calculates certainty of evidence per Key Characteristic
4. **Click "Analyze Chemical"** to start the systematic review
5. **Review Results** across the output tabs:
   - Analysis Summary
   - Evidence Matrix Heatmap
   - Mechanistic Pathway Network
   - PRISMA 2020 Flow Diagram
   - Risk-of-Bias Heatmap & Summary (if enabled)
   - Evidence Profile Cards
6. **Chat with Abstracts** — Use the chatbot tab to ask questions about the analyzed literature

---

## Multi-Reviewer Mode

When you select two or more models, Multi-Reviewer Mode is activated:

- **Higher reliability** through cross-model consensus
- **Inter-model agreement** statistics (Cohen's kappa)
- **Papers ranked** by consensus strength and evidence quality
- **Identifies** high-confidence vs. disputed findings

> **Note:** Multi-reviewer mode takes longer but provides significantly more reliable results.

---

## Advanced Configuration

You can adjust parameters by setting environment variables before running the app:

| Variable | Description | Default |
|---|---|---|
| `MAX_ABSTRACTS_INITIAL` | Initial PubMed fetch limit | {MAX_ABSTRACTS_INITIAL_DEFAULT} |
| `MAX_ABSTRACTS_ANALYZE` | Analysis limit after relevance filtering | {MAX_ABSTRACTS_ANALYZE_DEFAULT} |
| `LLM_TEMPERATURE` | LLM creativity/randomness (0.0 = deterministic) | {LLM_TEMPERATURE_DEFAULT} |
| `ENTREZ_EMAIL` | Email for NCBI/PubMed API access | — |
| `PROMPT_MODE` | Prompt strategy: `standard`, `enhanced`, or `liberal` | `enhanced` |

Example:

```
MAX_ABSTRACTS_ANALYZE=30 LLM_TEMPERATURE=0.2 python app.py
```

---

## Reference

Rusyn, I. et al. (2021). Key Characteristics of Human Hepatotoxicants. *Toxicological Sciences*.
"""

# Import enhanced modules
from search_enhanced import fetch_pubmed_enhanced, get_chemical_synonyms_enhanced
from fulltext_retrieval import fetch_fulltext, has_fulltext_available
from evidence_models import (
    EvidenceQuote, CausalLinkWithEvidence, StudyMetadata, 
    KCAnalysisEnhanced, StudyRecord, PRISMARecord
)
from provenance import (
    create_provenance_record, save_provenance, save_study_record, 
    save_search_log, hash_prompt
)
from plot_utils import save_all_plots
from prisma import create_prisma_flow_diagram, generate_prisma_text_summary
from risk_of_bias import (
    assess_roh_ohat, create_rob_heatmap, calculate_rob_summary_stats,
    assess_rob_with_llm
)
from rob_visualization import create_rob_heatmap_figure, create_rob_summary_figure
from certainty_grading import (
    assess_certainty_per_kc, create_certainty_summary_table
)
from evidence_profiles import create_all_evidence_profiles
from reliability import cohens_kappa, gwets_ac1, compare_llm_vs_human
from multi_reviewer import (
    consolidate_kc_analyses, rank_papers_by_consensus,
    create_consensus_evidence_matrix, create_agreement_heatmap
)
from hepatotoxicity_agent import HepatotoxicityAgent
# Load prompt mode from file BEFORE importing config (so env vars are set)
# Note: os is already imported above, no need to import again
env_file = ".prompt_mode"
if os.path.exists(env_file):
    try:
        with open(env_file, 'r') as f:
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
from exceptions import (
    SearchError, ChemicalStandardizationError, LLMError, LLMTimeoutError,
    LLMParseError, AnalysisError, ValidationError
)
from utils import retry_with_backoff, cache_result, hash_text
from gpu_utils import (
    check_gpu_available, get_gpu_count, configure_ollama_gpu,
    get_optimal_workers, setup_gpu_environment
)
# Import new enhancement modules
from confidence_scoring import analyze_with_confidence, filter_low_confidence_predictions
from rag_system import get_rag_system, add_to_example_database
from hierarchical_processing import prioritize_text_for_analysis, build_hierarchical_prompt
from active_learning import select_abstracts_for_analysis, prioritize_by_kc_coverage
from calibration import calibrate_predictions, get_calibration_model
from prompt_templates import get_prompt_for_abstract
from prompt_improvements import get_enhanced_prompt_with_synonyms, get_acetaminophen_specific_prompt, get_liberal_prompt
from causal_reasoning import enhance_causal_reasoning_prompt, validate_all_causal_links

# Optional MPI support
try:
    from mpi_support import is_mpi_available, get_mpi_rank, get_mpi_size, print_mpi_info
    MPI_ENABLED = is_mpi_available()
except (ImportError, OSError, RuntimeError, Exception) as e:
    # Catch all MPI-related errors including missing libmpi.so (OSError)
    MPI_ENABLED = False
    def print_mpi_info():
        logging.getLogger(__name__).info("MPI not available or failed to load. Running in single-process mode.")
    # Only print warning if it's not a simple ImportError (module not installed)
    if not isinstance(e, ImportError):
        logging.getLogger(__name__).warning(f"MPI support disabled: {type(e).__name__}: {e}")

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
    logger.info(f"GPU detected: {gpu_info}, Count: {gpu_count}")
    logger.info("GPU acceleration enabled for Ollama")
    # Set GPU layers for Ollama
    os.environ['OLLAMA_GPU_LAYERS'] = str(config.llm.gpu_layers)
else:
    logger.info("No GPU detected or GPU disabled, using CPU")

# Print MPI info if available
if MPI_ENABLED:
    print_mpi_info()

















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
            "Species": analysis.get("species", "Unknown"),
            "Study Type": analysis.get("study_type", "Unknown"),
            "Dose-Response": "; ".join(analysis.get("dose_response", [])),
        }
        # Add KC columns with status encoding (IMPROVEMENT #2: Multi-level evidence)
        for kc in KC_DEFINITIONS.keys():
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
            source = link.get("source", "")
            target = link.get("target", "")
            evidence = link.get("evidence", "")
            strength = link.get("strength", "MODERATE")
            
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
    except Exception:
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
        ax.text(0.5, 0.5, 'No data available for heatmap', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        return fig
    
    # Extract only KC columns for heatmap
    kc_cols = [kc for kc in KC_DEFINITIONS.keys() if kc in df.columns]
    
    if not kc_cols:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No KC columns found in data', 
               ha='center', va='center', transform=ax.transAxes, fontsize=14)
        return fig
    
    heatmap_data = df[kc_cols]
    
    # Create custom labels for y-axis (Paper number + truncated title)
    y_labels = [f"{row['Paper']}\n{row['Title']}" for _, row in df.iterrows()]
    
    # Create custom labels for x-axis (KC names)
    x_labels = [KC_NAMES[kc] for kc in kc_cols]
    
    fig, ax = plt.subplots(figsize=(14, max(8, len(df) * 0.8)))
    
    # Use diverging colormap: red for negative (REFUTED), white for neutral, green for positive (SUPPORTED)
    # Use fmt='.1f' to handle floats (0.7, 0.5) - shows 1 decimal place
    try:
        sns.heatmap(heatmap_data, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                    cbar_kws={'label': 'Evidence: 1=SUPPORTED, 0.7=ASSOCIATED, 0.5=CAUSALLY_LINKED, 0=NOT_MENTIONED, -1=REFUTED'},
                    xticklabels=x_labels, yticklabels=y_labels,
                    linewidths=0.5, linecolor='gray', ax=ax, vmin=-1, vmax=1)
    except Exception as e:
        # Fallback: create simple heatmap without annotations if there's an error
        logger.warning(f"Error creating annotated heatmap: {e}, creating simple version")
        sns.heatmap(heatmap_data, annot=False, cmap='RdYlGn', center=0,
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
    prompt_mode: Optional[str] = None,  # None means use config, otherwise use this value
    custom_prompt: Optional[str] = None,
    max_articles: Optional[int] = None,  # Maximum articles to analyze (overrides config if provided)
    progress: Optional[Progress] = None
) -> Tuple[str, plt.Figure, plt.Figure, Optional[plt.Figure], Optional[plt.Figure], Optional[plt.Figure], Optional[str], Optional[pd.DataFrame], List[Dict], Dict]:
    """
    Main analysis function that orchestrates all steps with PRISMA compliance and provenance tracking
    Returns: (summary_text, heatmap_fig, network_fig, prisma_fig, rob_heatmap_fig, rob_summary_fig, evidence_profiles_text)
    """
    # Log prompt mode being used - function parameter takes precedence over config
    # CRITICAL: UI selection (prompt_mode parameter) should override .prompt_mode file and config
    if prompt_mode is not None and str(prompt_mode).strip():
        ui_selected_mode = str(prompt_mode).strip()
        config_mode = getattr(config.analysis, 'prompt_mode', 'enhanced')
        logger.info(f"\n{'='*80}")
        logger.info(f"PROMPT MODE: UI selected '{ui_selected_mode}'")
        logger.info(f"PROMPT MODE: Config has '{config_mode}'")
        logger.info(f"PROMPT MODE: Using '{ui_selected_mode}' (UI selection OVERRIDES config)")
        logger.info(f"{'='*80}\n")
        # Use UI selection - this will be passed to analyze_abstract_with_llm
        prompt_mode = ui_selected_mode
    else:
        config_prompt_mode = getattr(config.analysis, 'prompt_mode', 'enhanced')
        logger.info(f"\nPROMPT MODE: No UI selection, using config: '{config_prompt_mode}'")
        prompt_mode = config_prompt_mode  # Use config value if not provided
    
    # Set article limits - UI selection overrides config
    # None means no limit - analyze all available articles
    if max_articles is None:
        # No limit - analyze all articles found
        max_articles_to_analyze = None  # None means no limit
        max_articles_initial = 10000  # Fetch a large number (PubMed API limit is typically 10,000)
        logger.info(f"\nARTICLE LIMITS: NO LIMIT - Will analyze ALL available articles")
        logger.info(f"ARTICLE LIMITS: Will fetch up to {max_articles_initial} articles initially (PubMed API limit)")
    elif max_articles > 0:
        max_articles_to_analyze = int(max_articles)
        # For limited analysis, fetch more initially to have enough for filtering
        # But if user wants a large number, don't over-fetch unnecessarily
        if max_articles_to_analyze <= 100:
            max_articles_initial = max(max_articles_to_analyze * 2, 100)  # Fetch 2x for small limits
        else:
            max_articles_initial = max_articles_to_analyze + 50  # Fetch slightly more for large limits
        logger.info(f"\nARTICLE LIMITS: UI selected {max_articles_to_analyze} articles to analyze")
        logger.info(f"ARTICLE LIMITS: Will fetch up to {max_articles_initial} articles initially")
    else:
        # Invalid value, use config defaults
        max_articles_to_analyze = config.search.max_abstracts_analyze
        max_articles_initial = config.search.max_abstracts_initial
        logger.info(f"\nARTICLE LIMITS: Invalid UI value, using config defaults ({max_articles_to_analyze} to analyze, {max_articles_initial} initial)")
    
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
        logger.info("\n" + "="*80)
        logger.info("AI TOXICOLOGIST: HEPATOTOXICITY ASSESSMENT")
        logger.info("="*80)
        logger.info(f"Chemical Name: {chemical_name}")
        logger.info(f"Models: {', '.join(model_names)} {'(Multi-Reviewer Mode)' if use_multi_reviewer else '(Single Reviewer)'}")
        logger.info("Settings:")
        logger.info(f"   • Risk-of-Bias Assessment: {'Enabled' if enable_rob else 'Disabled'}")
        logger.info(f"   • Certainty Grading: {'Enabled' if enable_certainty else 'Disabled'}")
        logger.info(f"   • Parallel Processing: {'Enabled' if config.llm.enable_parallel else 'Disabled'}")
        logger.info(f"   • GPU Acceleration: {'Enabled' if (gpu_info['available'] and config.llm.use_gpu) else 'Disabled'}")
        logger.info("="*80 + "\n")
        
        # Step A: The Librarian
        if progress:
            progress(0.05, desc="Step 1/6: Standardizing chemical name and searching PubMed...")
        step_start = time.time()
        standardized_name, cid, search_terms = standardize_chemical_name(chemical_name)
        
        # Store original chemical name for prompt selection (before standardization changes it)
        original_chemical_name = chemical_name.lower()
        
        # Print Step 1: Chemical Standardization results
        logger.info("STEP 1: CHEMICAL STANDARDIZATION")
        logger.info("-" * 80)
        logger.info(f"   Standardized Name: {standardized_name}")
        logger.info(f"   PubChem CID: {cid if cid else 'Not found'}")
        logger.info(f"   Search Terms: {len(search_terms)} terms")
        logger.info(f"      {', '.join(search_terms[:5])}{'...' if len(search_terms) > 5 else ''}")
        logger.info("")
        
        # Use configurable limit for initial fetch (UI selection or config)
        logger.info(f"Searching PubMed with {len(search_terms)} search terms...")
        all_abstracts, search_log = fetch_pubmed_abstracts(
            search_terms, 
            max_results=max_articles_initial  # Use UI-selected or config value
        )
        step_elapsed = time.time() - step_start
        logger.info(f"   Found {len(all_abstracts)} abstracts in {step_elapsed:.1f}s")
        logger.info("")
        if progress:
            progress(0.10, desc=f"Step 1/6: Found {len(all_abstracts)} abstracts ({step_elapsed:.1f}s)")
        
        # Update PRISMA record
        prisma_record.total_records_identified = len(all_abstracts)
        prisma_record.duplicates_removed = 0  # Single database for now
        
        # Save search log
        try:
            save_search_log(search_log, chemical_name=chemical_name)
        except Exception as e:
            logger.warning(f"Could not save search log: {e}")
        
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
        logger.info("STEP 2: RELEVANCE FILTERING")
        logger.info("-" * 80)
        logger.info(f"   Filtering {len(all_abstracts)} abstracts for liver toxicity relevance...")
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
            # Use configurable limit for analysis (UI selection or config)
            # If max_articles_to_analyze is None, there's no limit - process all
            if max_articles_to_analyze is not None and len(relevant_abstracts) >= max_articles_to_analyze:
                logger.info(f"Reached analysis limit ({max_articles_to_analyze}), stopping relevance filtering")
                break
        
        step_elapsed = time.time() - step_start
        logger.info(f"   Relevant: {len(relevant_abstracts)} abstracts")
        logger.info(f"   Excluded: {len(excluded_title_abstract)} abstracts")
        logger.info(f"   Filtering completed in {step_elapsed:.1f}s")
        logger.info("")
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
        # Only apply active learning if we have a limit and more abstracts than the limit
        if (max_articles_to_analyze is not None and 
            config.analysis.enable_active_learning and 
            len(relevant_abstracts) > max_articles_to_analyze):
            logger.info("STEP 2.5: ACTIVE LEARNING SELECTION")
            logger.info("-" * 80)
            logger.info(f"   Selecting most informative abstracts from {len(relevant_abstracts)} relevant abstracts...")
            if progress:
                progress(0.30, desc="Step 2.5/6: Active learning selection...")
            
            try:
                selected_abstracts = select_abstracts_for_analysis(
                    relevant_abstracts,
                    existing_analyses=None,  # No prior analyses for this chemical
                    max_select=max_articles_to_analyze  # Use UI-selected or config value
                )
                logger.info(f"   Selected {len(selected_abstracts)} abstracts using active learning")
                logger.info(f"      (Prioritized by uncertainty, information gain, and impact)")
                abstracts = selected_abstracts
            except Exception as e:
                logger.warning(f"Active learning failed, using all relevant abstracts: {e}")
                abstracts = relevant_abstracts[:max_articles_to_analyze]  # Use UI-selected or config value
        else:
            # No limit (max_articles_to_analyze is None) or within limit - use all relevant abstracts
            if max_articles_to_analyze is None:
                abstracts = relevant_abstracts  # No limit - use all
                logger.info(f"   No limit set - analyzing all {len(relevant_abstracts)} relevant abstracts")
            else:
                abstracts = relevant_abstracts[:max_articles_to_analyze]  # Use UI-selected or config value
        
        # Attempt full-text retrieval for abstracts (optional, but improves RoB assessment)
        logger.info("STEP 2.5: FULL-TEXT RETRIEVAL")
        logger.info("-" * 80)
        
        # Check if full-text retrieval is enabled
        if not config.search.enable_fulltext_retrieval:
            logger.info(f"   Full-text retrieval disabled in config. Using abstracts only.")
            logger.info(f"   To enable, set config.search.enable_fulltext_retrieval = True")
        else:
            logger.info(f"   Attempting full-text retrieval for {len(abstracts)} studies...")
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
                            full_text, source = fetch_fulltext(pmid)
                            if full_text:
                                # Replace abstract with full-text (keep original abstract as fallback)
                                abstract["fulltext"] = full_text
                                abstract["fulltext_source"] = source
                                fulltext_count += 1
                                logger.info(f"   Retrieved full-text for PMID {pmid} from {source}")
                    except Exception as e:
                        # Don't fail entire analysis if full-text retrieval fails
                        if config.search.skip_fulltext_on_error:
                            if config.debug:
                                logger.warning(f"Full-text retrieval failed for PMID {pmid}: {e}")
                        else:
                            raise
            
            coverage_pct = (fulltext_count / len(abstracts) * 100) if abstracts else 0
            logger.info(f"   Retrieval Results:")
            logger.info(f"      • Attempts: {retrieval_attempts}")
            logger.info(f"      • Success: {fulltext_count}/{len(abstracts)} studies")
            logger.info(f"      • Coverage: {coverage_pct:.1f}%")
            if fulltext_count == 0:
                logger.warning(f"Using abstracts only (RoB assessment may be limited)")
                logger.info(f"Note: Full-text retrieval may require institutional access or VPN.")
                logger.info(f"You can disable full-text retrieval by setting config.search.enable_fulltext_retrieval = False")
            logger.info("")
        
        # PUBLICATION QUALITY: Create experiment snapshot for reproducibility
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
            logger.info(f"   Experiment snapshot saved: {snapshot_path}")
        except Exception as e:
            if config.debug:
                logger.warning(f"Experiment snapshot creation failed: {e}")
        
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
        logger.info("STEP 3: KEY CHARACTERISTICS ANALYSIS")
        logger.info("-" * 80)
        logger.info(f"   Analyzing {len(abstracts)} abstracts against 12 Key Characteristics...")
        logger.info("")
        
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
                        logger.warning(f"Could not add to RAG database: {e}")
                
                return idx, analysis
            except Exception as e:
                logger.error(f"Error analyzing abstract {idx+1} with {model_name}: {e}")
                # Return empty analysis on error
                error_analysis = {kc: False for kc in KC_DEFINITIONS.keys()} | {f"{kc}_status": "NOT_MENTIONED" for kc in KC_DEFINITIONS.keys()} | {"reasoning": f"Error: {str(e)}", "causal_links": [], "evidence_quotes": {}, "pmid": abstract.get("pmid", "unknown"), "title": abstract.get("title", ""), "fulltext_used": False}
                return idx, error_analysis
        
        # Use parallel processing if enabled
        use_parallel = config.llm.enable_parallel and len(abstracts) > 1
        
        # Calculate optimal workers based on GPU availability
        optimal_workers = get_optimal_workers(len(abstracts), len(model_names), gpu_count)
        
        for model_idx, model_name in enumerate(model_names):
            logger.info(f"   Model {model_idx+1}/{len(model_names)}: {model_name}")
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
                        logger.info(f"      Progress: {i+1}/{len(abstracts)} abstracts analyzed...")
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
                    
                    # Pass prompt_mode from analyze_chemical (which comes from UI)
                    # This ensures UI selection takes precedence over config
                    # Debug: Log what we're passing
                    if config.debug and i == 0:
                        logger.debug(f"Passing prompt_mode={repr(prompt_mode)} to analyze_abstract_with_llm")
                    
                    analysis, prompt_hash = analyze_abstract_with_llm(
                        abstract_text,
                        abstract.get("title", ""),
                        model_name,
                        prompt_hash,
                        fulltext=fulltext,
                        chemical_name=original_chemical_name,  # Use original name for prompt selection
                        use_rag=config.analysis.enable_rag,
                        use_hierarchical=config.analysis.enable_hierarchical,
                        search_terms=search_terms,  # Pass search terms for better acetaminophen detection
                        prompt_mode=prompt_mode if prompt_mode else None,  # CRITICAL: Pass prompt_mode from UI (overrides config)
                        custom_prompt=custom_prompt  # Pass custom prompt if provided
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
                            logger.warning(f"Could not add to RAG database: {e}")
                    
                    # Add metadata to analysis
                    analysis["pmid"] = abstract.get("pmid", "unknown")
                    analysis["title"] = abstract.get("title", "")
                    analysis["fulltext_used"] = bool(abstract.get("fulltext"))
                    if analysis["fulltext_used"]:
                        analysis["fulltext_source"] = abstract.get("fulltext_source", "unknown")
                    model_analyses.append(analysis)
            
            step_elapsed = time.time() - step_start
            logger.info(f"      Completed analysis in {step_elapsed:.1f}s")
            logger.info("")
            all_model_analyses.append(model_analyses)
        
        # Consolidate multi-reviewer results if using multiple models
        if use_multi_reviewer:
            logger.info("   Consolidating multi-reviewer results...")
            if progress:
                progress(0.60, desc="Step 3.5/6: Consolidating multi-reviewer results...")
            # Use weighted consensus if configured
            consensus_method = config.analysis.consensus_method
            consolidated_analyses, agreement_stats = consolidate_kc_analyses(
                all_model_analyses, model_names, consensus_method=consensus_method
            )
            ranked_papers = rank_papers_by_consensus(consolidated_analyses, ranking_method="combined")
            logger.info(f"      Consensus analysis complete")
            logger.info("")
            
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
            logger.info("   Applying confidence scoring and calibration...")
            try:
                # Calibrate predictions
                calibration_model = get_calibration_model()
                kc_analyses = calibrate_predictions(kc_analyses, calibration_model)
                logger.info(f"      Calibrated {len(kc_analyses)} analyses")
            except Exception as e:
                logger.warning(f"Calibration failed: {e}")
        
        # Filter low-confidence predictions if configured
        if config.analysis.enable_confidence_scoring and config.analysis.filter_low_confidence:
            try:
                high_conf, low_conf = filter_low_confidence_predictions(
                    kc_analyses,
                    confidence_threshold=config.analysis.confidence_threshold
                )
                logger.info(f"      Confidence filtering: {len(high_conf)} high-confidence, {len(low_conf)} low-confidence")
                # Optionally use only high-confidence, or flag low-confidence
                if config.analysis.use_only_high_confidence:
                    kc_analyses = high_conf
                    abstracts = [ab for i, ab in enumerate(abstracts) if i < len(high_conf)]
            except Exception as e:
                logger.warning(f"Confidence filtering failed: {e}")
        
        # Create study metadata and Risk-of-Bias assessments
        logger.info("STEP 4: RISK-OF-BIAS ASSESSMENT")
        logger.info("-" * 80)
        if enable_rob:
            logger.info(f"   Assessing risk-of-bias for {len(abstracts)} studies...")
        else:
            logger.info(f"   Risk-of-Bias assessment disabled")
        logger.info("")
        
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
                        logger.info(f"      Progress: {i+1}/{len(abstracts)} studies assessed...")
                    if progress:
                        progress(0.65 + 0.10 * (i / len(abstracts)), 
                                desc=f"Step 4/6: Assessing Risk-of-Bias {i+1}/{len(abstracts)}...")
                    
                    # Use full-text if available and substantial, otherwise abstract
                    fulltext = abstract.get("fulltext", "")
                    abstract_text_only = abstract.get("abstract", "")
                    
                    # Check if full-text is actually available and substantial (not just empty string)
                    # Full-text should be significantly longer than abstract to be considered valid
                    if fulltext and len(fulltext.strip()) > len(abstract_text_only) * 1.5:
                        fulltext_available = True
                        text_for_rob = fulltext
                        logger.info(f"      Using full-text for RoB assessment (PMID {abstract.get('pmid', 'unknown')}): {len(fulltext)} chars")
                    else:
                        fulltext_available = False
                        text_for_rob = abstract_text_only
                        if fulltext:
                            logger.warning(f"Full-text exists but too short ({len(fulltext)} chars), using abstract instead for RoB")
                    
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
                        instrument="OHAT",
                        fulltext_available=fulltext_available
                    )
                    rob_assessments.append(rob_assessment)
                except Exception as e:
                    logger.warning(f"RoB assessment failed for study {i+1}: {e}")
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
                logger.warning(f"Could not save study record: {e}")
            
            study_records.append(study_record)
        
        if enable_rob and rob_assessments:
            # Print overall RoB judgments summary
            rob_summary = {}
            for rob in rob_assessments:
                overall = rob.overall_judgment if hasattr(rob, 'overall_judgment') else "Unknown"
                rob_summary[overall] = rob_summary.get(overall, 0) + 1
            logger.info(f"   Risk-of-Bias assessment complete:")
            for judgment, count in rob_summary.items():
                logger.info(f"      {judgment}: {count} studies")
            logger.info("")
        
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
            logger.warning(f"Could not save provenance: {e}")
        
        # Step C: The Architect
        logger.info("STEP 5: VISUALIZATIONS")
        logger.info("-" * 80)
        if progress:
            progress(0.80, desc="Step 5/6: Generating visualizations (Evidence Matrix, Network Graph, PRISMA)...")
        step_start = time.time()
        
        logger.info("   Creating visualizations...")
        logger.info("      Evidence Matrix Heatmap...")
        try:
            evidence_matrix = create_evidence_matrix(abstracts, kc_analyses)
            logger.info(f"      Evidence matrix created: {len(evidence_matrix)} papers × {len([c for c in evidence_matrix.columns if c in KC_DEFINITIONS.keys()])} KCs")
            heatmap_fig = create_heatmap(evidence_matrix)
            logger.info("      Heatmap figure created")
        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            import traceback
            traceback.print_exc()
            # Create empty figure as fallback
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f'Error creating heatmap:\n{str(e)}', 
                   ha='center', va='center', transform=ax.transAxes)
            heatmap_fig = fig
        # Simplified: Skip network, PRISMA, and RoB visualizations
        network_fig = None
        prisma_fig = None
        rob_heatmap_fig = None
        rob_summary_fig = None
        
        step_elapsed = time.time() - step_start
        logger.info(f"   All visualizations created in {step_elapsed:.1f}s")
        logger.info("")
        
        # Simplified: Skip certainty grading
        certainty_assessments = []
        evidence_profiles_text = None
        if False:  # Disabled for simplified version
            try:
                logger.info(f"   Assessing certainty of evidence for 12 Key Characteristics...")
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
                        logger.info(f"      Progress: {idx+1}/12 KCs assessed...")
                
                # Create evidence profile cards
                logger.info("      Generating evidence profile cards...")
                if progress:
                    progress(0.95, desc="Step 6/6: Generating evidence profile cards...")
                evidence_profiles_text = create_all_evidence_profiles(
                    kc_analyses, certainty_assessments, KC_NAMES
                )
                logger.info(f"   Certainty grading complete for all 12 KCs")
                logger.info("")
            except Exception as e:
                logger.warning(f"Certainty grading failed: {e}")
                evidence_profiles_text = "Certainty assessment could not be completed."
                logger.info("")
        else:
            logger.info(f"   Certainty grading disabled")
            logger.info("")
        
        step_elapsed = time.time() - step_start
        total_elapsed = time.time() - start_time
        
        # ============================================================================
        # COMPLETION SUMMARY
        # ============================================================================
        logger.info("="*80)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*80)
        
        # Calculate summary statistics
        total_papers = len(abstracts)
        kc_supported = {kc: sum(1 for analysis in kc_analyses 
                                if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") in ["SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"]) 
                        for kc in KC_DEFINITIONS.keys()}
        total_causal_links = sum(len(analysis.get("causal_links", [])) for analysis in kc_analyses)
        total_quotes = sum(len(quotes) for analysis in kc_analyses 
                          for quotes in analysis.get("evidence_quotes", {}).values())
        
        logger.info(f"Summary Statistics:")
        logger.info(f"   Papers Analyzed: {total_papers}")
        logger.info(f"   Key Characteristics Supported: {sum(kc_supported.values())} total instances")
        logger.info(f"   Causal Links Identified: {total_causal_links}")
        logger.info(f"   Evidence Quotes Extracted: {total_quotes}")
        if enable_rob and rob_assessments:
            rob_stats = calculate_rob_summary_stats(rob_assessments)
            logger.info(f"   Risk-of-Bias Assessments: {len(rob_assessments)} studies")
        if enable_certainty and certainty_assessments:
            logger.info(f"   Certainty Assessments: {len(certainty_assessments)} KCs")
        logger.info(f"Total Processing Time: {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)")
        logger.info(f"Results Location: results/{chemical_name.replace(' ', '_')}/")
        logger.info("="*80 + "\n")
        
        if progress:
            progress(1.0, desc=f"Complete! Total time: {total_elapsed:.1f}s")
        
        # Create summary text with enhanced statistics
        # (total_papers, kc_supported, total_causal_links, total_quotes already calculated above)
        kc_refuted = {kc: sum(1 for analysis in kc_analyses 
                              if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "REFUTED") 
                      for kc in KC_DEFINITIONS.keys()}
        
        # Show search terms used
        search_terms_display = ", ".join(search_terms[:3])
        if len(search_terms) > 3:
            search_terms_display += f" (+{len(search_terms)-3} more)"
        
        # Simplified summary
        models_display = ", ".join(model_names) if len(model_names) <= 3 else f"{', '.join(model_names[:2])} (+{len(model_names)-2} more)"
        summary = f"""# Analysis Results for {chemical_name.title()}

**Total Papers Analyzed:** {total_papers}

## Key Characteristics Support

"""
        # Add KC counts
        for kc in KC_DEFINITIONS.keys():
            count = kc_supported.get(kc, 0)
            pct = (count / total_papers * 100) if total_papers > 0 else 0
            summary += f"- **{KC_NAMES[kc]} ({kc})**: {count}/{total_papers} papers ({pct:.1f}%)\n"
        
        summary += f"\n---\n\n*Click on a paper in the table below to see evidence for each KC.*"
        
        # Add full-text retrieval summary
        if fulltext_count > 0:
            summary += f"\n\n📄 Full-text retrieval: {fulltext_count}/{len(abstracts)} studies had full-text available"
            summary += f"\n   (Full-text improves risk-of-bias assessment quality)"
        
        # Save all plots to disk
        saved_plots_info = {}
        try:
            logger.info("Saving plots to disk...")
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
            logger.warning(f"Could not save plots: {e}")
        
        summary += f"\n\nResults saved to: results/{chemical_name.replace(' ', '_')}/"
        
        # Create simple papers table showing supported KCs
        papers_table_df = None
        if abstracts and kc_analyses:
            papers_data = []
            for i, (abstract, analysis) in enumerate(zip(abstracts, kc_analyses)):
                supported_kcs = []
                for kc in KC_DEFINITIONS.keys():
                    status = analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED")
                    if status == "SUPPORTED":
                        supported_kcs.append(kc)
                
                papers_data.append({
                    "Paper #": i + 1,
                    "Title": abstract.get("title", ""),
                    "PMID": abstract.get("pmid", "unknown"),
                    "Supported KCs": ", ".join(supported_kcs) if supported_kcs else "None"
                })
            papers_table_df = pd.DataFrame(papers_data)
        
        # Store saved_plots_info in a way that can be accessed later
        # We'll pass it through a state variable
        # Convert rob_assessments to list of dicts for UI compatibility
        rob_assessments_for_ui = []
        if rob_assessments:
            for rob in rob_assessments:
                if hasattr(rob, 'model_dump'):
                    rob_assessments_for_ui.append(rob.model_dump())
                elif isinstance(rob, dict):
                    rob_assessments_for_ui.append(rob)
                else:
                    rob_assessments_for_ui.append({"overall_judgment": "Unknown"})
        
        return summary, heatmap_fig, network_fig, prisma_fig, rob_heatmap_fig, rob_summary_fig, evidence_profiles_text, papers_table_df, abstracts, kc_analyses, saved_plots_info, rob_assessments_for_ui
    
    except Exception as e:
        models_str = ", ".join(model_names) if model_names else "selected model"
        error_msg = f"Error during analysis: {str(e)}\n\nPlease ensure Ollama is running and the model(s) are installed.\n\nTo install Ollama: https://ollama.ai\nTo pull models: ollama pull {models_str}"
        return error_msg, None, None, None, None, None, None, None, [], [], {}, []


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
                gr.Markdown(f"""
        # 🔬 AI Toxicologist: Publication-Grade Hepatotoxicity Assessment
        
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
                            choices=[
                                "llama3.1",
                                "llama3.2",
                                "mistral",
                                "mixtral",
                                "phi3",
                                "gemma2",
                                "qwen2.5",
                                "deepseek-r1:70b",
                                "deepseek-v3"
                            ],
                            value=["llama3.2"],
                            info="Select 1+ models. Multiple models = Multi-Reviewer mode with consensus"
                        )
                
                analyze_btn = gr.Button("🔍 Analyze Chemical", variant="primary", size="lg")
                
                # Prompt Configuration Section
                with gr.Accordion("⚙️ Prompt Configuration (Advanced)", open=False):
                    prompt_type_dropdown = gr.Dropdown(
                        label="Prompt Type",
                        choices=[
                            "enhanced",
                            "liberal", 
                            "acetaminophen-specific",
                            "standard",
                            "custom"
                        ],
                        value="enhanced",
                        info="Select the prompt template to use. 'Enhanced' includes synonym recognition. 'Liberal' is more permissive. 'Custom' allows editing."
                    )
                    
                    custom_prompt_textbox = gr.Textbox(
                        label="Custom Prompt (only used if Prompt Type = 'custom')",
                        placeholder="Enter your custom prompt here. Use {kc_definitions} and {format_instructions} as placeholders.",
                        lines=20,
                        visible=False,
                        value=""
                    )
                    
                    def update_custom_prompt_visibility(prompt_type):
                        """Show/hide custom prompt textbox based on selection"""
                        return gr.update(visible=(prompt_type == "custom"))
                    
                    prompt_type_dropdown.change(
                        fn=update_custom_prompt_visibility,
                        inputs=[prompt_type_dropdown],
                        outputs=[custom_prompt_textbox]
                    )
                    
                    # Load default prompts as examples
                    def load_default_prompt(prompt_type):
                        """Load default prompt text for the selected type and switch to custom mode"""
                        try:
                            from prompt_improvements import (
                                get_enhanced_prompt_with_synonyms,
                                get_liberal_prompt,
                                get_acetaminophen_specific_prompt
                            )
                            from prompt_templates import get_standard_prompt
                            
                            # Build KC definitions (placeholder)
                            kc_definitions_text = "\n".join([f"{kc}: {definition}" for kc, definition in KC_DEFINITIONS.items()])
                            format_instructions_placeholder = "{format_instructions}"
                            
                            if prompt_type == "enhanced":
                                prompt_text = get_enhanced_prompt_with_synonyms(kc_definitions_text, format_instructions_placeholder)
                            elif prompt_type == "liberal":
                                prompt_text = get_liberal_prompt(kc_definitions_text, format_instructions_placeholder)
                            elif prompt_type == "acetaminophen-specific":
                                prompt_text = get_acetaminophen_specific_prompt(kc_definitions_text, format_instructions_placeholder)
                            elif prompt_type == "standard":
                                prompt_text = get_standard_prompt(kc_definitions_text, format_instructions_placeholder)
                            else:
                                prompt_text = ""
                            
                            # Return both the prompt text and update to show the textbox
                            return prompt_text, gr.update(value="custom"), gr.update(visible=True)
                        except Exception as e:
                            error_msg = f"Error loading prompt: {str(e)}"
                            return error_msg, gr.update(), gr.update(visible=True)
                    
                    load_prompt_btn = gr.Button("📋 Load Default Prompt Template (for editing)", variant="secondary")
                    load_prompt_btn.click(
                        fn=load_default_prompt,
                        inputs=[prompt_type_dropdown],
                        outputs=[custom_prompt_textbox, prompt_type_dropdown, custom_prompt_textbox]
                    )
                    
                    gr.Markdown("""
                    **💡 Tips:**
                    - Select a prompt type and click "Load Default Prompt Template" to view/edit it
                    - Use `{kc_definitions}` and `{format_instructions}` as placeholders in custom prompts
                    - The prompt will be automatically populated with KC definitions and JSON schema when used
                    """)
                
                # Article Limit Configuration
                with gr.Accordion("📊 Article Limit Configuration", open=False):
                    max_articles_dropdown = gr.Dropdown(
                        choices=["15", "25", "50", "75", "100", "All", "Custom"],
                        label="Maximum Articles to Analyze",
                        value="15",
                        info="Select the maximum number of articles to analyze. Choose 'All' to analyze all available articles, or 'Custom' to specify your own number."
                    )
                    
                    max_articles_custom_input = gr.Number(
                        label="Custom Article Limit",
                        value=15,
                        minimum=1,
                        maximum=1000,
                        step=1,
                        visible=False,
                        info="Enter the number of articles you want to analyze (1-1000)"
                    )
                    
                    def update_custom_input_visibility(selection):
                        """Show/hide custom input based on dropdown selection"""
                        return gr.update(visible=(selection == "Custom"))
                    
                    max_articles_dropdown.change(
                        fn=update_custom_input_visibility,
                        inputs=[max_articles_dropdown],
                        outputs=[max_articles_custom_input]
                    )
                    
                    gr.Markdown("""
                    **💡 Options:**
                    - **15-100 articles**: Quick presets for common use cases
                    - **All**: Analyze ALL available articles found in PubMed (no limit)
                    - **Custom**: Specify your own number (1-1000)
                    
                    **Note:** The system will analyze all relevant articles up to your selected limit. 
                    For 'All', it will analyze every article found in the PubMed search.
                    """)
                
                # KC Support Threshold Configuration
                with gr.Accordion("🎯 KC Support Threshold", open=False):
                    support_threshold_min_papers = gr.Number(
                        label="Minimum Papers Required",
                        value=2,
                        minimum=1,
                        maximum=50,
                        step=1,
                        info="A KC must be supported by at least this many papers to be marked as 'Supported'"
                    )
                    
                    support_threshold_min_percentage = gr.Number(
                        label="Minimum Percentage Required (%)",
                        value=5.0,
                        minimum=0.1,
                        maximum=100.0,
                        step=0.5,
                        info="A KC must be supported by at least this percentage of papers to be marked as 'Supported'"
                    )
                    
                    gr.Markdown("""
                    **💡 Threshold Logic:**
                    A KC is marked as "✅ Supported" only if **BOTH** conditions are met:
                    - Supported by **at least** the minimum number of papers (absolute count)
                    - **AND** supported by **at least** the minimum percentage of papers
                    
                    **Example:** With 66 papers, a KC needs:
                    - At least 2 papers supporting it (absolute minimum)
                    - **AND** at least 5% (≈3.3 papers, so effectively 4+ papers)
                    
                    This prevents marking KCs as "Supported" based on isolated findings from just 1-2 papers.
                    """)
                
                gr.Markdown("---")
                
                with gr.Row():
                    summary_output = gr.Markdown(
                        label="Analysis Summary"
                    )
                
                with gr.Row():
                    kc_summary_table = gr.Dataframe(
                        label="KC Summary: Support Status",
                        headers=["KC", "Name", "Status", "Papers Supporting", "Percentage"],
                        interactive=False,
                        wrap=True
                    )
                
                with gr.Row():
                    heatmap_output = gr.Plot(label="Evidence Matrix: Which Papers Support Which KCs")
                
                with gr.Row():
                    papers_table_output = gr.Dataframe(
                        label="Papers Analyzed (Click a row to see evidence for each KC)",
                        interactive=True,
                        wrap=True
                    )
                
                with gr.Row():
                    evidence_viewer = gr.Markdown(
                        label="Evidence for Selected Paper",
                        value="Click on a paper in the table above to see evidence for each KC."
                    )
                
                gr.Markdown("---")
                gr.Markdown("## 💬 Ask Questions About the Analyzed Abstracts")
                gr.Markdown("Use the chatbot below to ask questions about the analyzed abstracts. The chatbot uses RAG (Retrieval-Augmented Generation) to find relevant information.")
                
                # Chatbot for asking questions about analyzed abstracts
                analysis_chatbot = gr.Chatbot(
                    label="Chat About Analyzed Abstracts",
                    height=400,
                    show_label=True,
                    container=True,
                    visible=False
                )
                
                # State for RAG system and chat history
                analysis_rag_state = gr.State(value=None)  # Will store AgentRAGSystem instance
                analysis_chat_history = gr.State(value=[])  # Chat history
                
                with gr.Row():
                    analysis_msg_input = gr.Textbox(
                        label="Your Question",
                        placeholder="e.g., 'What evidence supports KC5 (oxidative stress) for this chemical?' or 'Which studies mention mitochondrial dysfunction?'",
                        lines=2,
                        scale=4,
                        visible=False
                    )
                    analysis_send_btn = gr.Button("Send", variant="primary", scale=1, visible=False)
                    analysis_reset_btn = gr.Button("Reset", variant="secondary", scale=1, visible=False)
                
                def analyze_with_progress(chem, models, prompt_type, custom_prompt, max_articles_selection, max_articles_custom, support_threshold_min_papers, support_threshold_min_percentage, progress=gr.Progress()):
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
                    
                    # Determine max_articles from UI selection
                    if max_articles_selection == "All":
                        max_articles = None  # None means no limit - analyze all
                        logger.info(f"\n{'='*80}")
                        logger.info(f"ARTICLE LIMIT: ALL articles will be analyzed (no limit)")
                    elif max_articles_selection == "Custom":
                        # Use custom input value
                        if max_articles_custom is not None:
                            max_articles = int(max_articles_custom)
                            if max_articles < 1:
                                max_articles = 15  # Fallback to default
                            logger.info(f"\n{'='*80}")
                            logger.info(f"ARTICLE LIMIT: Custom value = {max_articles} articles")
                        else:
                            max_articles = 15  # Default fallback
                            logger.info(f"\n{'='*80}")
                            logger.info(f"ARTICLE LIMIT: Custom input empty, using default = {max_articles} articles")
                    else:
                        # Preset value (15, 25, 50, 75, 100)
                        try:
                            max_articles = int(max_articles_selection)
                        except (ValueError, TypeError):
                            max_articles = 15  # Default fallback
                        logger.info(f"\n{'='*80}")
                        logger.info(f"ARTICLE LIMIT: Preset value = {max_articles} articles")
                    
                    logger.info(f"{'='*80}\n")
                    
                    # Simplified: disable RoB and certainty
                    # Pass prompt configuration
                    logger.info(f"\n{'='*80}")
                    logger.info(f"UI PROMPT SELECTION: '{prompt_type}'")
                    logger.info(f"MAX ARTICLES TO ANALYZE: {max_articles if max_articles else 'ALL (no limit)'}")
                    logger.info(f"Custom prompt provided: {bool(custom_prompt and prompt_type == 'custom')}")
                    logger.info(f"Config prompt_mode: '{getattr(config.analysis, 'prompt_mode', 'enhanced')}'")
                    logger.info(f"{'='*80}\n")
                    
                    # Unpack all return values but only return what we need
                    # Ensure prompt_type is properly passed (handle empty string case)
                    effective_prompt_mode = prompt_type if prompt_type and str(prompt_type).strip() else None
                    if effective_prompt_mode:
                        logger.info(f"   UI selected prompt_mode: '{effective_prompt_mode}'")
                    
                    summary, heatmap_fig, network_fig, prisma_fig, rob_heatmap_fig, rob_summary_fig, evidence_profiles_text, papers_table_df, abstracts, kc_analyses, saved_plots_info, rob_assessments = analyze_chemical(
                        chem, models, enable_rob=False, enable_certainty=False, 
                        prompt_mode=effective_prompt_mode,  # UI selection - this should override config
                        custom_prompt=custom_prompt if prompt_type == "custom" else None,
                        max_articles=max_articles,  # Pass UI selection for article limit (None = no limit)
                        progress=progress
                    )
                    
                    # Create KC summary table with threshold checking
                    kc_summary_data = []
                    if abstracts and kc_analyses:
                        total_papers = len(abstracts)
                        
                        # Get threshold values (with defaults)
                        min_papers = int(support_threshold_min_papers) if support_threshold_min_papers is not None and support_threshold_min_papers > 0 else 2
                        min_percentage = float(support_threshold_min_percentage) if support_threshold_min_percentage is not None and support_threshold_min_percentage > 0 else 5.0
                        
                        logger.info(f"\nKC Support Thresholds:")
                        logger.info(f"   Minimum papers: {min_papers}")
                        logger.info(f"   Minimum percentage: {min_percentage}%")
                        logger.info(f"   Total papers analyzed: {total_papers}")
                        
                        for i in range(1, 13):
                            kc_key = f"KC{i}"
                            kc_name = KC_NAMES[kc_key]
                            
                            # Count papers supporting this KC
                            supported_count = sum(1 for analysis in kc_analyses 
                                                 if analysis.get(f"kc{i}_status", "NOT_MENTIONED") == "SUPPORTED")
                            percentage = (supported_count / total_papers * 100) if total_papers > 0 else 0
                            
                            # Determine status based on BOTH thresholds
                            # A KC is "Supported" only if it meets BOTH:
                            # 1. At least min_papers papers support it (absolute count)
                            # 2. At least min_percentage% of papers support it (relative percentage)
                            meets_min_papers = supported_count >= min_papers
                            meets_min_percentage = percentage >= min_percentage
                            
                            if meets_min_papers and meets_min_percentage:
                                status = "✅ Supported"
                            else:
                                status = "❌ Not Supported"
                                # Add note if close to threshold
                                if supported_count > 0:
                                    if not meets_min_papers:
                                        status += f" (needs {min_papers - supported_count} more paper(s))"
                                    elif not meets_min_percentage:
                                        status += f" (needs {min_percentage - percentage:.1f}% more)"
                            
                            kc_summary_data.append({
                                "KC": kc_key,
                                "Name": kc_name,
                                "Status": status,
                                "Papers Supporting": f"{supported_count}/{total_papers}",
                                "Percentage": f"{percentage:.1f}%"
                            })
                    
                    kc_summary_df = pd.DataFrame(kc_summary_data) if kc_summary_data else pd.DataFrame()
                    
                    # Return only what the UI needs (including rob_assessments)
                    return summary, kc_summary_df, heatmap_fig, papers_table_df, abstracts, kc_analyses, rob_assessments
                
                def initialize_analysis_rag(abstracts, model_names):
                    """Initialize RAG system with analyzed abstracts"""
                    if not abstracts or len(abstracts) == 0:
                        return None, "No abstracts available. Please run an analysis first."
                    
                    try:
                        # Try importing AgentRAGSystem from scripts
                        try:
                            from scripts.agent_rag_system import AgentRAGSystem
                        except ImportError:
                            # Fallback: try importing from current directory
                            import sys
                            import os
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
                        logger.info(f"Generating embeddings for {len(rag_abstracts)} abstracts...")
                        rag_system.generate_embeddings()
                        
                        return rag_system, f"RAG system initialized with {len(rag_abstracts)} abstracts"
                    except Exception as e:
                        import traceback
                        error_msg = f"Error initializing RAG: {str(e)}\n{traceback.format_exc()}"
                        logger.error(error_msg)
                        # Return a simple RAG system that uses keyword search as fallback
                        return None, f"RAG initialization failed: {str(e)}. Using simple keyword search."
                
                def chat_about_analysis(message, history, rag_system, abstracts, model_names):
                    """Handle chat messages about analyzed abstracts using RAG"""
                    if not message.strip():
                        return history, rag_system
                    
                    # Initialize RAG if needed
                    if rag_system is None:
                        if not abstracts or len(abstracts) == 0:
                            history.append((message, "Error: No abstracts available. Please run an analysis first."))
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
                        if rag_system:
                            relevant_abstracts = rag_system.retrieve_relevant_abstracts(message)
                        else:
                            # Fallback: simple keyword search
                            relevant_abstracts = []
                            query_lower = message.lower()
                            query_words = set(query_lower.split())
                            for abstract in abstracts:
                                abstract_text_lower = (abstract.get("abstract", "") + " " + abstract.get("title", "")).lower()
                                if any(word in abstract_text_lower for word in query_words if len(word) > 3):
                                    relevant_abstracts.append({
                                        "title": abstract.get("title", ""),
                                        "abstract": abstract.get("abstract", ""),
                                        "pmid": abstract.get("pmid", "unknown")
                                    })
                            relevant_abstracts = relevant_abstracts[:3]  # Top 3
                        
                        # Format context from retrieved abstracts
                        context_parts = []
                        if relevant_abstracts:
                            context_parts.append("**Relevant Abstracts:**\n")
                            for i, abs_data in enumerate(relevant_abstracts[:3], 1):  # Top 3
                                title = abs_data.get("title", "No title")
                                abstract_text = abs_data.get("abstract", "")[:300] + "..." if len(abs_data.get("abstract", "")) > 300 else abs_data.get("abstract", "")
                                pmid = abs_data.get("pmid", "unknown")
                                context_parts.append(f"{i}. **{title}** (PMID: {pmid})\n   {abstract_text}\n")
                            context = "\n".join(context_parts)
                        else:
                            context = "No relevant abstracts found."
                        
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
                        from langchain_ollama import ChatOllama
                        from langchain_core.messages import SystemMessage, HumanMessage
                        
                        llm = ChatOllama(
                            model=model_name, 
                            temperature=0.1,
                            timeout=config.search.llm_timeout  # Add timeout to prevent hanging
                        )
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
                        logger.error(error_msg)
                        history.append((message, f"Error generating response: {str(e)}"))
                        return history, rag_system
                
                def reset_analysis_chat(rag_system):
                    """Reset chat history"""
                    return [], rag_system
                
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
                
                # Store abstracts, kc_analyses, and rob_assessments for interactive viewing
                abstracts_state = gr.State(value=[])
                kc_analyses_state = gr.State(value=[])
                rob_assessments_state = gr.State(value=[])
                
                def show_paper_evidence(evt: gr.SelectData, abstracts_list, kc_analyses_list, rob_assessments_list=None):
                    """Show evidence for each KC when a paper is clicked"""
                    try:
                        if evt is None or not abstracts_list or not kc_analyses_list:
                            return "Please select a paper from the table above."
                        
                        # Get row index
                        row_idx = None
                        if hasattr(evt, 'index'):
                            if isinstance(evt.index, (list, tuple)) and len(evt.index) > 0:
                                row_idx = evt.index[0]
                            elif isinstance(evt.index, int):
                                row_idx = evt.index
                        
                        if row_idx is None or row_idx >= len(abstracts_list):
                            return "Invalid selection."
                        
                        abstract = abstracts_list[row_idx]
                        analysis = kc_analyses_list[row_idx]
                        
                        # Get risk of bias assessment if available
                        rob_assessment = None
                        if rob_assessments_list and len(rob_assessments_list) > 0 and row_idx < len(rob_assessments_list):
                            rob_assessment = rob_assessments_list[row_idx]
                        # Also check if stored in abstract or analysis
                        if not rob_assessment:
                            if "risk_of_bias" in abstract:
                                rob_assessment = abstract.get("risk_of_bias")
                            elif "risk_of_bias" in analysis:
                                rob_assessment = analysis.get("risk_of_bias")
                        
                        title = abstract.get("title", "No title")
                        pmid = abstract.get("pmid", "unknown")
                        abstract_text = abstract.get("abstract", "No abstract available")
                        fulltext_used = analysis.get("fulltext_used", False) or bool(abstract.get("fulltext"))
                        fulltext_source = abstract.get("fulltext_source", analysis.get("fulltext_source", "unknown"))
                        year = abstract.get("year", "")
                        authors = abstract.get("authors", "")
                        journal = abstract.get("journal", "")
                        
                        # Build evidence display
                        output_lines = [f"# {title}\n"]
                        output_lines.append(f"**PMID:** {pmid}")
                        if year:
                            output_lines.append(f" | **Year:** {year}")
                        if journal:
                            output_lines.append(f" | **Journal:** {journal}")
                        output_lines.append("\n")
                        if authors:
                            output_lines.append(f"**Authors:** {authors}\n")
                        
                        # Full-text usage indicator
                        if fulltext_used:
                            output_lines.append(f"📄 **Full-text used:** Yes (Source: {fulltext_source})\n")
                        else:
                            output_lines.append(f"📄 **Full-text used:** No (Abstract only)\n")
                        
                        output_lines.append(f"\n**Abstract:**\n{abstract_text}\n\n")
                        output_lines.append("---\n")
                        
                        # Risk of Bias Assessment Section
                        if rob_assessment:
                            output_lines.append("## ⚖️ Risk-of-Bias Assessment\n")
                            try:
                                # Handle both RiskOfBiasAssessment object and dict
                                if hasattr(rob_assessment, 'overall_judgment'):
                                    overall = rob_assessment.overall_judgment
                                    domains = rob_assessment.domains
                                    instrument = rob_assessment.instrument
                                    rob_fulltext_used = getattr(rob_assessment, 'fulltext_used', False)
                                elif isinstance(rob_assessment, dict):
                                    overall = rob_assessment.get("overall_judgment", "Unknown")
                                    domains = rob_assessment.get("domains", [])
                                    instrument = rob_assessment.get("instrument", "OHAT")
                                    rob_fulltext_used = rob_assessment.get("fulltext_used", False)
                                else:
                                    overall = "Unknown"
                                    domains = []
                                    instrument = "Unknown"
                                    rob_fulltext_used = False
                                
                                # Overall judgment with color coding
                                judgment_emoji = {
                                    "Low": "🟢",
                                    "Some concerns": "🟡",
                                    "High": "🟠",
                                    "Critical": "🔴",
                                    "Insufficient information": "⚪"
                                }.get(overall, "⚪")
                                
                                output_lines.append(f"**Overall Judgment:** {judgment_emoji} **{overall}**\n")
                                output_lines.append(f"**Instrument:** {instrument}\n")
                                if rob_fulltext_used:
                                    output_lines.append(f"**Assessment based on:** Full-text\n")
                                else:
                                    output_lines.append(f"**Assessment based on:** Abstract only\n")
                                output_lines.append("\n")
                                
                                # Domain assessments
                                if domains:
                                    output_lines.append("**Domain Assessments:**\n\n")
                                    for domain in domains:
                                        if isinstance(domain, dict):
                                            domain_name = domain.get("domain", "Unknown")
                                            domain_judgment = domain.get("judgment", "Unknown")
                                            domain_rationale = domain.get("rationale", "")
                                            domain_quote = domain.get("supporting_quote", "")
                                        elif hasattr(domain, 'domain'):
                                            domain_name = domain.domain
                                            domain_judgment = domain.judgment
                                            domain_rationale = getattr(domain, 'rationale', '')
                                            domain_quote = getattr(domain, 'supporting_quote', '')
                                        else:
                                            continue
                                        
                                        domain_emoji = {
                                            "Low": "🟢",
                                            "Some concerns": "🟡",
                                            "High": "🟠",
                                            "Critical": "🔴",
                                            "Insufficient information": "⚪"
                                        }.get(domain_judgment, "⚪")
                                        
                                        output_lines.append(f"- **{domain_name}:** {domain_emoji} {domain_judgment}\n")
                                        if domain_rationale:
                                            output_lines.append(f"  - *Rationale:* {domain_rationale}\n")
                                        if domain_quote:
                                            output_lines.append(f"  - *Quote:* \"{domain_quote}\"\n")
                                    output_lines.append("\n")
                            except Exception as e:
                                output_lines.append(f"*Error displaying risk-of-bias assessment: {e}*\n\n")
                        
                        output_lines.append("---\n")
                        output_lines.append("## 🔬 Key Characteristics Evidence\n")
                        
                        # Helper function to get evidence quotes for a KC
                        def get_evidence_quotes_for_kc(evidence_quotes_dict, kc_key, kc_num):
                            """Extract evidence quotes for a specific KC"""
                            evidence_quotes = []
                            if isinstance(evidence_quotes_dict, dict):
                                evidence_quotes = evidence_quotes_dict.get(kc_key, [])
                                if not evidence_quotes:
                                    evidence_quotes = evidence_quotes_dict.get(f"kc{kc_num}", [])
                                if not evidence_quotes and isinstance(evidence_quotes_dict, list):
                                    evidence_quotes = evidence_quotes_dict
                            return evidence_quotes
                        
                        # Show evidence for each KC (SUPPORTED, REFUTED, ASSOCIATED, CAUSALLY_LINKED)
                        has_supported = False
                        has_refuted = False
                        has_associated = False
                        has_causally_linked = False
                        for i in range(1, 13):
                            kc_key = f"KC{i}"
                            status = analysis.get(f"kc{i}_status", "NOT_MENTIONED")
                            
                            if status == "SUPPORTED":
                                has_supported = True
                                output_lines.append(f"### {KC_NAMES[kc_key]} (KC{i}) - SUPPORTED\n")
                                
                                # Show evidence quotes
                                evidence_quotes_dict = analysis.get("evidence_quotes", {})
                                evidence_quotes = get_evidence_quotes_for_kc(evidence_quotes_dict, kc_key, i)
                                
                                if evidence_quotes:
                                    output_lines.append("**Evidence Quotes:**\n")
                                    # Handle both list of strings and list of EvidenceQuote objects
                                    for quote in evidence_quotes:
                                        if isinstance(quote, dict):
                                            quote_text = quote.get("quote", quote.get("text", quote.get("sentence", str(quote))))
                                        else:
                                            quote_text = str(quote)
                                        if quote_text and quote_text.strip():
                                            output_lines.append(f"- \"{quote_text}\"\n")
                                else:
                                    # Try to extract relevant sentences from abstract
                                    kc_name_lower = KC_NAMES[kc_key].lower()
                                    kc_keywords = kc_name_lower.split()
                                    # Add KC-specific keywords
                                    if "reactive" in kc_name_lower or "bioactivation" in kc_name_lower:
                                        kc_keywords.extend(["reactive", "metabolite", "bioactivation", "N-acetyl-p-benzoquinone", "NAPQI"])
                                    elif "oxidative" in kc_name_lower or "stress" in kc_name_lower:
                                        kc_keywords.extend(["oxidative", "ROS", "reactive oxygen", "antioxidant"])
                                    elif "metabolism" in kc_name_lower:
                                        kc_keywords.extend(["metabolism", "metabolic", "metabolize"])
                                    
                                    # Find sentences containing keywords
                                    sentences = abstract_text.split('.')
                                    relevant_sentences = [s.strip() for s in sentences 
                                                         if any(kw in s.lower() for kw in kc_keywords) 
                                                         and len(s.strip()) > 20]
                                    
                                    if relevant_sentences:
                                        output_lines.append("**Relevant Text from Abstract:**\n")
                                        for sent in relevant_sentences[:3]:  # Show up to 3 sentences
                                            output_lines.append(f"- \"{sent}.\"\n")
                                    else:
                                        output_lines.append("*No specific quotes extracted. The abstract may contain relevant information but specific sentences were not identified.*\n")
                                
                                # Show reasoning if available
                                reasoning = analysis.get("reasoning", "")
                                if reasoning:
                                    # Handle dict reasoning (per-KC) or string reasoning
                                    if isinstance(reasoning, dict):
                                        kc_reasoning = reasoning.get(kc_key, reasoning.get(f"kc{i}", ""))
                                        if kc_reasoning:
                                            if isinstance(kc_reasoning, list):
                                                kc_reasoning = " ".join(str(x) for x in kc_reasoning)
                                            output_lines.append(f"**Reasoning:** {kc_reasoning}\n")
                                    elif isinstance(reasoning, str) and reasoning.strip() and reasoning != "No reasoning provided":
                                        # Check if reasoning mentions this KC
                                        if kc_key.lower() in reasoning.lower() or f"kc{i}" in reasoning.lower() or KC_NAMES[kc_key].lower() in reasoning.lower():
                                            output_lines.append(f"**Reasoning:** {reasoning}\n")
                                        else:
                                            # Show reasoning anyway if it's substantial
                                            if len(reasoning) > 50:
                                                output_lines.append(f"**General Reasoning:** {reasoning[:200]}...\n")
                                
                                # If still no reasoning shown, try to provide a basic explanation
                                if not any("Reasoning" in line for line in output_lines[-5:]):
                                    output_lines.append(f"**Note:** This KC was marked as SUPPORTED based on the abstract content. The model identified evidence for {KC_NAMES[kc_key]} but did not extract specific reasoning text.\n")
                                
                                output_lines.append("\n")
                        
                        # Show REFUTED KCs
                        refuted_kcs = []
                        for i in range(1, 13):
                            kc_key = f"KC{i}"
                            status = analysis.get(f"kc{i}_status", "NOT_MENTIONED")
                            
                            if status == "REFUTED":
                                has_refuted = True
                                refuted_kcs.append((i, kc_key))
                        
                        if refuted_kcs:
                            output_lines.append("---\n")
                            output_lines.append("### ❌ REFUTED Key Characteristics\n")
                            output_lines.append("*These KCs were explicitly stated as NOT present in this study.*\n\n")
                            
                            for i, kc_key in refuted_kcs:
                                output_lines.append(f"#### {KC_NAMES[kc_key]} (KC{i}) - REFUTED\n")
                                
                                # Get evidence quotes for REFUTED
                                evidence_quotes_dict = analysis.get("evidence_quotes", {})
                                evidence_quotes = get_evidence_quotes_for_kc(evidence_quotes_dict, kc_key, i)
                                
                                if evidence_quotes:
                                    output_lines.append("**Evidence Quote (showing absence):**\n")
                                    for quote in evidence_quotes:
                                        if isinstance(quote, dict):
                                            quote_text = quote.get("quote", quote.get("text", quote.get("sentence", str(quote))))
                                        else:
                                            quote_text = str(quote)
                                        if quote_text and quote_text.strip():
                                            output_lines.append(f"- \"{quote_text}\"\n")
                                else:
                                    # Try to find negation in abstract
                                    kc_keywords = [KC_NAMES[kc_key].lower()]
                                    negation_patterns = ["no evidence of", "did not cause", "absence of", "lack of", "not observed", "not found"]
                                    
                                    sentences = abstract_text.split('.')
                                    refuted_sentences = []
                                    for sent in sentences:
                                        sent_lower = sent.lower()
                                        if any(kw in sent_lower for kw in kc_keywords) and any(neg in sent_lower for neg in negation_patterns):
                                            refuted_sentences.append(sent.strip())
                                    
                                    if refuted_sentences:
                                        output_lines.append("**Relevant Text from Abstract:**\n")
                                        for sent in refuted_sentences[:2]:
                                            output_lines.append(f"- \"{sent}.\"\n")
                                    else:
                                        output_lines.append("*No specific quote extracted, but the text explicitly states this KC is not present.*\n")
                                
                                # Show reasoning if available
                                reasoning = analysis.get("reasoning", "")
                                if reasoning:
                                    if isinstance(reasoning, dict):
                                        kc_reasoning = reasoning.get(kc_key, reasoning.get(f"kc{i}", ""))
                                        if kc_reasoning:
                                            if isinstance(kc_reasoning, list):
                                                kc_reasoning = " ".join(str(x) for x in kc_reasoning)
                                            output_lines.append(f"**Reasoning:** {kc_reasoning}\n")
                                    elif isinstance(reasoning, str) and reasoning.strip():
                                        if kc_key.lower() in reasoning.lower() or f"kc{i}" in reasoning.lower():
                                            output_lines.append(f"**Reasoning:** {reasoning}\n")
                                
                                output_lines.append("\n")
                        
                        # Show ASSOCIATED KCs
                        associated_kcs = []
                        for i in range(1, 13):
                            kc_key = f"KC{i}"
                            status = analysis.get(f"kc{i}_status", "NOT_MENTIONED")
                            
                            if status == "ASSOCIATED":
                                has_associated = True
                                associated_kcs.append((i, kc_key))
                        
                        if associated_kcs:
                            output_lines.append("---\n")
                            output_lines.append("### ⚠️ ASSOCIATED Key Characteristics\n")
                            output_lines.append("*These KCs show association but not explicit causation.*\n\n")
                            
                            for i, kc_key in associated_kcs:
                                output_lines.append(f"#### {KC_NAMES[kc_key]} (KC{i}) - ASSOCIATED\n")
                                
                                evidence_quotes_dict = analysis.get("evidence_quotes", {})
                                evidence_quotes = get_evidence_quotes_for_kc(evidence_quotes_dict, kc_key, i)
                                
                                if evidence_quotes:
                                    output_lines.append("**Evidence Quote:**\n")
                                    for quote in evidence_quotes:
                                        if isinstance(quote, dict):
                                            quote_text = quote.get("quote", quote.get("text", str(quote)))
                                        else:
                                            quote_text = str(quote)
                                        if quote_text:
                                            output_lines.append(f"- \"{quote_text}\"\n")
                                output_lines.append("\n")
                        
                        # Show CAUSALLY_LINKED KCs
                        causally_linked_kcs = []
                        for i in range(1, 13):
                            kc_key = f"KC{i}"
                            status = analysis.get(f"kc{i}_status", "NOT_MENTIONED")
                            
                            if status == "CAUSALLY_LINKED":
                                has_causally_linked = True
                                causally_linked_kcs.append((i, kc_key))
                        
                        if causally_linked_kcs:
                            output_lines.append("---\n")
                            output_lines.append("### 🔗 CAUSALLY_LINKED Key Characteristics\n")
                            output_lines.append("*These KCs occur indirectly through other mechanisms.*\n\n")
                            
                            for i, kc_key in causally_linked_kcs:
                                output_lines.append(f"#### {KC_NAMES[kc_key]} (KC{i}) - CAUSALLY_LINKED\n")
                                
                                evidence_quotes_dict = analysis.get("evidence_quotes", {})
                                evidence_quotes = get_evidence_quotes_for_kc(evidence_quotes_dict, kc_key, i)
                                
                                if evidence_quotes:
                                    output_lines.append("**Evidence Quote:**\n")
                                    for quote in evidence_quotes:
                                        if isinstance(quote, dict):
                                            quote_text = quote.get("quote", quote.get("text", str(quote)))
                                        else:
                                            quote_text = str(quote)
                                        if quote_text:
                                            output_lines.append(f"- \"{quote_text}\"\n")
                                output_lines.append("\n")
                        
                        if not has_supported and not has_refuted and not has_associated and not has_causally_linked:
                            output_lines.append("*No KCs were marked as SUPPORTED, REFUTED, ASSOCIATED, or CAUSALLY_LINKED for this paper.*\n")
                            output_lines.append("*All KCs are NOT_MENTIONED (not discussed in the text).*\n")
                        
                        # Add Causal Links section
                        causal_links = analysis.get("causal_links", [])
                        if causal_links and len(causal_links) > 0:
                            output_lines.append("---\n")
                            output_lines.append("## Causal Links Between Key Characteristics\n")
                            output_lines.append("*Mechanistic pathways showing how one KC leads to another*\n\n")
                            
                            # Group links by source for better readability
                            links_by_source = {}
                            for link in causal_links:
                                if isinstance(link, dict):
                                    source = link.get("source", link.get("cause", ""))
                                    target = link.get("target", link.get("effect", ""))
                                    evidence = link.get("evidence", "")
                                    strength = link.get("strength", "MODERATE")
                                    
                                    if source and target:
                                        if source not in links_by_source:
                                            links_by_source[source] = []
                                        links_by_source[source].append({
                                            "target": target,
                                            "evidence": evidence,
                                            "strength": strength
                                        })
                            
                            # Display links grouped by source
                            for source_kc in sorted(links_by_source.keys()):
                                source_name = KC_NAMES.get(source_kc, source_kc)
                                output_lines.append(f"### {source_name} ({source_kc})\n")
                                
                                for link_info in links_by_source[source_kc]:
                                    target_kc = link_info["target"]
                                    target_name = KC_NAMES.get(target_kc, target_kc)
                                    evidence = link_info["evidence"]
                                    strength = link_info["strength"]
                                    
                                    # Strength indicator
                                    strength_emoji = {
                                        "STRONG": "🔴",
                                        "MODERATE": "🟡",
                                        "WEAK": "🟢"
                                    }.get(strength, "⚪")
                                    
                                    output_lines.append(f"**→ {target_name} ({target_kc})** {strength_emoji} *{strength}*\n")
                                    if evidence:
                                        output_lines.append(f"  - *Evidence:* \"{evidence}\"\n")
                                    output_lines.append("\n")
                            
                            if not links_by_source:
                                output_lines.append("*Causal links were extracted but could not be parsed correctly.*\n")
                        else:
                            # Show a note if no causal links
                            output_lines.append("---\n")
                            output_lines.append("## Causal Links\n")
                            output_lines.append("*No causal relationships between KCs were identified in this abstract.*\n")
                            output_lines.append("*Note: Causal links require explicit mechanistic statements in the text.*\n\n")
                        
                        # Add Dose-Response Data section
                        dose_response_data = analysis.get("dose_response", [])
                        if dose_response_data and len(dose_response_data) > 0:
                            output_lines.append("---\n")
                            output_lines.append("## Dose-Response Information\n")
                            output_lines.append("*⚠️ Note: Complete dose-response data may require full-text access*\n\n")
                            
                            for dose_info in dose_response_data:
                                if isinstance(dose_info, str) and dose_info.strip():
                                    output_lines.append(f"- {dose_info}\n")
                                elif isinstance(dose_info, dict):
                                    # Handle dict format if present
                                    dose_text = dose_info.get("dose", dose_info.get("text", str(dose_info)))
                                    if dose_text:
                                        output_lines.append(f"- {dose_text}\n")
                            
                            output_lines.append("\n")
                        else:
                            # Optional: Show note about dose-response
                            # output_lines.append("---\n")
                            # output_lines.append("## Dose-Response Information\n")
                            # output_lines.append("*No dose-response data was extracted from the abstract.*\n")
                            # output_lines.append("*Note: Detailed dose-response information may require full-text access.*\n\n")
                            pass  # Don't show empty section
                        
                        return "\n".join(output_lines)
                    except Exception as e:
                        import traceback
                        return f"Error displaying evidence: {str(e)}\n{traceback.format_exc()}"
                
                # Simplified: Removed chatbot functionality from analysis tab
                
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
                                        except ValueError:
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
                                logger.warning(f"Could not save RoB table: {e}")
                        
                        with open(results_file, 'w', encoding='utf-8') as f:
                            json.dump(results_data, f, indent=2, ensure_ascii=False)
                        
                        logger.info(f"Saved complete analysis results: {results_file}")
                        return results_file
                    except Exception as e:
                        logger.warning(f"Could not save analysis results: {e}")
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
                        with open(selected_file, 'r', encoding='utf-8') as f:
                            results_data = json.load(f)
                        
                        # Load abstracts
                        abstracts_file = os.path.join(os.path.dirname(selected_file), "abstracts_for_chat.json")
                        if os.path.exists(abstracts_file):
                            with open(abstracts_file, 'r', encoding='utf-8') as f:
                                abstracts_data = json.load(f)
                            abstracts = abstracts_data.get("abstracts", [])
                        else:
                            abstracts = []
                        
                        summary_text = results_data.get("summary_text", "")
                        evidence_profiles = results_data.get("evidence_profiles", "")
                        saved_plots = results_data.get("saved_plots", {})
                        
                        # Load plots from saved files
                        import matplotlib.pyplot as plt
                        import matplotlib.image as mpimg
                        from PIL import Image
                        
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
                                logger.warning(f"Could not load image {resolved_path}: {e}")
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
                                    logger.warning(f"Could not load RoB table: {e}")
                        
                        return (summary_text, heatmap_fig, network_fig, prisma_fig, 
                               rob_heatmap_fig, rob_summary_fig, evidence_profiles, 
                               rob_table_df, abstracts)
                        
                    except Exception as e:
                        import traceback
                        error_msg = f"Error loading analysis: {str(e)}\n{traceback.format_exc()}"
                        logger.error(error_msg)
                        return None, None, None, None, None, None, None, None, []
                
                # Function to load available analyses
                def auto_prepare_analysis(chemical_name, records_file, results_dir):
                    """Automatically prepare an analysis from study_records.jsonl"""
                    try:
                        import json
                        import pandas as pd
                        from datetime import datetime
                        
                        # Load abstracts from study_records.jsonl
                        abstracts = []
                        rob_data = []
                        with open(records_file, 'r', encoding='utf-8') as f:
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
                                    except (KeyError, TypeError, AttributeError):
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
                            except (ValueError, TypeError, OSError) as e:
                                logger.warning(f"Could not save RoB table: {e}")
                        
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
                        
                        logger.info(f"Auto-prepared {chemical_name}: {len(abstracts)} abstracts")
                        return True
                    except Exception as e:
                        logger.warning(f"Could not auto-prepare {chemical_name}: {e}")
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
                                    with open(abstracts_file, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        analyses.append({
                                            "label": f"{data.get('chemical_name', chemical_dir)} ({data.get('num_abstracts', 0)} abstracts)",
                                            "value": abstracts_file,
                                            "chemical": data.get('chemical_name', chemical_dir)
                                        })
                                except Exception as e:
                                    logger.warning(f"Could not load {abstracts_file}: {e}")
                            
                            # If not found, check for study_records.jsonl and AUTO-PREPARE it
                            elif os.path.exists(records_file):
                                try:
                                    # Count abstracts first
                                    num_abstracts = 0
                                    with open(records_file, 'r', encoding='utf-8') as f:
                                        for line in f:
                                            if line.strip():
                                                num_abstracts += 1
                                    
                                    if num_abstracts > 0:
                                        chemical_name = chemical_dir.replace('_', ' ')
                                        # Auto-prepare the analysis
                                        if auto_prepare_analysis(chemical_name, records_file, chemical_path):
                                            # Now load the prepared file
                                            if os.path.exists(abstracts_file):
                                                with open(abstracts_file, 'r', encoding='utf-8') as f:
                                                    data = json.load(f)
                                                    analyses.append({
                                                        "label": f"{data.get('chemical_name', chemical_dir)} ({data.get('num_abstracts', 0)} abstracts)",
                                                        "value": abstracts_file,
                                                        "chemical": data.get('chemical_name', chemical_dir)
                                                    })
                                except Exception as e:
                                    logger.warning(f"Could not process {records_file}: {e}")
                                    import traceback
                                    traceback.print_exc()
                        
                        # Sort by chemical name
                        analyses.sort(key=lambda x: x.get("chemical", "").lower())
                        return analyses
                    except Exception as e:
                        logger.error(f"Error loading analyses: {e}")
                        import traceback
                        traceback.print_exc()
                        return []
                
                # Simplified: Removed load previous analysis functionality
                
                # State to store saved plots info
                saved_plots_state = gr.State(value={})
                
                analyze_btn.click(
                    fn=analyze_with_progress,
                    inputs=[
                        chemical_input, 
                        model_checkboxes, 
                        prompt_type_dropdown, 
                        custom_prompt_textbox, 
                        max_articles_dropdown, 
                        max_articles_custom_input,
                        support_threshold_min_papers,
                        support_threshold_min_percentage
                    ],
                    outputs=[
                        summary_output,
                        kc_summary_table,
                        heatmap_output, 
                        papers_table_output,
                        abstracts_state,
                        kc_analyses_state,
                        rob_assessments_state
                    ],
                    show_progress="full"
                ).then(
                    fn=show_analysis_chatbot,
                    inputs=[abstracts_state],
                    outputs=[analysis_chatbot, analysis_msg_input, analysis_send_btn, analysis_reset_btn]
                )
                
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
                
                # Make papers table rows clickable - show evidence for each KC
                papers_table_output.select(
                    fn=show_paper_evidence,
                    inputs=[abstracts_state, kc_analyses_state, rob_assessments_state],
                    outputs=[evidence_viewer]
                )
                
                # Simplified: Removed chatbot functionality from analysis tab
                
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
                        logger.error(error_msg)
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
    logger.info(f"Prompt mode: {config.analysis.prompt_mode}")
    logger.info(f"Enhanced prompts: {config.analysis.enable_enhanced_prompts}")
    
    app = create_interface()
    port = find_free_port(7862)
    
    # For WSL: bind to 0.0.0.0 to allow access; log localhost URLs
    logger.info("=" * 70)
    logger.info(f"Starting Gradio app on port {port}...")
    logger.info("=" * 70)
    logger.info("Access the application at:")
    logger.info(f"   http://localhost:{port}/")
    logger.info(f"   http://127.0.0.1:{port}/")
    logger.info("Note: If using WSL, use 'localhost' or '127.0.0.1' from Windows browser")
    logger.info("   (Do NOT use 0.0.0.0 - that's only the server bind address)")
    logger.info("=" * 70)
    
    app.launch(share=False, server_name="0.0.0.0", server_port=port)
