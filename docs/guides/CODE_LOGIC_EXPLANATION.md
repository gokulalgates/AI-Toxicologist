# AI Toxicologist: Complete Code Logic Explanation

## 🏗️ Overall Architecture

The application follows a **pipeline architecture** with 6 main steps, mimicking a systematic literature review process:

```
User Input → Step 1: Chemical Standardization → Step 2: Literature Search → 
Step 3: Relevance Filtering → Step 4: KC Analysis → Step 5: Risk-of-Bias → 
Step 6: Visualization & Output
```

---

## 📋 Main Function: `analyze_chemical()`

**Location**: `app.py`, line 911

This is the **orchestrator function** that coordinates all steps. It takes:
- `chemical_name`: The chemical to analyze
- `model_names`: List of LLM models to use (single or multi-reviewer)
- `enable_rob`: Whether to assess risk-of-bias
- `enable_certainty`: Whether to grade certainty

**Returns**: 9 outputs (summary text, 5 plots, evidence profiles, RoB table, abstracts)

---

## 🔄 Step-by-Step Logic Flow

### **STEP 1: Chemical Standardization** ("The Librarian")

**Function**: `standardize_chemical_name()` (line ~250)

**Logic**:
1. **Query PubChem** with the chemical name
2. **Get standardized name** (IUPAC, preferred name)
3. **Extract synonyms** (common names, trade names, CAS numbers)
4. **Build search terms**:
   - Standardized name
   - Up to 10 synonyms
   - Chemical name + "hepatotoxicity" / "liver toxicity"

**Example**:
```
Input: "acetaminophen"
→ Standardized: "acetaminophen"
→ Synonyms: ["paracetamol", "APAP", "N-acetyl-p-aminophenol", ...]
→ Search terms: ["acetaminophen hepatotoxicity", "paracetamol liver", ...]
```

**Why**: Ensures we find all relevant papers, even if they use different names.

---

### **STEP 2: PubMed Search** ("The Librarian")

**Function**: `fetch_pubmed_abstracts()` (line ~265)

**Logic**:
1. **For each search term**:
   - Query PubMed API (Entrez)
   - Use MeSH terms when available
   - Fetch abstracts with metadata (title, authors, journal, year, PMID)
2. **Combine results** from all search terms
3. **Remove duplicates** (by PMID)
4. **Limit results** (default: 100 abstracts initially)

**Data Structure**:
```python
abstract = {
    "pmid": "12345678",
    "title": "Study title...",
    "abstract": "Full abstract text...",
    "authors": "Smith, J., et al.",
    "journal": "Toxicology",
    "year": 2023
}
```

**Why**: Gathers all potentially relevant literature from PubMed.

---

### **STEP 3: Relevance Filtering** ("The Gatekeeper")

**Function**: `check_relevance()` (line ~390)

**Logic**:
1. **For each abstract**:
   - Extract title + abstract text
   - Send to LLM with prompt: "Is this about liver toxicity of [chemical]?"
   - LLM returns: "YES" or "NO"
2. **Filter abstracts**:
   - Keep only "YES" responses
   - Stop when reaching analysis limit (default: 20 abstracts)
3. **Track excluded abstracts** for PRISMA diagram

**Prompt Example**:
```
"Is the following abstract about liver toxicity or hepatotoxicity 
of [chemical]? Answer YES or NO only.

Title: [title]
Abstract: [abstract]"
```

**Why**: Removes irrelevant papers (e.g., papers about cancer treatment, metabolism in other organs).

**Performance**: Uses first model only (faster) with temperature=0.0 (deterministic).

---

### **STEP 4: Full-Text Retrieval** (Optional)

**Functions**: `has_fulltext_available()`, `fetch_fulltext()` (from `fulltext_retrieval.py`)

**Logic**:
1. **For each relevant abstract**:
   - Check if full-text PDF is available (via DOI/PMID)
   - Try multiple sources: PubMed Central, DOI links, etc.
2. **Extract text** from PDF if found
3. **Store full-text** in abstract dict as `abstract["fulltext"]`

**Why**: Full-text provides more detail for risk-of-bias assessment and better KC analysis.

---

### **STEP 5: Key Characteristics Analysis** ("The Analyst")

**Function**: `analyze_abstract_with_llm()` (line ~439)

This is the **core analysis step**. Here's the detailed logic:

#### **5.1. Prompt Selection**

**Logic**:
```python
if chemical == "acetaminophen" and prompt_mode == "liberal":
    prompt = get_liberal_prompt()  # Very permissive
elif chemical == "acetaminophen":
    prompt = get_acetaminophen_specific_prompt()  # Known mechanisms
elif prompt_mode == "liberal":
    prompt = get_liberal_prompt()  # Permissive for all
else:
    prompt = get_enhanced_prompt_with_synonyms()  # Standard enhanced
```

**Why**: Different chemicals need different prompt strategies. Acetaminophen has well-known mechanisms, so we can be more specific.

#### **5.2. Prompt Enhancement**

**Logic**:
1. **Add causal reasoning** framework (from `causal_reasoning.py`)
2. **Add RAG context** (if enabled): Similar abstracts analyzed before
3. **Add hierarchical processing** (if full-text available): Prioritize methods/results sections

**RAG Context**:
- Retrieves similar abstracts from previous analyses
- Provides examples of how KCs were detected before
- Helps LLM recognize patterns

**Hierarchical Processing**:
- Full-text is long, so prioritize:
  1. Abstract (always)
  2. Methods section (how study was done)
  3. Results section (what was found)
  4. Discussion (interpretation)

#### **5.3. LLM Analysis**

**Prompt Structure**:
```
ROLE: Expert Toxicologist
KC DEFINITIONS: [12 KCs with definitions]
INSTRUCTIONS: 
  - For each KC, determine: SUPPORTED, REFUTED, or NOT_MENTIONED
  - Extract evidence quotes
  - Identify causal links (KC1 → KC5)
  - Extract dose-response data
OUTPUT FORMAT: JSON with Pydantic schema
```

**LLM Processing**:
1. **Send prompt** to Ollama (local LLM)
2. **Parse JSON response** using Pydantic
3. **Validate** response structure
4. **Extract**:
   - KC statuses (12 values)
   - Evidence quotes (dict: {"KC1": ["quote1", "quote2"]})
   - Causal links (list: [{"source": "KC1", "target": "KC5", "strength": "STRONG"}])
   - Dose-response data
   - Reasoning text

**Output Structure**:
```python
{
    "kc1_status": "SUPPORTED",
    "kc2_status": "NOT_MENTIONED",
    ...
    "kc12_status": "SUPPORTED",
    "evidence_quotes": {
        "KC1": ["Acetaminophen is metabolized by CYP2E1 to NAPQI..."],
        "KC5": ["NAPQI depletes glutathione, causing oxidative stress..."]
    },
    "causal_links": [
        {"source": "KC1", "target": "KC5", "evidence": "...", "strength": "STRONG"}
    ],
    "dose_response": ["50 mg/kg", "10-100 μM"],
    "reasoning": "Acetaminophen exhibits multiple mechanisms..."
}
```

#### **5.4. Multi-Reviewer Mode** (if multiple models selected)

**Logic**:
1. **For each model** (llama3, mixtral, etc.):
   - Run analysis independently
   - Store results in `all_model_analyses`
2. **Consolidate results** using `consolidate_kc_analyses()`:
   - **For each KC in each paper**:
     - Collect all model judgments: ["SUPPORTED", "SUPPORTED", "NOT_MENTIONED"]
     - **Majority voting**: Most common judgment wins
     - **Confidence**: % of models agreeing (e.g., 2/3 = 67%)
3. **Rank papers** by consensus strength

**Consensus Example**:
```
Paper 1, KC1:
  llama3: SUPPORTED
  mixtral: SUPPORTED
  mistral: NOT_MENTIONED
  → Consensus: SUPPORTED (67% confidence, 2/3 agree)
```

**Why**: Multiple reviewers reduce bias and improve reliability (like human systematic reviews).

---

### **STEP 6: Risk-of-Bias Assessment** ("The Critic")

**Function**: `assess_rob_with_llm()` (from `risk_of_bias.py`)

**Logic**:
1. **For each abstract**:
   - Use OHAT framework (7 domains):
     - Selection Bias
     - Confounding
     - Performance Bias
     - Detection/Measurement Bias
     - Attrition Bias
     - Selective Reporting
     - Other Sources of Bias
2. **LLM assesses each domain**:
   - Judgment: Low, Some concerns, High, Critical, Insufficient information
   - Rationale: Why this judgment
   - Supporting quote: Evidence from text
3. **Determine overall judgment**: Worst domain judgment (or "Insufficient information" if multiple domains lack info)

**Output**:
```python
{
    "domains": [
        {"domain": "Selection Bias", "judgment": "Low", "rationale": "...", "quote": "..."},
        ...
    ],
    "overall_judgment": "Some concerns"
}
```

**Why**: Assesses study quality to weight evidence appropriately.

---

### **STEP 7: Certainty Grading** (Optional)

**Function**: `assess_certainty_per_kc()` (from `certainty_grading.py`)

**Logic**:
1. **For each KC**:
   - Collect all studies supporting it
   - Assess:
     - **Consistency**: Do studies agree?
     - **Precision**: How many studies?
     - **Risk-of-Bias**: Average RoB of supporting studies
     - **Indirectness**: Direct evidence or inferred?
2. **Grade certainty**: High, Moderate, Low, Very Low

**Why**: GRADE/OHAT framework for evidence quality assessment.

---

### **STEP 8: Visualization & Output** ("The Architect")

**Functions**: Multiple visualization functions

#### **8.1. Evidence Matrix**

**Function**: `create_evidence_matrix()` (line ~715)

**Logic**:
1. **Create DataFrame**:
   - Rows: Papers
   - Columns: KCs
   - Values: 1 (SUPPORTED), 0 (NOT_MENTIONED), -1 (REFUTED)
2. **Create heatmap**:
   - Green = SUPPORTED
   - White = NOT_MENTIONED
   - Red = REFUTED

**Why**: Visual summary of which papers support which mechanisms.

#### **8.2. Causal Pathway Network**

**Function**: `create_causal_pathway_network()` (line ~800)

**Logic**:
1. **Extract all causal links** from analyses
2. **Build graph**:
   - Nodes: KCs
   - Edges: Causal links (KC1 → KC5)
   - Edge weights: Frequency of link across papers
3. **Layout**: Force-directed graph (networkx)
4. **Visualize**: Thicker edges = more common pathway

**Why**: Shows mechanistic relationships between KCs.

#### **8.3. PRISMA Flow Diagram**

**Function**: `create_prisma_flow_diagram()` (from `prisma.py`)

**Logic**:
1. **Track numbers**:
   - Total abstracts found
   - Excluded (not relevant)
   - Assessed
   - Included
2. **Create flow diagram** following PRISMA 2020 template

**Why**: Standard format for systematic reviews.

#### **8.4. Risk-of-Bias Visualizations**

**Functions**: `create_rob_heatmap_figure()`, `create_rob_summary_figure()` (from `rob_visualization.py`)

**Logic**:
1. **Heatmap**: KCs (rows) × Domains (cols) showing average RoB
2. **Summary bar chart**: Distribution of overall judgments

**Why**: Visual summary of study quality.

---

## 🔧 Key Algorithms & Logic

### **1. Relevance Filtering Algorithm**

```python
for abstract in all_abstracts:
    is_relevant = check_relevance(abstract, chemical_name, model)
    if is_relevant:
        relevant_abstracts.append(abstract)
    if len(relevant_abstracts) >= MAX_ANALYZE:
        break  # Stop when limit reached
```

**Optimization**: Stops early when enough relevant abstracts found.

### **2. Multi-Reviewer Consensus Algorithm**

```python
for each paper:
    for each KC:
        judgments = [model1.judgment, model2.judgment, model3.judgment]
        consensus = most_common(judgments)  # Majority vote
        confidence = count(consensus) / len(models)
```

**Weighted Version** (if enabled):
```python
weighted_votes = {}
for judgment, model in zip(judgments, models):
    weight = MODEL_WEIGHTS[model]  # llama3.2=1.0, mixtral=0.95, etc.
    weighted_votes[judgment] += weight
consensus = max(weighted_votes, key=weighted_votes.get)
```

### **3. Causal Link Extraction**

**Logic**:
1. **LLM identifies** explicit causal statements:
   - "Metabolism (KC1) leads to oxidative stress (KC5)"
   - "NAPQI causes mitochondrial dysfunction (KC7)"
2. **Validate links** using `validate_causal_link()`:
   - Check temporal relationship (cause before effect)
   - Check mechanistic plausibility
   - Verify strength (STRONG/MODERATE/WEAK)
3. **Aggregate** across papers to find common pathways

### **4. Parallel Processing**

**Logic**:
```python
with ThreadPoolExecutor(max_workers=optimal_workers) as executor:
    futures = [executor.submit(analyze_abstract, abstract) 
               for abstract in abstracts]
    results = [future.result() for future in as_completed(futures)]
```

**Why**: Analyzes multiple abstracts simultaneously (I/O-bound LLM calls).

**Optimization**: Worker count based on GPU availability:
- 1 GPU → 2-4 workers
- Multiple GPUs → More workers

---

## 📊 Data Flow

```
User Input (chemical name, models)
    ↓
[Step 1] Standardize → (standardized_name, synonyms, search_terms)
    ↓
[Step 2] Search PubMed → (list of abstracts with metadata)
    ↓
[Step 3] Filter Relevance → (relevant_abstracts, excluded_abstracts)
    ↓
[Step 4] Retrieve Full-text → (abstracts with fulltext if available)
    ↓
[Step 5] Analyze KCs → (kc_analyses: list of dicts with KC statuses)
    ↓
[Step 6] Assess RoB → (rob_assessments: list of RoB objects)
    ↓
[Step 7] Grade Certainty → (certainty_grades: dict per KC)
    ↓
[Step 8] Visualize → (plots, summary text, evidence profiles)
    ↓
Output (displayed in Gradio UI + saved to files)
```

---

## 🎯 Key Design Patterns

### **1. Retry Logic**

**Function**: `retry_with_backoff()` (from `utils.py`)

**Logic**:
```python
@retry_with_backoff(max_retries=3, delay=1.0)
def analyze_abstract():
    # LLM call that might fail
    pass
```

**Why**: LLM calls can fail (network, timeout). Retry with exponential backoff.

### **2. Caching**

**Function**: `cache_result()` (from `utils.py`)

**Logic**:
- Cache function results based on input hash
- Avoid re-computing expensive operations

**Why**: Chemical standardization, relevance checks can be cached.

### **3. Error Handling**

**Custom Exceptions** (from `exceptions.py`):
- `SearchError`: PubMed search failed
- `LLMError`: LLM call failed
- `LLMTimeoutError`: LLM took too long
- `LLMParseError`: Couldn't parse LLM response

**Strategy**: Graceful degradation (if relevance check fails, include abstract by default).

### **4. Configuration Management**

**File**: `config.py`

**Logic**:
- Centralized configuration using dataclasses
- Environment variable overrides
- Default values for all settings

**Why**: Easy to adjust behavior without code changes.

---

## 🔄 State Management

### **Gradio State Component**

**Usage**: `abstracts_state = gr.State(value=[])`

**Logic**:
- Stores abstracts list between function calls
- Used for interactive RoB table (click to view abstract)

**Why**: Gradio functions are stateless. State component maintains data across interactions.

---

## 🚀 Performance Optimizations

### **1. Parallel Processing**
- Analyze multiple abstracts simultaneously
- Optimal worker count based on GPU availability

### **2. Early Stopping**
- Stop relevance filtering when limit reached
- Don't process more abstracts than needed

### **3. GPU Acceleration**
- Offload LLM inference to GPU
- Configure GPU layers for Ollama

### **4. Caching**
- Cache expensive operations (standardization, relevance checks)

---

## 📝 Output Files

Results are saved to `results/{chemical_name}/`:

1. **`study_records.jsonl`**: One JSON per line with full analysis
2. **`provenance_{timestamp}.json`**: Complete provenance record
3. **`search_log_{timestamp}.json`**: Search query and results
4. **Plots**: PNG/PDF versions of visualizations

---

## 🎨 UI Logic (Gradio)

**Function**: `create_interface()` (line ~1720)

**Components**:
1. **Input**: Chemical name textbox, model checkboxes
2. **Button**: "Analyze Chemical" triggers analysis
3. **Outputs**: 
   - Summary textbox
   - 5 plot components
   - Evidence profiles textbox
   - RoB table (interactive)
   - Abstract viewer (clickable)

**Event Flow**:
```
User clicks "Analyze Chemical"
    ↓
analyze_with_progress() called
    ↓
analyze_chemical() executes (6 steps)
    ↓
Returns 9 outputs
    ↓
Gradio updates all output components
    ↓
User can interact with RoB table
    ↓
Click row → show_abstract_from_table() → display abstract
```

---

## 🔍 Key Functions Reference

| Function | Purpose | Location |
|----------|---------|----------|
| `analyze_chemical()` | Main orchestrator | `app.py:911` |
| `standardize_chemical_name()` | Get synonyms, CID | `app.py:~250` |
| `fetch_pubmed_abstracts()` | Search PubMed | `app.py:265` |
| `check_relevance()` | Filter abstracts | `app.py:390` |
| `analyze_abstract_with_llm()` | Core KC analysis | `app.py:439` |
| `consolidate_kc_analyses()` | Multi-reviewer consensus | `multi_reviewer.py:13` |
| `assess_rob_with_llm()` | Risk-of-bias | `risk_of_bias.py:46` |
| `create_evidence_matrix()` | Build heatmap data | `app.py:715` |
| `create_causal_pathway_network()` | Build network graph | `app.py:800` |

---

## 💡 Key Insights

1. **Pipeline Architecture**: Each step feeds into the next, with clear separation of concerns.

2. **LLM as Core Engine**: Uses LLMs for:
   - Relevance filtering (binary classification)
   - KC extraction (structured extraction)
   - Risk-of-bias assessment (structured assessment)

3. **Multi-Reviewer Pattern**: Mimics human systematic reviews with multiple independent reviewers.

4. **Provenance Tracking**: Records everything for reproducibility (models, prompts, data).

5. **Graceful Degradation**: If a step fails, continue with defaults rather than crashing.

6. **Configuration-Driven**: Behavior controlled by config, not hardcoded.

---

This architecture enables systematic, reproducible, and transparent hepatotoxicity assessment using AI-powered literature review.
