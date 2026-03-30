# Code Explanation: AI Toxicologist Application

## Overview
This application performs automated systematic literature reviews for chemical hepatotoxicity assessment using the Key Characteristics (KC) framework. It uses AI (LLMs via Ollama) to analyze scientific abstracts and extract mechanistic evidence.

## Main Components

### 1. **Chemical Standardization** (`standardize_chemical_name`)
- **Purpose**: Resolves chemical names using PubChem database
- **What it does**:
  - Takes a chemical name (e.g., "acetaminophen")
  - Queries PubChem to get standardized IUPAC name
  - Retrieves PubChem CID (unique identifier)
  - Collects synonyms and common names for better searching
  - Returns standardized name, CID, and list of search terms

### 2. **PubMed Search** (`fetch_pubmed_abstracts`)
- **Purpose**: Fetches relevant scientific abstracts from PubMed
- **What it does**:
  - Uses BioPython's Entrez API to search PubMed
  - Uses enhanced search with MeSH terms (medical subject headings)
  - Searches using multiple chemical synonyms
  - Retrieves abstracts with metadata (title, abstract, PMID, year, authors, journal)
  - Returns list of abstracts and search log

### 3. **Relevance Filtering** (`check_relevance`)
- **Purpose**: Filters abstracts to keep only those relevant to liver toxicity
- **What it does**:
  - Uses LLM to determine if abstract discusses liver toxicity
  - Excludes abstracts about:
    - Chemical treating liver cancer (efficacy studies)
    - Toxicity in other organs (kidney, heart) but not liver
    - Metabolism without toxicity
  - Returns True/False for each abstract

### 4. **Full-Text Retrieval** (`fetch_fulltext`)
- **Purpose**: Attempts to retrieve full-text articles (not just abstracts)
- **What it does**:
  - Checks if full-text is available for each study
  - Retrieves from multiple sources if available
  - Improves quality of Risk-of-Bias assessment
  - Falls back to abstract if full-text unavailable

### 5. **KC Analysis** (`analyze_abstract_with_llm`)
- **Purpose**: Analyzes each abstract against 12 Key Characteristics
- **What it does**:
  - Uses LLM (via LangChain + Ollama) to analyze abstract text
  - For each of 12 KCs, determines status:
    - **SUPPORTED**: Chemical causes this effect
    - **ASSOCIATED**: Chemical is associated with this effect
    - **CAUSALLY_LINKED**: Chemical is causally linked to this effect
    - **REFUTED**: Chemical does NOT cause this effect
    - **NOT_MENTIONED**: Not discussed in abstract
  - Extracts evidence quotes (exact sentences supporting each KC)
  - Identifies causal links between KCs (e.g., KC1 → KC5)
  - Provides chain-of-thought reasoning
  - Returns structured analysis with all KC statuses and evidence

### 6. **Multi-Reviewer Mode** (`consolidate_kc_analyses`)
- **Purpose**: Uses multiple LLM models as independent reviewers
- **What it does**:
  - Runs same analysis with different models (e.g., llama3.1, llama3.2, mixtral)
  - Consolidates results using consensus (majority voting)
  - Calculates inter-model agreement statistics (Cohen's kappa)
  - Ranks papers by consensus strength
  - Provides more reliable results than single model

### 7. **Risk-of-Bias Assessment** (`assess_rob_with_llm`)
- **Purpose**: Evaluates study quality using OHAT/ROBINS-I framework
- **What it does**:
  - Uses LLM to assess multiple bias domains:
    - Selection bias
    - Performance bias
    - Detection bias
    - Attrition bias
    - Reporting bias
  - Provides overall judgment: Low Risk / Some Concerns / High Risk
  - Uses full-text if available for better assessment

### 8. **Certainty Grading** (`assess_certainty_per_kc`)
- **Purpose**: Rates certainty of evidence per Key Characteristic
- **What it does**:
  - Uses GRADE/OHAT methodology
  - Considers:
    - Risk-of-Bias across studies
    - Consistency of findings
    - Directness of evidence
    - Precision of estimates
  - Provides rating: High / Moderate / Low / Very Low certainty

### 9. **Evidence Matrix** (`create_evidence_matrix`)
- **Purpose**: Creates matrix showing which papers support which KCs
- **What it does**:
  - Creates table: Papers (rows) × Key Characteristics (columns)
  - Values: 1 = SUPPORTED, 0.7 = ASSOCIATED, 0.5 = CAUSALLY_LINKED, -1 = REFUTED, 0 = NOT_MENTIONED
  - Used to create heatmap visualization

### 10. **Causal Pathway Network** (`create_network_graph`)
- **Purpose**: Visualizes mechanistic relationships between KCs
- **What it does**:
  - Creates directed graph (network) showing causal links
  - Nodes = Key Characteristics
  - Edges = Causal relationships (e.g., KC1 → KC5)
  - Edge weights = frequency of causal links across papers
  - Color-codes nodes by role (upstream/intermediate/downstream)

### 11. **PRISMA Flow Diagram** (`create_prisma_flow_diagram`)
- **Purpose**: Creates standardized PRISMA 2020 flow diagram
- **What it does**:
  - Shows screening process:
    - Records identified
    - Records screened
    - Records excluded
    - Full-text assessed
    - Studies included
  - Standard format for systematic reviews

### 12. **Provenance Tracking** (`save_provenance`, `save_study_record`)
- **Purpose**: Records all analysis details for reproducibility
- **What it does**:
  - Saves search queries and parameters
  - Records model names and settings
  - Stores prompt hashes
  - Tracks all decisions and exclusions
  - Enables full reproducibility

## Main Workflow (`analyze_chemical` function)

1. **Input**: Chemical name, model selection, settings
2. **Step 1**: Standardize chemical name, search PubMed
3. **Step 2**: Filter abstracts for relevance
4. **Step 2.5**: Attempt full-text retrieval
5. **Step 3**: Analyze abstracts with LLM(s) against 12 KCs
   - If multi-reviewer: Consolidate results
6. **Step 4**: Assess Risk-of-Bias for each study
7. **Step 5**: Generate visualizations (heatmap, network, PRISMA)
8. **Step 6**: Grade certainty of evidence per KC
9. **Output**: Summary, visualizations, evidence profiles

## Key Features

- **Parallel Processing**: Can analyze multiple abstracts simultaneously
- **GPU Acceleration**: Uses GPU if available for faster LLM inference
- **RAG System**: Retrieval-Augmented Generation for better context
- **Hierarchical Processing**: Prioritizes important text sections
- **Confidence Scoring**: Calibrates predictions and filters low-confidence
- **Active Learning**: Selects most informative abstracts for analysis

## Output Files

All results saved to `results/{chemical_name}/`:
- `provenance_*.json`: Complete analysis provenance
- `study_records.jsonl`: Individual study analyses
- `search_log_*.json`: Search query details
- `*.png`: Visualizations (heatmap, network, PRISMA, RoB)

## Technical Stack

- **Frontend**: Gradio (Python web framework)
- **LLM**: LangChain + Ollama (open-source models)
- **Data**: pandas, numpy
- **Visualization**: matplotlib, seaborn, networkx
- **APIs**: PubChem (PubChemPy), PubMed (BioPython Entrez)
