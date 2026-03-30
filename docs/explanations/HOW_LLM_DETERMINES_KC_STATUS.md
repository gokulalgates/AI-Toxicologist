# How the LLM Determines Each KC Status: Detailed Explanation

## Overview

The Large Language Model (LLM) determines the status of each Key Characteristic (KC) by reading the abstract text and following a structured decision process. This document explains exactly how each status (SUPPORTED, NOT_MENTIONED, REFUTED, ASSOCIATED, CAUSALLY_LINKED) is determined.

---

## The Decision Process

### Step 1: The LLM Receives Instructions

The LLM is given:
1. **The abstract text** (and optionally full-text)
2. **Definitions of all 12 Key Characteristics**
3. **Detailed instructions** on how to assess each KC
4. **Examples** showing how to make decisions

### Step 2: For Each KC, the LLM Follows This Chain

```
1. SCAN → 2. EVALUATE → 3. QUOTE → 4. LINK → 5. DECIDE
```

**Detailed Steps**:

1. **SCAN**: Identify all mentions related to this KC mechanism in the text
   - Looks for keywords, phrases, and concepts related to the KC
   - Example for KC1: "metabolism", "bioactivation", "reactive metabolite", "NAPQI", "CYP450"

2. **EVALUATE**: Determine if the text explicitly states the chemical causes this effect
   - Checks if there's a causal relationship (chemical → effect)
   - Distinguishes between correlation and causation
   - Looks for explicit statements vs. implicit mentions

3. **QUOTE**: Extract the exact sentence(s) that support the conclusion
   - Finds verbatim text from the abstract
   - Stores quotes for evidence

4. **LINK**: If another KC is mentioned as causing this one, note the causal relationship
   - Identifies mechanistic pathways
   - Example: "Bioactivation (KC1) led to oxidative stress (KC5)"

5. **DECIDE**: Assign status based on the evaluation

---

## How Each Status is Determined

### Status 1: SUPPORTED

**Definition**: The text explicitly states the chemical causes/induces this effect.

**Criteria**:
- ✅ The text contains explicit causal language:
  - "causes", "induces", "leads to", "results in", "triggers"
  - "is metabolized to", "undergoes bioactivation"
  - "depletes", "disrupts", "activates"
- ✅ The chemical is the subject (the cause)
- ✅ The KC mechanism is the object (the effect)
- ✅ There is a direct causal relationship stated

**Examples**:

**Example 1: KC1 (Bioactivation) - SUPPORTED**
```
Abstract: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine that depletes glutathione."
```
**Why SUPPORTED**:
- Explicitly states: "is metabolized to NAPQI"
- NAPQI is a reactive metabolite (matches KC1 definition)
- Direct causal statement

**Example 2: KC5 (Oxidative Stress) - SUPPORTED**
```
Abstract: "The compound caused increased ROS levels and oxidative stress in hepatocytes."
```
**Why SUPPORTED**:
- Explicitly states: "caused... oxidative stress"
- Direct causal relationship
- Chemical → oxidative stress

**Example 3: KC7 (Mitochondrial Dysfunction) - SUPPORTED**
```
Abstract: "Treatment resulted in mitochondrial swelling and decreased ATP production."
```
**Why SUPPORTED**:
- "resulted in" = causal language
- "mitochondrial swelling" = mitochondrial dysfunction
- Direct statement

**Counter-Example (NOT SUPPORTED)**:
```
Abstract: "Oxidative stress was observed in the liver."
```
**Why NOT SUPPORTED**:
- Doesn't explicitly state the chemical caused it
- Could be from other causes
- Missing causal link

---

### Status 2: NOT_MENTIONED

**Definition**: The text does not discuss this mechanism at all.

**Criteria**:
- ❌ No keywords related to the KC are found
- ❌ No concepts related to the KC are mentioned
- ❌ The mechanism is completely absent from the text

**Examples**:

**Example: KC4 (Transport Disruption) - NOT_MENTIONED**
```
Abstract: "Acetaminophen caused oxidative stress and mitochondrial dysfunction, leading to cell death."
```
**Why NOT_MENTIONED**:
- No mention of transport, bile, transporters, or transport disruption
- Text focuses on other mechanisms
- KC4 is not discussed

**Example: KC10 (Cytoskeleton Disruption) - NOT_MENTIONED**
```
Abstract: "The study examined oxidative stress and apoptosis in hepatocytes."
```
**Why NOT_MENTIONED**:
- No mention of cytoskeleton, actin, microtubules, or cell structure
- Mechanism not discussed

---

### Status 3: REFUTED

**Definition**: The text explicitly states the chemical DOES NOT cause this effect.

**Criteria**:
- ✅ Contains explicit negation:
  - "no evidence of", "did not cause", "was not observed"
  - "absence of", "lack of", "no signs of"
- ✅ The chemical is tested for this effect
- ✅ The effect is explicitly stated to be absent

**Examples**:

**Example: KC11 (Liver Fibrosis) - REFUTED**
```
Abstract: "Histological examination revealed hepatocellular necrosis but no evidence of fibrosis was observed after 28 days of treatment."
```
**Why REFUTED**:
- Explicitly states: "no evidence of fibrosis"
- Direct negation
- Effect was looked for but not found

**Example: KC9 (Cholestasis) - REFUTED**
```
Abstract: "Liver function tests showed elevated ALT and AST, but bile flow was not impaired."
```
**Why REFUTED**:
- "bile flow was not impaired" = no cholestasis
- Explicit negation

**Counter-Example (NOT REFUTED, just NOT_MENTIONED)**:
```
Abstract: "The study examined oxidative stress in hepatocytes."
```
**Why NOT REFUTED**:
- Doesn't mention fibrosis at all
- Not tested for, so can't be refuted
- Should be NOT_MENTIONED instead

---

### Status 4: ASSOCIATED

**Definition**: The chemical is associated with this effect, but causation is not explicitly stated (correlation, not explicit causation).

**Criteria**:
- ⚠️ The effect is mentioned in relation to the chemical
- ⚠️ But no explicit causal language is used
- ⚠️ Correlation is implied but not stated
- ⚠️ Weaker evidence than SUPPORTED

**Examples**:

**Example: KC2 (Cell Death) - ASSOCIATED**
```
Abstract: "Following treatment, increased apoptosis was observed in liver tissue, along with elevated oxidative stress markers."
```
**Why ASSOCIATED**:
- "Following treatment" = temporal association, not explicit causation
- "was observed" = observation, not "caused"
- Correlation implied but not explicitly stated

**Example: KC8 (Stress Signaling) - ASSOCIATED**
```
Abstract: "The compound was associated with activation of stress response pathways, including JNK and p38 MAPK."
```
**Why ASSOCIATED**:
- "was associated with" = correlation language
- Not "caused" or "induced"
- Weaker evidence

**When to use ASSOCIATED vs SUPPORTED**:
- **SUPPORTED**: "caused", "induced", "led to" → Strong causation
- **ASSOCIATED**: "associated with", "correlated with", "observed with" → Weak causation/correlation

---

### Status 5: CAUSALLY_LINKED

**Definition**: The effect occurs, but it's caused by another KC (indirect causation), not directly by the chemical.

**Criteria**:
- 🔗 The effect is mentioned
- 🔗 But it's stated as being caused by another mechanism (KC)
- 🔗 Indirect pathway: Chemical → KC1 → KC5 (KC5 is CAUSALLY_LINKED)
- 🔗 The chemical doesn't directly cause this KC

**Examples**:

**Example: KC5 (Oxidative Stress) - CAUSALLY_LINKED**
```
Abstract: "Metabolism of the compound led to glutathione depletion, resulting in increased ROS levels and oxidative stress."
```
**Why CAUSALLY_LINKED**:
- Oxidative stress (KC5) occurs
- But it's caused by metabolism/bioactivation (KC1)
- Indirect pathway: Chemical → KC1 → KC5
- KC5 is not directly caused by the chemical

**Example: KC2 (Cell Death) - CAUSALLY_LINKED**
```
Abstract: "The chemical undergoes bioactivation via CYP450, generating reactive metabolites that deplete glutathione. This leads to mitochondrial dysfunction and ultimately triggers apoptosis in liver cells."
```
**Why CAUSALLY_LINKED**:
- Cell death (KC2) occurs
- But pathway is: Chemical → KC1 (bioactivation) → KC7 (mitochondrial dysfunction) → KC2 (cell death)
- KC2 is indirectly caused through other KCs

**When to use CAUSALLY_LINKED vs SUPPORTED**:
- **SUPPORTED**: Chemical directly causes the KC
- **CAUSALLY_LINKED**: Chemical causes KC1, which causes KC5 (KC5 is indirectly caused)

---

## The Prompt Given to the LLM

Here's a simplified version of what the LLM receives:

```
### TASK
Analyze this abstract against 12 Key Characteristics (KCs) of liver toxicity.

### KEY CHARACTERISTICS DEFINITIONS
KC1: Is reactive and/or is metabolized (bioactivated) to reactive moieties.
KC2: Causes death (apoptosis and/or necrosis) of liver cells.
KC5: Induces oxidative stress (imbalance between ROS and antioxidants).
KC7: Causes mitochondrial dysfunction.
... (all 12 KCs)

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

Example 1: KC1 - SUPPORTED
Abstract: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine."
Analysis: SUPPORTED (explicitly states bioactivation to reactive metabolite)

Example 2: KC5 - CAUSALLY_LINKED
Abstract: "Metabolism led to glutathione depletion, resulting in oxidative stress."
Analysis: CAUSALLY_LINKED (oxidative stress caused by metabolism/KC1, not directly)

Example 3: KC11 - REFUTED
Abstract: "No evidence of fibrosis was observed."
Analysis: REFUTED (explicitly states absence of fibrosis)

### OUTPUT
Return JSON with:
- kc1_status, kc2_status, ... kc12_status (values: SUPPORTED, REFUTED, NOT_MENTIONED, ASSOCIATED, CAUSALLY_LINKED)
- evidence_quotes: {"KC1": ["quote1", "quote2"], ...}
- causal_links: [{"source": "KC1", "target": "KC5", "evidence": "...", "strength": "STRONG"}]
- reasoning: "Step-by-step explanation"
```

---

## Decision Tree for the LLM

```
For each KC:
│
├─ Is the mechanism mentioned in the text?
│  │
│  ├─ NO → NOT_MENTIONED
│  │
│  └─ YES → Continue...
│     │
│     ├─ Does text explicitly state chemical DOES NOT cause this?
│     │  │
│     │  └─ YES → REFUTED
│     │
│     └─ NO → Continue...
│        │
│        ├─ Does text explicitly state chemical CAUSES this?
│        │  │
│        │  ├─ YES → Is it directly caused or indirectly (through another KC)?
│        │  │  │
│        │  │  ├─ Directly → SUPPORTED
│        │  │  │
│        │  │  └─ Indirectly (through another KC) → CAUSALLY_LINKED
│        │  │
│        │  └─ NO → Continue...
│        │     │
│        │     └─ Is the chemical associated with this effect (correlation)?
│        │        │
│        │        ├─ YES → ASSOCIATED
│        │        │
│        │        └─ NO → NOT_MENTIONED (mentioned but not related)
```

---

## Real Example: Acetaminophen Analysis

### Abstract Text:
```
"Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine that depletes glutathione and causes oxidative stress. This leads to mitochondrial dysfunction and ultimately triggers apoptosis in hepatocytes."
```

### LLM Analysis:

**KC1 (Bioactivation)**: **SUPPORTED**
- **Scan**: Found "metabolized", "NAPQI", "reactive quinone imine"
- **Evaluate**: Explicitly states "is metabolized to NAPQI" (reactive metabolite)
- **Quote**: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"
- **Decide**: SUPPORTED (direct causation)

**KC5 (Oxidative Stress)**: **CAUSALLY_LINKED**
- **Scan**: Found "oxidative stress"
- **Evaluate**: States "causes oxidative stress" BUT it's caused by NAPQI (from KC1)
- **Quote**: "depletes glutathione and causes oxidative stress"
- **Link**: KC1 → KC5 (bioactivation causes oxidative stress)
- **Decide**: CAUSALLY_LINKED (indirect causation through KC1)

**KC7 (Mitochondrial Dysfunction)**: **CAUSALLY_LINKED**
- **Scan**: Found "mitochondrial dysfunction"
- **Evaluate**: States "leads to mitochondrial dysfunction" BUT it's caused by oxidative stress (KC5)
- **Quote**: "This leads to mitochondrial dysfunction"
- **Link**: KC5 → KC7 (oxidative stress causes mitochondrial dysfunction)
- **Decide**: CAUSALLY_LINKED (indirect causation through KC5)

**KC2 (Cell Death)**: **CAUSALLY_LINKED**
- **Scan**: Found "apoptosis"
- **Evaluate**: States "triggers apoptosis" BUT it's caused by mitochondrial dysfunction (KC7)
- **Quote**: "ultimately triggers apoptosis in hepatocytes"
- **Link**: KC7 → KC2 (mitochondrial dysfunction causes apoptosis)
- **Decide**: CAUSALLY_LINKED (indirect causation through KC7)

**All Other KCs**: **NOT_MENTIONED**
- No mentions of: transport, cholestasis, cytoskeleton, fibrosis, etc.

---

## Factors That Influence the Decision

### 1. **Explicit vs. Implicit Language**
- **Explicit**: "causes", "induces", "leads to" → SUPPORTED
- **Implicit**: "associated with", "observed with" → ASSOCIATED

### 2. **Direct vs. Indirect Causation**
- **Direct**: Chemical → KC → SUPPORTED
- **Indirect**: Chemical → KC1 → KC5 → CAUSALLY_LINKED

### 3. **Negation Language**
- "no evidence", "did not cause", "absence of" → REFUTED
- "not mentioned" → NOT_MENTIONED

### 4. **Context and Keywords**
- The LLM looks for domain-specific keywords:
  - KC1: metabolism, bioactivation, reactive metabolite, NAPQI, CYP450
  - KC5: oxidative stress, ROS, glutathione, antioxidants
  - KC7: mitochondrial, ATP, electron transport chain
  - KC2: apoptosis, necrosis, cell death

### 5. **Causal Chain Recognition**
- The LLM identifies mechanistic pathways:
  - "Metabolism led to... which resulted in... which triggered..."
  - This helps distinguish SUPPORTED (direct) from CAUSALLY_LINKED (indirect)

---

## Quality Control Mechanisms

### 1. **Structured Output**
- The LLM must return JSON with specific fields
- Pydantic validation ensures correct format
- Prevents invalid statuses

### 2. **Evidence Quotes Required**
- For SUPPORTED/REFUTED/ASSOCIATED/CAUSALLY_LINKED, quotes are required
- Forces the LLM to cite specific text
- Enables verification

### 3. **Reasoning Field**
- LLM must explain its reasoning
- Shows the decision process
- Helps identify errors

### 4. **Multi-Reviewer Mode**
- Multiple models analyze the same abstract
- Consensus increases reliability
- Disagreement flags uncertain cases

### 5. **Fallback Parsing**
- If structured parsing fails, JSON extraction is attempted
- Format fixes are applied (e.g., cause/effect → source/target)
- Ensures robustness

---

## Common Challenges and How They're Handled

### Challenge 1: Ambiguous Language
**Problem**: "The compound was associated with oxidative stress"
**Solution**: LLM distinguishes between:
- "caused" → SUPPORTED
- "associated with" → ASSOCIATED

### Challenge 2: Indirect Causation
**Problem**: "Bioactivation led to oxidative stress"
**Solution**: LLM recognizes:
- Chemical directly causes bioactivation → KC1 = SUPPORTED
- Bioactivation causes oxidative stress → KC5 = CAUSALLY_LINKED

### Challenge 3: Missing Information
**Problem**: Abstract doesn't mention a mechanism
**Solution**: LLM assigns NOT_MENTIONED (not guessing)

### Challenge 4: Contradictory Statements
**Problem**: "Some studies show X, but this study found no evidence of X"
**Solution**: LLM focuses on what THIS study found (not other studies)

---

## Summary

The LLM determines KC status through a structured process:

1. **Scans** text for KC-related keywords and concepts
2. **Evaluates** whether explicit causal language is present
3. **Distinguishes** between:
   - Direct causation → SUPPORTED
   - Indirect causation → CAUSALLY_LINKED
   - Correlation → ASSOCIATED
   - Explicit negation → REFUTED
   - No mention → NOT_MENTIONED
4. **Extracts** evidence quotes to support decisions
5. **Identifies** causal relationships between KCs
6. **Provides** reasoning for transparency

The system is designed to be:
- **Conservative**: Prefers NOT_MENTIONED over guessing
- **Evidence-based**: Requires explicit statements for SUPPORTED
- **Transparent**: Provides quotes and reasoning
- **Robust**: Handles various text formats and edge cases

---

## Code References

- **Main Analysis Function**: `app.py` lines 541-1042 (`analyze_abstract_with_llm`)
- **Prompt Construction**: `app.py` lines 593-764 (prompt building)
- **Status Definitions**: `evidence_models.py` lines 279-293 (Pydantic model)
- **Parsing Logic**: `app.py` lines 818-950 (JSON parsing and validation)
