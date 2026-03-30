# How the LLM Determines KC Status: Quick Reference Guide

## The 5-Step Decision Process

For each Key Characteristic (KC), the LLM follows this process:

```
1. SCAN → 2. EVALUATE → 3. QUOTE → 4. LINK → 5. DECIDE
```

---

## Status Definitions & Decision Criteria

### ✅ SUPPORTED
**Meaning**: Chemical explicitly causes this effect

**Look for**:
- "causes", "induces", "leads to", "results in", "triggers"
- "is metabolized to", "undergoes bioactivation"
- "depletes", "disrupts", "activates"

**Example**:
```
"Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine."
→ KC1 = SUPPORTED (explicitly states bioactivation)
```

---

### ⚪ NOT_MENTIONED
**Meaning**: Mechanism not discussed in the text

**Look for**:
- No keywords related to the KC
- No concepts related to the KC
- Complete absence from text

**Example**:
```
"Acetaminophen caused oxidative stress and mitochondrial dysfunction."
→ KC4 (Transport Disruption) = NOT_MENTIONED (not discussed)
```

---

### ❌ REFUTED
**Meaning**: Text explicitly states chemical does NOT cause this effect

**Look for**:
- "no evidence of", "did not cause", "was not observed"
- "absence of", "lack of", "no signs of"

**Example**:
```
"Histological examination revealed no evidence of fibrosis."
→ KC11 = REFUTED (explicitly states absence)
```

---

### ⚠️ ASSOCIATED
**Meaning**: Chemical is associated with effect, but causation not explicit (correlation)

**Look for**:
- "associated with", "correlated with", "observed with"
- Temporal association ("following treatment")
- No explicit causal language

**Example**:
```
"Following treatment, increased apoptosis was observed."
→ KC2 = ASSOCIATED (temporal association, not explicit causation)
```

---

### 🔗 CAUSALLY_LINKED
**Meaning**: Effect occurs but caused by another KC (indirect causation)

**Look for**:
- Effect is mentioned
- But stated as caused by another mechanism
- Indirect pathway: Chemical → KC1 → KC5

**Example**:
```
"Metabolism led to glutathione depletion, resulting in oxidative stress."
→ KC5 = CAUSALLY_LINKED (oxidative stress caused by metabolism/KC1, not directly)
```

---

## Decision Tree

```
Is mechanism mentioned?
│
├─ NO → NOT_MENTIONED
│
└─ YES
   │
   ├─ Does text say "does NOT cause"?
   │  └─ YES → REFUTED
   │
   └─ NO
      │
      ├─ Does text say "causes/induces"?
      │  │
      │  ├─ Directly? → SUPPORTED
      │  │
      │  └─ Indirectly (through another KC)? → CAUSALLY_LINKED
      │
      └─ NO
         │
         └─ Is chemical "associated with" effect?
            │
            ├─ YES → ASSOCIATED
            │
            └─ NO → NOT_MENTIONED
```

---

## Real Example: Acetaminophen

### Abstract:
```
"Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine 
that depletes glutathione and causes oxidative stress. This leads to 
mitochondrial dysfunction and ultimately triggers apoptosis in hepatocytes."
```

### LLM Analysis:

| KC | Status | Why |
|---|---|---|
| **KC1** (Bioactivation) | ✅ **SUPPORTED** | "is metabolized to NAPQI" = explicit causation |
| **KC5** (Oxidative Stress) | 🔗 **CAUSALLY_LINKED** | "causes oxidative stress" BUT caused by NAPQI (KC1) |
| **KC7** (Mitochondrial Dysfunction) | 🔗 **CAUSALLY_LINKED** | "leads to mitochondrial dysfunction" BUT caused by oxidative stress (KC5) |
| **KC2** (Cell Death) | 🔗 **CAUSALLY_LINKED** | "triggers apoptosis" BUT caused by mitochondrial dysfunction (KC7) |
| **KC3-KC4, KC6, KC8-KC12** | ⚪ **NOT_MENTIONED** | Not discussed |

---

## Key Distinctions

### SUPPORTED vs CAUSALLY_LINKED
- **SUPPORTED**: Chemical directly causes KC
  - "Chemical causes oxidative stress"
- **CAUSALLY_LINKED**: Chemical causes KC1, which causes KC5
  - "Metabolism (KC1) leads to oxidative stress (KC5)"

### SUPPORTED vs ASSOCIATED
- **SUPPORTED**: Explicit causation
  - "causes", "induces", "leads to"
- **ASSOCIATED**: Correlation, not explicit causation
  - "associated with", "correlated with", "observed with"

### REFUTED vs NOT_MENTIONED
- **REFUTED**: Explicitly tested and found absent
  - "no evidence of fibrosis"
- **NOT_MENTIONED**: Not tested or discussed
  - Fibrosis not mentioned at all

---

## What the LLM Receives

1. **Abstract text** (and optionally full-text)
2. **12 KC definitions** (what each mechanism means)
3. **Instructions** (how to assess each KC)
4. **Examples** (showing correct decisions)

## What the LLM Returns

- **Status for each KC** (SUPPORTED, NOT_MENTIONED, REFUTED, ASSOCIATED, CAUSALLY_LINKED)
- **Evidence quotes** (exact sentences supporting each decision)
- **Causal links** (relationships between KCs)
- **Reasoning** (explanation of decisions)

---

## Quality Controls

1. **Structured Output**: Must return valid JSON
2. **Evidence Required**: Quotes needed for SUPPORTED/REFUTED
3. **Reasoning Required**: Must explain decisions
4. **Multi-Reviewer**: Multiple models for consensus
5. **Validation**: Pydantic ensures correct format

---

## Summary

The LLM determines KC status by:
1. **Scanning** text for KC-related keywords
2. **Evaluating** whether explicit causal language exists
3. **Distinguishing** direct vs indirect causation
4. **Extracting** evidence quotes
5. **Providing** reasoning for transparency

**Conservative approach**: Prefers NOT_MENTIONED over guessing

**Evidence-based**: Requires explicit statements for SUPPORTED

**Transparent**: Provides quotes and reasoning for all decisions
