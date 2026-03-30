# How Liver Toxicity Relevance Filtering Works

## Overview
The relevance filtering step acts as a "gatekeeper" that filters abstracts to keep only those relevant to **liver toxicity** of the specific chemical. This prevents wasting computational resources analyzing irrelevant papers.

## The `check_relevance()` Function

### Location
- **File**: `app.py`
- **Function**: `check_relevance(abstract_text, title, chemical_name, model_name)`
- **Returns**: `True` if relevant, `False` if not relevant

### How It Works

#### Step 1: Prepare the Prompt
The function creates a specific prompt for the LLM that asks it to determine relevance:

```python
SYSTEM_PROMPT_GATEKEEPER = """### TASK
Determine if the following abstract describes **ADVERSE EFFECTS**, **TOXICITY**, or **SAFETY HAZARDS** of the chemical '{chemical_name}' specifically in the **LIVER**.

### CRITERIA
- **YES**: Abstract discusses hepatotoxicity, liver injury, DILI, liver enzyme elevation, steatosis, fibrosis, or mechanisms of liver damage caused by the chemical.
- **NO**: Abstract discusses the chemical TREATING liver cancer (efficacy), metabolism without toxicity, or toxicity in other organs (kidney, heart) but not liver.

### OUTPUT
Answer with a single word: "YES" or "NO".

Title: {title}
Abstract: {abstract_text}"""
```

#### Step 2: Truncate Abstract (if needed)
- The abstract text is truncated to `config.search.relevance_check_truncate` characters (default: 2000)
- This ensures the prompt doesn't exceed token limits while keeping enough context

#### Step 3: Call the LLM
- Uses the same LLM model as the main analysis (default: llama3.1)
- Uses **deterministic temperature (0.0)** for consistent results
- Sends the prompt to the LLM via Ollama

#### Step 4: Parse the Response
The LLM responds with "YES" or "NO", but sometimes adds explanations. The code handles this:

```python
answer = response.content.strip().upper()

# Extract YES/NO from response (handle cases where model adds explanation)
is_relevant = "YES" in answer and "NO" not in answer[:10]  # Check first 10 chars
if not is_relevant:
    is_relevant = answer.startswith("Y") and not answer.startswith("NO")
```

**Logic**:
- If "YES" appears and "NO" doesn't appear in first 10 characters → Relevant
- If response starts with "Y" but not "NO" → Relevant
- Otherwise → Not relevant

#### Step 5: Return Result
- Returns `True` if relevant, `False` if not
- Logs the decision for debugging

## What Gets INCLUDED (YES)

Abstracts are marked as **relevant** if they discuss:

1. **Hepatotoxicity** - Direct liver toxicity
2. **Liver injury** - Any form of liver damage
3. **DILI** - Drug-Induced Liver Injury
4. **Liver enzyme elevation** - ALT, AST, ALP increases
5. **Steatosis** - Fatty liver disease
6. **Fibrosis** - Liver scarring
7. **Mechanisms of liver damage** - How the chemical harms the liver

**Example**: "Acetaminophen overdose causes hepatocellular necrosis and elevated liver enzymes..."

## What Gets EXCLUDED (NO)

Abstracts are marked as **not relevant** if they discuss:

1. **Efficacy studies** - Chemical treating liver cancer (therapeutic use)
2. **Metabolism without toxicity** - How the chemical is metabolized, but no adverse effects
3. **Other organ toxicity** - Toxicity in kidney, heart, brain, etc., but NOT liver
4. **General pharmacology** - Drug mechanisms unrelated to liver toxicity

**Examples**:
- ❌ "Sorafenib treatment improves survival in hepatocellular carcinoma patients" (efficacy)
- ❌ "Acetaminophen is metabolized by CYP2E1 in the liver" (metabolism only, no toxicity)
- ❌ "Chemical X causes nephrotoxicity and cardiotoxicity" (other organs, not liver)

## How It's Used in the Workflow

### In `analyze_chemical()` function:

```python
# Step 2: Relevance Filtering
for idx, abstract in enumerate(all_abstracts):
    if check_relevance(
        abstract.get("abstract", ""), 
        abstract.get("title", ""), 
        standardized_name, 
        model_names[0]  # Uses first model for relevance check
    ):
        relevant_abstracts.append(abstract)  # Keep it
    else:
        excluded_title_abstract.append(abstract)  # Exclude it
    
    # Stop if we reach the analysis limit
    if len(relevant_abstracts) >= config.search.max_abstracts_analyze:
        break
```

### Process:
1. Loops through all retrieved abstracts
2. Calls `check_relevance()` for each abstract
3. If relevant → adds to `relevant_abstracts` list
4. If not relevant → adds to `excluded_title_abstract` list (for PRISMA tracking)
5. Stops early if analysis limit is reached (default: 500 abstracts)

## Configuration Options

### Key Parameters (in `config.py`):

```python
class SearchConfig:
    relevance_check_truncate: int = 2000  # Characters to use for relevance check
    max_abstracts_analyze: int = 20     # Max abstracts to analyze after filtering

class LLMConfig:
    temperature_relevance: float = 0.0    # Deterministic (0.0) for consistency
```

## Why This Approach?

### Advantages:
1. **Semantic Understanding**: LLM understands context, not just keywords
   - Can distinguish "liver cancer treatment" (exclude) from "liver toxicity" (include)
   - Understands synonyms and related terms

2. **Flexible**: Handles various ways authors describe liver toxicity
   - "hepatotoxicity", "liver injury", "DILI", "hepatocellular damage" all recognized

3. **Accurate**: Better than keyword matching
   - Keyword search might miss papers using different terminology
   - LLM understands the meaning, not just exact words

4. **Fast**: Quick binary decision (YES/NO) before expensive full analysis

### Limitations:
1. **LLM Dependency**: Requires LLM to be running
2. **Cost**: Each abstract requires one LLM call
3. **False Positives/Negatives**: LLM might occasionally misclassify
   - Conservative approach: If check fails, includes abstract by default

## Error Handling

If the relevance check fails (LLM error, timeout, etc.):

```python
except Exception as e:
    # Default to including if check fails (conservative approach)
    # Log warning but don't fail the entire analysis
    print(f"Warning: Relevance check failed, including abstract by default")
    return True  # Include it to be safe
```

**Conservative approach**: When in doubt, include the abstract rather than exclude it. Better to analyze a few extra abstracts than miss important evidence.

## Performance Considerations

- **Parallel Processing**: Can be parallelized, but typically runs sequentially
- **Speed**: Each check takes ~1-3 seconds depending on LLM speed
- **Early Stopping**: Stops once analysis limit is reached
- **Caching**: Could be cached, but currently not implemented

## Example Output

During analysis, you'll see progress messages:

```
🔍 STEP 2: RELEVANCE FILTERING
--------------------------------------------------------------------------------
   📊 Filtering 150 abstracts for liver toxicity relevance...
Relevance check for 'Acetaminophen-induced liver injury...': YES -> True
Relevance check for 'Sorafenib treatment in HCC...': NO -> False
Relevance check for 'Metabolism of acetaminophen...': NO -> False
   ✓ Relevant: 45 abstracts
   ✗ Excluded: 105 abstracts
   ⏱️  Filtering completed in 120.5s
```

## Summary

The relevance filtering uses an **AI-powered semantic filter** that:
1. Uses LLM to understand abstract content
2. Determines if it discusses liver toxicity (not just mentions liver)
3. Excludes efficacy studies, metabolism-only papers, and other-organ toxicity
4. Uses deterministic settings for consistency
5. Takes a conservative approach (includes if uncertain)

This ensures only relevant abstracts proceed to the expensive KC analysis step, saving time and computational resources while maintaining high accuracy.
