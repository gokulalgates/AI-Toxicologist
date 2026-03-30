# How KC Status Determination is Implemented Programmatically

## Overview

This document explains the **actual code implementation** of how the LLM determines KC status. It shows the step-by-step programmatic process from sending the prompt to extracting the final status.

---

## Step-by-Step Code Flow

### Step 1: Setup and Prompt Construction

**Location**: `app.py` lines 541-773 (`analyze_abstract_with_llm` function)

```python
def analyze_abstract_with_llm(abstract_text: str, title: str, model_name: str = "llama3.1", ...):
    """
    Main function that orchestrates the LLM analysis
    """
    # 1. Initialize LLM
    llm = ChatOllama(
        model=model_name,
        temperature=config.llm.temperature,  # Default: 0.1
    )
    
    # 2. Build KC definitions text
    kc_definitions_text = "\n".join([
        f"{kc}: {definition}" 
        for kc, definition in KC_DEFINITIONS.items()
    ])
    # Example output:
    # "KC1: Is reactive and/or is metabolized (bioactivated) to reactive moieties.\nKC2: Causes death..."
    
    # 3. Create Pydantic parser for structured output
    parser = PydanticOutputParser(pydantic_object=KCAnalysis)
    format_instructions = parser.get_format_instructions()
    # This generates JSON schema instructions for the LLM
    
    # 4. Build the prompt (varies based on chemical and settings)
    if config.analysis.enable_enhanced_prompts:
        # Use enhanced prompts with better synonym recognition
        base_prompt = get_enhanced_prompt_with_synonyms(
            kc_definitions_text, 
            format_instructions_escaped
        )
    else:
        # Use standard prompt
        base_prompt = get_prompt_for_abstract(
            abstract_text, fulltext, kc_definitions_text, 
            format_instructions_escaped, rag_context
        )
    
    # 5. Enhance with causal reasoning instructions
    base_prompt_enhanced = enhance_causal_reasoning_prompt(base_prompt)
    
    # 6. Create LangChain prompt template
    prompt_template_with_format = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_ANALYST),  # Contains instructions
        ("human", """Title: {title}\n\nAbstract: {abstract}\n\nAnalyze this abstract against the 12 Key Characteristics. Return ONLY the raw JSON."""),
    ])
```

**What happens here**:
- LLM is initialized with specific model and temperature
- KC definitions are formatted as text
- Pydantic parser is created to validate JSON output
- Prompt is built with instructions and examples
- LangChain template is created for structured input/output

---

### Step 2: Invoke LLM and Get Response

**Location**: `app.py` lines 801-810

```python
    # 7. Create chain: prompt → LLM
    chain = prompt_template_with_format | llm
    
    # 8. Invoke LLM with abstract
    raw_response = chain.invoke({
        "title": title,
        "abstract": text_to_analyze  # Abstract or full-text
    })
    
    # 9. Extract response text
    response_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
    print(f"LLM Response preview: {response_text[:300]}...")
    
    # Example response_text might look like:
    # '{"kc1_status": "SUPPORTED", "kc2_status": "NOT_MENTIONED", ...}'
```

**What happens here**:
- LLM receives the prompt with abstract text
- LLM processes and generates JSON response
- Response is extracted as text string

---

### Step 3: Clean and Parse Response

**Location**: `app.py` lines 812-820

```python
    # 10. Clean response: Remove markdown code blocks if present
    cleaned_text = re.sub(r'```json\s*', '', response_text)
    cleaned_text = re.sub(r'```\s*', '', cleaned_text)
    cleaned_text = cleaned_text.strip()
    
    # Example: Removes ```json and ``` markers
    
    # 11. Try parsing with Pydantic (primary method)
    try:
        result = parser.parse(cleaned_text)
        # parser.parse() validates against KCAnalysis Pydantic model
        # Returns KCAnalysis object with all fields validated
```

**What happens here**:
- Markdown formatting is removed (```json blocks)
- Pydantic parser validates JSON structure
- If valid, returns `KCAnalysis` object with all KC statuses

---

### Step 4: Fallback Parsing (If Primary Fails)

**Location**: `app.py` lines 821-950

```python
    except Exception as parse_error:
        print(f"Pydantic parsing failed: {parse_error}")
        
        # 12. Fallback: Extract JSON from response using regex
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            json_data = json.loads(json_str)  # Parse JSON
            
            # 13. Fix causal_links format if needed
            if "causal_links" in json_data:
                fixed_causal_links = []
                for link in json_data["causal_links"]:
                    # Transform cause/effect → source/target
                    if "cause" in link or "effect" in link:
                        fixed_link = {
                            "source": link.get("cause", ""),
                            "target": link.get("effect", ""),
                            "evidence": link.get("evidence", ""),
                            "strength": link.get("strength", "MODERATE")
                        }
                        fixed_causal_links.append(fixed_link)
                json_data["causal_links"] = fixed_causal_links
            
            # 14. Ensure all required fields exist
            for i in range(1, 13):
                kc_key = f"kc{i}_status"
                if kc_key not in json_data:
                    json_data[kc_key] = "NOT_MENTIONED"  # Default
            
            # 15. Create KCAnalysis object from fixed JSON
            result = KCAnalysis(**json_data)
```

**What happens here**:
- If Pydantic parsing fails, regex extracts JSON
- JSON is parsed manually
- Format fixes are applied (e.g., cause/effect → source/target)
- Missing fields are filled with defaults
- KCAnalysis object is created

---

### Step 5: Extract KC Statuses

**Location**: `app.py` lines 950-1040

```python
    # 16. Convert Pydantic object to dictionary
    kc_dict = {}
    
    # Extract each KC status
    for i in range(1, 13):
        kc_key = f"KC{i}"
        status_key = f"kc{i}_status"
        
        # Get status from result object
        status = getattr(result, status_key, "NOT_MENTIONED")
        
        # Validate status is one of allowed values
        allowed_statuses = ["SUPPORTED", "NOT_MENTIONED", "REFUTED", 
                           "ASSOCIATED", "CAUSALLY_LINKED"]
        if status not in allowed_statuses:
            status = "NOT_MENTIONED"  # Default if invalid
        
        # Store in dictionary
        kc_dict[kc_key] = (status == "SUPPORTED" or 
                          status == "ASSOCIATED" or 
                          status == "CAUSALLY_LINKED")
        kc_dict[status_key] = status
    
    # 17. Extract other fields
    kc_dict["reasoning"] = result.reasoning or "No reasoning provided"
    kc_dict["causal_links"] = [
        {
            "source": link.source,
            "target": link.target,
            "evidence": link.evidence,
            "strength": link.strength
        }
        for link in result.causal_links
    ]
    kc_dict["evidence_quotes"] = result.evidence_quotes or {}
    kc_dict["dose_response"] = result.dose_response or []
```

**What happens here**:
- Each KC status is extracted from the Pydantic object
- Status is validated against allowed values
- Boolean flags are set (True if SUPPORTED/ASSOCIATED/CAUSALLY_LINKED)
- Causal links, evidence quotes, and dose-response are extracted

---

### Step 6: Final Output Format

**Location**: `app.py` lines 1040-1042

```python
    # 18. Return dictionary with all analysis results
    return kc_dict, current_prompt_hash
```

**Output format**:
```python
{
    "KC1": True,  # Boolean: is this KC supported?
    "kc1_status": "SUPPORTED",  # String: actual status
    "KC2": False,
    "kc2_status": "NOT_MENTIONED",
    # ... for all 12 KCs
    "reasoning": "Step-by-step reasoning...",
    "causal_links": [
        {
            "source": "KC1",
            "target": "KC5",
            "evidence": "Metabolism led to oxidative stress",
            "strength": "STRONG"
        }
    ],
    "evidence_quotes": {
        "KC1": ["Acetaminophen is metabolized to NAPQI"],
        "KC5": ["causes oxidative stress"]
    },
    "dose_response": ["50 mg/kg", "10-100 μM"]
}
```

---

## The Pydantic Model: Structure Validation

**Location**: `app.py` lines 279-310 (`KCAnalysis` class)

```python
class KCAnalysis(BaseModel):
    """Pydantic model that defines the expected JSON structure"""
    
    # Each KC has a status field
    kc1_status: str = Field(
        default="NOT_MENTIONED",
        description="KC1: Reactive/Bioactivation - Values: 'SUPPORTED', 'REFUTED', or 'NOT_MENTIONED'"
    )
    kc2_status: str = Field(
        default="NOT_MENTIONED",
        description="KC2: Cell Death - Values: 'SUPPORTED', 'ASSOCIATED', 'CAUSALLY_LINKED', 'REFUTED', or 'NOT_MENTIONED'"
    )
    # ... kc3_status through kc12_status
    
    # Other fields
    reasoning: str = Field(default="No reasoning provided")
    causal_links: List[CausalLink] = Field(default_factory=list)
    evidence_quotes: Dict[str, List[str]] = Field(default_factory=dict)
    dose_response: List[str] = Field(default_factory=list)
```

**What this does**:
- Defines the exact JSON structure the LLM must return
- Provides default values if fields are missing
- Validates data types (str, List, Dict)
- Generates format instructions for the LLM prompt

---

## The Prompt: What the LLM Actually Sees

**Location**: `app.py` lines 683-764 (fallback prompt) + `prompt_improvements.py` (enhanced prompts)

### Simplified Prompt Structure:

```python
SYSTEM_PROMPT = """### TASK
Analyze this abstract against 12 Key Characteristics (KCs) of liver toxicity.

### KEY CHARACTERISTICS DEFINITIONS
{kc_definitions}
# Example:
# KC1: Is reactive and/or is metabolized (bioactivated) to reactive moieties.
# KC2: Causes death (apoptosis and/or necrosis) of liver cells.
# ...

### INSTRUCTIONS
For EACH KC, follow this process:

1. SCAN: Identify all mentions related to this KC mechanism
2. EVALUATE: Determine if the text explicitly states the chemical causes this effect
3. QUOTE: Extract exact sentences that support your conclusion
4. LINK: If another KC causes this one, note the causal relationship
5. DECIDE: Assign status:
   - SUPPORTED: Text explicitly states chemical causes this effect
   - REFUTED: Text explicitly states chemical does NOT cause this effect
   - NOT_MENTIONED: Mechanism not discussed
   - ASSOCIATED: Chemical associated with effect, but causation not explicit
   - CAUSALLY_LINKED: Effect occurs but caused by another KC (indirect)

### EXAMPLES
[Few-shot examples showing correct decisions]

### JSON OUTPUT REQUIREMENTS
{format_instructions}
# Generated by Pydantic parser, tells LLM exact JSON structure needed
"""

HUMAN_PROMPT = """Title: {title}

Abstract: {abstract}

Analyze this abstract against the 12 Key Characteristics. Return ONLY the raw JSON."""
```

**What the LLM receives**:
1. Task description
2. All 12 KC definitions
3. Step-by-step instructions (SCAN → EVALUATE → QUOTE → LINK → DECIDE)
4. Examples showing correct decisions
5. JSON schema (from Pydantic)
6. The actual abstract text

---

## How Status Determination Actually Works

### The LLM's Internal Process (Not Directly Programmed)

The LLM doesn't execute code - it uses pattern matching and learned associations. However, the prompt guides it through these steps:

**1. SCAN (Keyword Matching)**:
```python
# The LLM looks for keywords related to each KC
# This is not explicitly coded, but the prompt instructs it to:
# "Identify all mentions related to this KC mechanism"

# Example for KC1 (Bioactivation):
# Keywords: "metabolism", "bioactivation", "reactive metabolite", "NAPQI", "CYP450"
# The LLM's training includes these associations
```

**2. EVALUATE (Causal Language Detection)**:
```python
# The LLM evaluates if explicit causal language exists
# Prompt instructs: "Determine if the text explicitly states the chemical causes this effect"

# Causal language patterns (learned from training):
# - "causes", "induces", "leads to" → SUPPORTED
# - "associated with", "correlated with" → ASSOCIATED
# - "no evidence of", "did not cause" → REFUTED
# - "metabolism led to..." → CAUSALLY_LINKED (indirect)
```

**3. QUOTE (Text Extraction)**:
```python
# The LLM extracts verbatim sentences
# Prompt instructs: "Extract exact sentences that support your conclusion"

# Programmatically, quotes are stored in:
result.evidence_quotes = {
    "KC1": ["Acetaminophen is metabolized to NAPQI"],
    "KC5": ["causes oxidative stress"]
}
```

**4. LINK (Causal Relationship Detection)**:
```python
# The LLM identifies relationships between KCs
# Prompt instructs: "If another KC causes this one, note the causal relationship"

# Programmatically extracted as:
result.causal_links = [
    CausalLink(
        source="KC1",
        target="KC5",
        evidence="Metabolism led to oxidative stress",
        strength="STRONG"
    )
]
```

**5. DECIDE (Status Assignment)**:
```python
# The LLM assigns status based on evaluation
# This is where the actual decision happens

# Programmatically extracted as:
result.kc1_status = "SUPPORTED"  # From LLM's JSON response
result.kc5_status = "CAUSALLY_LINKED"  # From LLM's JSON response
```

---

## Complete Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. INPUT: abstract_text, title, model_name                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. BUILD PROMPT                                            │
│    - Format KC definitions                                  │
│    - Create Pydantic parser                                 │
│    - Build prompt with instructions                         │
│    - Add examples                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. INVOKE LLM                                              │
│    chain = prompt_template | llm                           │
│    response = chain.invoke({"title": title,                 │
│                            "abstract": abstract_text})      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EXTRACT RESPONSE                                        │
│    response_text = response.content                        │
│    # Example: '{"kc1_status": "SUPPORTED", ...}'            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. CLEAN RESPONSE                                          │
│    cleaned_text = re.sub(r'```json', '', response_text)    │
│    cleaned_text = cleaned_text.strip()                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. PARSE WITH PYDANTIC (Primary Method)                    │
│    try:                                                     │
│        result = parser.parse(cleaned_text)                  │
│        # Validates structure, returns KCAnalysis object      │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    SUCCESS                  FAILURE
         │                       │
         ▼                       ▼
┌──────────────────┐  ┌──────────────────────────────┐
│ 7a. EXTRACT      │  │ 7b. FALLBACK PARSING        │
│    STATUSES      │  │    - Extract JSON with regex│
│                  │  │    - Fix format issues      │
│ for i in 1..12:  │  │    - Fill missing fields    │
│   status =       │  │    - Create KCAnalysis      │
│   result.kc{i}   │  │                              │
│   _status        │  │                              │
└────────┬─────────┘  └──────────────┬───────────────┘
         │                           │
         └───────────┬───────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. VALIDATE AND FORMAT                                     │
│    - Check status is in allowed values                     │
│    - Set boolean flags (KC1: True if SUPPORTED)            │
│    - Extract causal_links, evidence_quotes, etc.          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. RETURN DICTIONARY                                       │
│    return {                                                 │
│        "KC1": True,                                        │
│        "kc1_status": "SUPPORTED",                          │
│        "reasoning": "...",                                  │
│        "causal_links": [...],                               │
│        ...                                                  │
│    }                                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Code Functions

### 1. Main Analysis Function
```python
# Location: app.py line 541
def analyze_abstract_with_llm(
    abstract_text: str,
    title: str,
    model_name: str = "llama3.1",
    ...
) -> Tuple[Dict, str]:
    """
    Orchestrates the entire process
    Returns: (kc_dict, prompt_hash)
    """
```

### 2. Prompt Building
```python
# Location: prompt_improvements.py
def get_enhanced_prompt_with_synonyms(
    kc_definitions_text: str,
    format_instructions: str
) -> str:
    """
    Builds enhanced prompt with synonym recognition
    """
```

### 3. Response Parsing
```python
# Location: app.py line 819
parser = PydanticOutputParser(pydantic_object=KCAnalysis)
result = parser.parse(cleaned_text)
```

### 4. Status Extraction
```python
# Location: app.py lines 950-1000
for i in range(1, 13):
    status_key = f"kc{i}_status"
    status = getattr(result, status_key, "NOT_MENTIONED")
    # Validate and store
```

---

## Example: Complete Execution Trace

### Input:
```python
abstract_text = "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine that depletes glutathione and causes oxidative stress."
title = "Mechanisms of Acetaminophen Toxicity"
model_name = "llama3.2"
```

### Step 1: Prompt Construction
```python
# KC definitions formatted:
kc_definitions = """
KC1: Is reactive and/or is metabolized (bioactivated) to reactive moieties.
KC2: Causes death (apoptosis and/or necrosis) of liver cells.
...
"""

# Prompt includes:
# - Task description
# - KC definitions
# - Instructions (SCAN → EVALUATE → QUOTE → LINK → DECIDE)
# - Examples
# - JSON schema
```

### Step 2: LLM Invocation
```python
response = chain.invoke({
    "title": "Mechanisms of Acetaminophen Toxicity",
    "abstract": "Acetaminophen is metabolized by CYP2E1 to NAPQI..."
})
```

### Step 3: LLM Response (Raw)
```json
{
  "kc1_status": "SUPPORTED",
  "kc2_status": "NOT_MENTIONED",
  "kc5_status": "CAUSALLY_LINKED",
  "kc7_status": "NOT_MENTIONED",
  ...
  "reasoning": "KC1 is SUPPORTED because text explicitly states 'is metabolized to NAPQI'...",
  "causal_links": [
    {
      "source": "KC1",
      "target": "KC5",
      "evidence": "depletes glutathione and causes oxidative stress",
      "strength": "STRONG"
    }
  ],
  "evidence_quotes": {
    "KC1": ["Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"]
  }
}
```

### Step 4: Parsing
```python
result = parser.parse(response_text)
# Returns KCAnalysis object:
# result.kc1_status = "SUPPORTED"
# result.kc5_status = "CAUSALLY_LINKED"
# result.causal_links = [CausalLink(...)]
```

### Step 5: Status Extraction
```python
kc_dict = {}
kc_dict["KC1"] = True  # Because status == "SUPPORTED"
kc_dict["kc1_status"] = "SUPPORTED"
kc_dict["KC5"] = True  # Because status == "CAUSALLY_LINKED"
kc_dict["kc5_status"] = "CAUSALLY_LINKED"
```

### Step 6: Output
```python
return {
    "KC1": True,
    "kc1_status": "SUPPORTED",
    "KC2": False,
    "kc2_status": "NOT_MENTIONED",
    "KC5": True,
    "kc5_status": "CAUSALLY_LINKED",
    ...
    "reasoning": "...",
    "causal_links": [...],
    "evidence_quotes": {...}
}
```

---

## Summary

**Programmatic Implementation**:

1. **Prompt Construction**: Code builds prompt with KC definitions, instructions, examples
2. **LLM Invocation**: LangChain sends prompt to LLM, receives JSON response
3. **Response Parsing**: Pydantic validates and parses JSON into structured object
4. **Status Extraction**: Code extracts each `kc{i}_status` field from parsed object
5. **Validation**: Code checks status is in allowed values, sets defaults if missing
6. **Formatting**: Code converts to dictionary format with boolean flags

**The LLM's Role**:
- The LLM doesn't execute code - it uses learned patterns
- The prompt guides it through SCAN → EVALUATE → QUOTE → LINK → DECIDE
- The LLM generates JSON matching the Pydantic schema
- The code extracts and validates the LLM's decisions

**Key Code Locations**:
- Main function: `app.py` lines 541-1042
- Prompt building: `prompt_improvements.py`
- Pydantic model: `app.py` lines 279-310
- Parsing logic: `app.py` lines 812-950
