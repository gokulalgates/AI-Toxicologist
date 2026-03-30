# Evidence Quotes and Causal Pathways Extraction

## Overview
The AI Toxicologist system extracts two types of evidence from scientific abstracts:
1. **Evidence Quotes**: Exact sentences from the text that support each Key Characteristic
2. **Causal Pathways**: Mechanistic relationships showing how one KC leads to another

## 1. Evidence Quotes

### What Are Evidence Quotes?
Evidence quotes are **verbatim sentences** from the abstract that directly support the presence of a Key Characteristic. They provide traceability - you can see exactly what text led to the conclusion.

### How They're Extracted

#### Step 1: LLM Analysis
The LLM analyzes the abstract and identifies which KCs are supported. For each supported KC, it extracts 1-2 exact sentences.

#### Step 2: Storage Format
Evidence quotes are stored as a dictionary:
```python
evidence_quotes = {
    "KC1": ["Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"],
    "KC5": ["increased ROS levels and oxidative stress in hepatocytes", 
            "glutathione depletion resulted in oxidative damage"],
    "KC2": ["hepatocellular necrosis was observed"]
}
```

#### Step 3: Requirements
- **Verbatim**: Quotes must be exact sentences from the abstract (not paraphrased)
- **Relevant**: Must directly support the KC conclusion
- **Quantity**: 1-2 quotes per KC (enough to support, not overwhelming)

### Example

**Abstract Text:**
> "Acetaminophen overdose causes hepatocellular necrosis. The drug is metabolized by CYP2E1 to NAPQI, a reactive metabolite that depletes glutathione. This leads to increased ROS levels and oxidative stress in hepatocytes."

**Extracted Evidence Quotes:**
```json
{
  "KC1": ["The drug is metabolized by CYP2E1 to NAPQI, a reactive metabolite"],
  "KC2": ["Acetaminophen overdose causes hepatocellular necrosis"],
  "KC5": ["increased ROS levels and oxidative stress in hepatocytes"]
}
```

### Why Evidence Quotes Matter

1. **Transparency**: Shows exactly what evidence supports each conclusion
2. **Verification**: Allows reviewers to check if the extraction is correct
3. **Traceability**: Links conclusions back to source text
4. **Quality Control**: Helps identify if LLM misunderstood the text

## 2. Causal Pathways

### What Are Causal Pathways?
Causal pathways show **mechanistic relationships** between Key Characteristics - how one biological mechanism leads to or causes another.

### Format
Each causal link has:
- **Source KC**: The upstream mechanism (cause)
- **Target KC**: The downstream mechanism (effect)
- **Evidence**: The exact text supporting the causal relationship
- **Strength**: How strong the causal link is (STRONG, MODERATE, WEAK)

### Example Causal Link
```json
{
  "source": "KC1",
  "target": "KC5",
  "evidence": "Metabolism of the compound led to glutathione depletion, resulting in increased ROS levels",
  "strength": "STRONG"
}
```

This means: **KC1 (Reactive/Bioactivation) → KC5 (Oxidative Stress)**

### How They're Extracted

#### Step 1: LLM Identifies Causal Language
The LLM looks for explicit causal statements in the text:
- "led to", "causes", "results in", "triggers", "induces"
- "Metabolism...led to...oxidative stress"
- "Reactive metabolites...caused...mitochondrial dysfunction"

#### Step 2: Extract Only Explicit Links
**CRITICAL RULE**: Only extract links that are **explicitly stated** in the text. Do NOT infer connections.

**✅ GOOD (Explicit):**
- "Bioactivation via CYP450 led to oxidative stress"
- "Mitochondrial dysfunction caused cell death"
- "Metabolism resulted in glutathione depletion"

**❌ BAD (Inferred):**
- Paper mentions KC1 and KC5 separately → Don't assume KC1→KC5
- Paper discusses mechanisms but doesn't link them → Don't infer links

#### Step 3: Assess Strength
- **STRONG**: Directly stated causal relationship
  - Example: "Metabolism led to oxidative stress"
  
- **MODERATE**: Implied but clear causal relationship
  - Example: "Following bioactivation, oxidative stress was observed"
  
- **WEAK**: Tenuous connection
  - Example: "Both mechanisms were observed" (not really causal)

#### Step 4: Store with Evidence
Each causal link includes the exact quote supporting it:
```json
{
  "source": "KC1",
  "target": "KC5",
  "evidence": "Metabolism of acetaminophen by CYP2E1 generated NAPQI, which depleted glutathione and led to increased ROS levels",
  "strength": "STRONG"
}
```

### Example: Multi-Step Causal Chain

**Abstract:**
> "The chemical undergoes bioactivation via CYP450, generating reactive metabolites that deplete glutathione. This leads to mitochondrial dysfunction and ultimately triggers apoptosis in liver cells."

**Extracted Causal Links:**
```json
[
  {
    "source": "KC1",
    "target": "KC5",
    "evidence": "bioactivation...generating reactive metabolites that deplete glutathione",
    "strength": "STRONG"
  },
  {
    "source": "KC5",
    "target": "KC7",
    "evidence": "glutathione depletion...leads to mitochondrial dysfunction",
    "strength": "STRONG"
  },
  {
    "source": "KC7",
    "target": "KC2",
    "evidence": "mitochondrial dysfunction...ultimately triggers apoptosis",
    "strength": "STRONG"
  }
]
```

**Causal Chain**: KC1 → KC5 → KC7 → KC2
(Bioactivation → Oxidative Stress → Mitochondrial Dysfunction → Cell Death)

## How They're Used

### 1. Evidence Quotes Usage

#### In Evidence Matrix
- Shows which papers support which KCs
- Provides traceability for each conclusion

#### In Evidence Profiles
- Included in certainty grading summaries
- Shows reviewers what evidence was found

#### In Study Records
- Saved with each analysis for reproducibility
- Allows verification of conclusions

### 2. Causal Pathways Usage

#### In Network Visualization
- Creates directed graph showing mechanistic relationships
- Edge weights = frequency of causal links across papers
- Color-coded by pathway role (upstream/intermediate/downstream)

#### In Pathway Analysis
- Identifies common mechanistic pathways
- Shows which KCs are upstream (triggers) vs downstream (effects)
- Helps understand toxicological mechanisms

#### In Risk-of-Bias Weighting
- High-quality studies (low RoB) contribute more to pathway strength
- Low-quality studies (high RoB) are down-weighted
- Ensures pathways are based on reliable evidence

## Technical Implementation

### Data Structure

```python
# Evidence Quotes
evidence_quotes = {
    "KC1": ["quote1", "quote2"],
    "KC5": ["quote3"]
}

# Causal Links
causal_links = [
    {
        "source": "KC1",
        "target": "KC5",
        "evidence": "exact quote from text",
        "strength": "STRONG"  # or "MODERATE" or "WEAK"
    }
]
```

### Extraction Process

1. **LLM Prompt**: Instructs LLM to extract quotes and causal links
2. **JSON Parsing**: LLM returns structured JSON with both
3. **Validation**: Causal links are validated against original text
4. **Storage**: Saved in analysis results and study records

### Validation

Causal links are validated to ensure:
- Source and target KCs are valid (KC1-KC12)
- Evidence quote actually appears in the original text
- Strength assessment is reasonable

## Examples from Real Analysis

### Example 1: Acetaminophen

**Evidence Quotes:**
- KC1: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"
- KC5: "NAPQI depletes glutathione, leading to increased ROS levels"
- KC2: "Hepatocellular necrosis was observed in overdose cases"

**Causal Links:**
- KC1 → KC5: "Metabolism to NAPQI depletes glutathione, causing oxidative stress"
- KC5 → KC2: "Oxidative stress leads to hepatocellular necrosis"

### Example 2: Carbon Tetrachloride

**Evidence Quotes:**
- KC1: "CCl4 undergoes bioactivation by CYP2E1 to trichloromethyl radical"
- KC5: "Reactive metabolites cause lipid peroxidation and oxidative stress"
- KC11: "Chronic exposure leads to liver fibrosis"

**Causal Links:**
- KC1 → KC5: "Bioactivation generates reactive radicals that cause oxidative stress"
- KC5 → KC11: "Oxidative stress and repeated injury lead to fibrosis"

## Summary

**Evidence Quotes:**
- Verbatim sentences supporting each KC
- Provides transparency and traceability
- Stored per KC in a dictionary

**Causal Pathways:**
- Mechanistic relationships between KCs
- Only explicit links (not inferred)
- Include strength assessment and evidence
- Used to build pathway networks

Both features make the analysis **transparent, reproducible, and scientifically rigorous** by showing exactly what evidence supports each conclusion and how mechanisms are connected.
