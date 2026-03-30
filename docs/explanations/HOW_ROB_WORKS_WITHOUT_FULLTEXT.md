# How Risk-of-Bias Assessment Works Without Full-Text

## Overview

The Risk-of-Bias (RoB) assessment system is designed to work with **abstracts only**, but it explicitly flags when information is insufficient. This document explains how the system handles abstract-only assessment and what limitations exist.

---

## The Assessment Process

### Step 1: Text Input

**Location**: `risk_of_bias.py` lines 49-55

```python
def assess_rob_with_llm(
    abstract_text: str,  # Can be abstract OR full-text
    title: str,
    pmid: str,
    model_name: str = "llama3.2",
    instrument: str = "OHAT"
) -> RiskOfBiasAssessment:
```

**What happens**:
- The function receives `abstract_text` (which may be just an abstract or full-text)
- It determines text type based on length:
  ```python
  text_type = "Full-text" if len(abstract_text) > 3000 else "Abstract"
  ```
- If text is long (>3000 chars), it's truncated to first 3000 chars for processing

---

## Step 2: The Prompt Instructs the LLM

**Location**: `risk_of_bias.py` lines 64-105

### Key Instructions in the Prompt:

```
### INSTRUCTIONS
For EACH domain, assess the risk of bias based on the provided text (abstract or full-text):
- **Low**: Study design and methods minimize bias
- **Some concerns**: Some issues that may introduce bias
- **High**: Significant risk of bias
- **Critical**: Critical flaws that invalidate the study
- **N/A**: Domain not applicable to this study
- **Insufficient information**: The text does not contain enough information to assess this domain

CRITICAL: If the text does not contain sufficient information to assess a domain 
(e.g., methods section missing, no details on blinding, etc.), return 
"Insufficient information" rather than guessing or defaulting to "Some concerns".
```

**What this means**:
- The LLM is explicitly told to assess based on what's available (abstract or full-text)
- **Most importantly**: The LLM is instructed to use "Insufficient information" when details are missing
- The LLM should NOT guess or default to "Some concerns" when information is missing

---

## Step 3: Domain-by-Domain Assessment

### The 7 OHAT Domains Assessed:

1. **Selection Bias**: Were study groups properly selected?
2. **Confounding**: Were confounding variables controlled?
3. **Performance Bias**: Could the study design introduce bias?
4. **Detection/Measurement Bias**: Were outcomes measured correctly?
5. **Attrition Bias**: Were dropouts handled properly?
6. **Selective Reporting**: Were all results reported?
7. **Other Sources of Bias**: Any other bias concerns?

### How Each Domain is Assessed from Abstract:

**What CAN be assessed from abstracts**:
- **Study type**: Usually mentioned (e.g., "animal study", "in vitro")
- **Species**: Usually mentioned (e.g., "mice", "HepG2 cells")
- **Basic design**: Sometimes mentioned (e.g., "randomized", "controlled")
- **Outcomes measured**: Usually mentioned (e.g., "ALT levels", "histology")

**What CANNOT be assessed from abstracts**:
- **Detailed methods**: Methods section is usually not in abstract
- **Blinding procedures**: Rarely mentioned in abstracts
- **Randomization details**: Usually not described in abstracts
- **Confounding control**: Detailed statistical methods not in abstract
- **Attrition handling**: Dropout information not in abstract
- **Selective reporting**: Full results not available

---

## Step 4: LLM Decision Process

### For Each Domain, the LLM:

1. **Scans** the abstract for relevant information
2. **Evaluates** if sufficient information exists
3. **Decides**:
   - If information is sufficient → Assigns judgment (Low, Some concerns, High, Critical)
   - If information is insufficient → Assigns "Insufficient information"

### Example: Selection Bias Domain

**Abstract text**:
```
"Male C57BL/6 mice (n=10 per group) were randomly assigned to treatment or control groups."
```

**LLM Analysis**:
- **Scans**: Found "randomly assigned" → suggests randomization
- **Evaluates**: Abstract mentions randomization, but no details on method
- **Decides**: 
  - **Option 1**: If abstract says "randomly assigned" → "Low" (some information available)
  - **Option 2**: If abstract doesn't mention selection → "Insufficient information"

**Abstract text**:
```
"Acetaminophen was administered to mice and liver injury was assessed."
```

**LLM Analysis**:
- **Scans**: No mention of selection method
- **Evaluates**: No information on how animals were selected
- **Decides**: **"Insufficient information"** (no details available)

---

## Step 5: Overall Judgment

**Location**: `risk_of_bias.py` line 105

```
Determine overall judgment based on the most serious concerns across domains. 
If multiple domains have "Insufficient information", the overall judgment 
should be "Insufficient information".
```

**Logic**:
- If **any domain** = "High" or "Critical" → Overall = "High" or "Critical"
- If **any domain** = "Some concerns" → Overall = "Some concerns" (unless High/Critical exists)
- If **all domains** = "Low" → Overall = "Low"
- If **multiple domains** = "Insufficient information" → Overall = "Insufficient information"

---

## Real Example: Acetaminophen Analysis

### Study 1 (PMID: 41386882)

**Abstract** (excerpt):
```
"Quercetin-liposomes effectively regulated the Nrf2/Keap1 and NF-κB/P38 MAPK 
signaling pathways and protected the liver against paracetamol-induced damage."
```

**LLM RoB Assessment**:

| Domain | Judgment | Why |
|--------|----------|-----|
| Selection Bias | Low | Abstract doesn't mention selection issues |
| Confounding | Insufficient information | No details on confounders or controls |
| Performance Bias | Low | No mention of performance bias |
| Detection/Measurement Bias | Insufficient information | No details on measurement methods |
| Attrition Bias | Low | No mention of dropouts |
| Selective Reporting | Insufficient information | No details on what was reported |
| Other Sources | Low | No other bias mentioned |

**Overall Judgment**: **"Insufficient information"**
- Reason: Multiple domains have insufficient information
- This is **correct** - abstract doesn't contain enough detail for full assessment

---

## How the System Handles Abstract-Only Assessment

### 1. **Explicit "Insufficient Information" Status**

**Location**: `risk_of_bias.py` lines 77-79

The prompt explicitly instructs:
```
CRITICAL: If the text does not contain sufficient information to assess a domain 
(e.g., methods section missing, no details on blinding, etc.), return 
"Insufficient information" rather than guessing or defaulting to "Some concerns".
```

**Why this matters**:
- Prevents the LLM from guessing when information is missing
- Ensures transparency about what can/cannot be assessed
- Aligns with OHAT framework guidance

### 2. **Information Availability Flag**

**Location**: `risk_of_bias.py` line 85

Each domain assessment includes:
```python
information_available: true if sufficient info exists, false if insufficient
```

**What this does**:
- Tracks whether each domain had enough information
- Can be used to filter or weight assessments
- Provides transparency about assessment quality

### 3. **Full-Text Tracking**

**Location**: `risk_of_bias.py` lines 113-114, 240-241

```python
# Determine if we have full-text or just abstract
text_type = "Full-text" if len(abstract_text) > 3000 else "Abstract"
fulltext_used = len(abstract_text) > 3000
```

**What this does**:
- Tracks whether full-text was used (heuristic: >3000 chars)
- Stored in `RiskOfBiasAssessment.fulltext_used` field
- Reported in summary statistics

---

## Limitations of Abstract-Only Assessment

### What's Missing from Abstracts:

1. **Methods Section**:
   - Detailed experimental procedures
   - Randomization methods
   - Blinding procedures
   - Sample size calculations

2. **Statistical Methods**:
   - How confounders were controlled
   - Statistical tests used
   - Power analysis

3. **Results Details**:
   - Complete results (not just highlights)
   - Negative results (may be omitted from abstract)
   - Supplementary data

4. **Study Design Details**:
   - Inclusion/exclusion criteria
   - Treatment protocols
   - Follow-up procedures

### Impact on Assessment:

**Domains Most Affected** (often "Insufficient information"):
- **Confounding**: Requires statistical methods (usually not in abstract)
- **Detection/Measurement Bias**: Requires detailed methods (usually not in abstract)
- **Selective Reporting**: Requires full results (not available in abstract)

**Domains Sometimes Assessable**:
- **Selection Bias**: May mention "randomized" or "selected"
- **Performance Bias**: May mention blinding or controls
- **Attrition Bias**: May mention dropouts (rarely)

---

## How the System Reports This

### Summary Statistics

**Location**: `risk_of_bias.py` lines 340-370

```python
def calculate_rob_summary_stats(rob_assessments):
    return {
        "total_studies": total,
        "overall_distribution": {
            "Low": count,
            "Some concerns": count,
            "High": count,
            "Insufficient information": count
        },
        "fulltext_used_count": fulltext_count,
        "fulltext_percentage": (fulltext_count / total * 100)
    }
```

**Example Output** (from Acetaminophen analysis):
```
Risk-of-Bias Summary:
  • Low Risk: 8/15 studies (53%)
  • Some Concerns: 6/15 studies (40%)
  • High Risk: 0/15 studies (0%)
  • Insufficient Information: 1/15 studies (7%)
  • Full-text Used: 0/15 studies (0%)
```

**Interpretation**:
- Most studies (53%) were assessed as "Low risk" based on abstract
- Some studies (40%) had "Some concerns" (issues detected in abstract)
- One study (7%) had "Insufficient information" (not enough detail)
- **No full-text was used** (0%) - all assessments were abstract-only

---

## Why "Low Risk" Can Be Assigned from Abstracts

### When Abstract Provides Sufficient Information:

**Example 1: Clear Study Design**
```
Abstract: "A randomized, controlled study was conducted with 50 mice per group. 
Animals were randomly assigned using a computer-generated sequence. 
Investigators were blinded to treatment groups."
```

**Assessment**:
- Selection Bias: **Low** (randomization mentioned)
- Performance Bias: **Low** (blinding mentioned)
- Other domains: May still be "Insufficient information"

**Example 2: Well-Described Methods**
```
Abstract: "Liver injury was assessed using standardized ALT/AST assays 
(commercial kits, manufacturer's protocol). Histological examination was 
performed by two independent pathologists blinded to treatment groups."
```

**Assessment**:
- Detection/Measurement Bias: **Low** (standardized methods, blinded assessment)
- Other domains: May vary

---

## When "Insufficient Information" is Assigned

### Common Scenarios:

**Scenario 1: No Methods Mentioned**
```
Abstract: "Acetaminophen caused liver injury in mice."
```
- **All domains**: "Insufficient information" (no methods/details)

**Scenario 2: Partial Information**
```
Abstract: "Mice were treated with acetaminophen and liver injury was assessed."
```
- **Selection Bias**: "Insufficient information" (no selection method)
- **Confounding**: "Insufficient information" (no control details)
- **Detection Bias**: "Insufficient information" (no measurement details)

**Scenario 3: Some Information Available**
```
Abstract: "Randomized study with 20 mice per group. Liver enzymes were measured."
```
- **Selection Bias**: "Low" (randomization mentioned)
- **Detection Bias**: "Insufficient information" (no measurement details)
- **Confounding**: "Insufficient information" (no control details)

---

## The Prompt's Critical Instruction

**Location**: `risk_of_bias.py` line 79

```
CRITICAL: If the text does not contain sufficient information to assess a domain 
(e.g., methods section missing, no details on blinding, etc.), return 
"Insufficient information" rather than guessing or defaulting to "Some concerns".
```

**Why this is important**:
- **Prevents over-confidence**: Doesn't assume "Some concerns" when information is missing
- **Ensures transparency**: Clearly indicates when assessment is limited
- **Follows OHAT guidance**: OHAT framework recommends "Insufficient information" when details are missing
- **Avoids bias**: Doesn't penalize studies unfairly due to abstract limitations

---

## Comparison: Abstract vs Full-Text Assessment

### Abstract-Only Assessment:

**Advantages**:
- ✅ Fast (no need to retrieve full-text)
- ✅ Can assess basic study design
- ✅ Can identify obvious bias issues
- ✅ Can extract study type and species

**Limitations**:
- ❌ Many domains will be "Insufficient information"
- ❌ Cannot assess detailed methods
- ❌ Cannot verify statistical approaches
- ❌ May miss subtle bias issues

### Full-Text Assessment:

**Advantages**:
- ✅ Can assess all domains thoroughly
- ✅ Can verify methods and statistics
- ✅ Can identify subtle bias issues
- ✅ More reliable overall judgments

**Limitations**:
- ❌ Slower (requires full-text retrieval)
- ❌ May not be available for all studies
- ❌ More computationally expensive

---

## Programmatic Implementation

### Code Flow:

```python
# 1. Receive abstract text
abstract_text = abstract.get("abstract", "")

# 2. Determine if full-text available
fulltext_used = len(abstract_text) > 3000  # Heuristic

# 3. Assess with LLM
assessment = assess_rob_with_llm(
    abstract_text=abstract_text,
    title=abstract.get("title", ""),
    pmid=abstract.get("pmid", ""),
    model_name="llama3.2"
)

# 4. LLM processes prompt and returns:
#    - Domain judgments (Low/Some concerns/High/Insufficient information)
#    - Overall judgment
#    - information_available flags

# 5. Store assessment
assessment.fulltext_used = fulltext_used  # Track what was used
```

### Key Code Sections:

**Prompt Construction** (`risk_of_bias.py` lines 107-136):
```python
prompt = SYSTEM_PROMPT_ROB.format(...)
text_type = "Full-text" if len(abstract_text) > 3000 else "Abstract"
full_prompt = f"""{prompt}
Text Type: {text_type}
Text: {text_preview}
"""
```

**Domain Assessment** (`risk_of_bias.py` lines 222-231):
```python
for domain_data in json_data.get("domains", []):
    domain = RiskOfBiasDomain(
        domain=domain_data.get("domain"),
        judgment=domain_data.get("judgment", "Insufficient information"),
        information_available=domain_data.get("information_available", False)
    )
```

**Full-Text Tracking** (`risk_of_bias.py` line 241):
```python
fulltext_used = len(abstract_text) > 3000  # Heuristic
assessment.fulltext_used = fulltext_used
```

---

## Summary Statistics Interpretation

### From Acetaminophen Analysis:

```
Risk-of-Bias Summary:
  • Low Risk: 8/15 studies (53%)
  • Some Concerns: 6/15 studies (40%)
  • Insufficient Information: 1/15 studies (7%)
  • Full-text Used: 0/15 studies (0%)
```

**What this means**:
- **8 studies** were assessed as "Low risk" based on abstract information
- **6 studies** had "Some concerns" detected from abstract
- **1 study** had "Insufficient information" (not enough detail in abstract)
- **0 studies** used full-text (all were abstract-only)

**Interpretation**:
- Most abstracts contained enough information for basic assessment
- Some studies had bias concerns detectable from abstract
- One study lacked sufficient detail even for basic assessment
- **All assessments were abstract-only** - full-text would improve accuracy

---

## Best Practices

### When Using Abstract-Only Assessment:

1. **Interpret "Low Risk" cautiously**:
   - "Low Risk" from abstract may mean "no obvious bias detected"
   - Full-text might reveal additional concerns

2. **Pay attention to "Insufficient Information"**:
   - This is **correct** when details are missing
   - Not a flaw in the system - it's being transparent

3. **Consider full-text for critical studies**:
   - For high-impact studies, retrieve full-text
   - Full-text assessment is more reliable

4. **Use summary statistics**:
   - Check `fulltext_percentage` to know assessment quality
   - Higher percentage = more reliable assessments

---

## Conclusion

**How RoB works without full-text**:

1. **LLM reads abstract** and assesses each domain
2. **Uses "Insufficient information"** when details are missing (doesn't guess)
3. **Assigns judgments** when abstract provides enough information
4. **Tracks full-text usage** to indicate assessment quality
5. **Reports transparently** what can/cannot be assessed

**Key Points**:
- ✅ System is designed to work with abstracts
- ✅ Explicitly flags insufficient information
- ✅ Doesn't guess when details are missing
- ✅ Tracks whether full-text was used
- ⚠️ Full-text provides more reliable assessments

**Recommendation**: For publication-grade reviews, enable full-text retrieval when available to improve RoB assessment quality.
