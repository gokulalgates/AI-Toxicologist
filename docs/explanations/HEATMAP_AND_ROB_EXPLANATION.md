# Heatmap and Risk-of-Bias Summary: Calculation Methods Explained

## 1. Evidence Matrix Heatmap

### Purpose
The Evidence Matrix Heatmap visualizes which Key Characteristics (KCs) are supported by each study, creating a **Papers × KCs** matrix.

### Calculation Steps

#### Step 1: Create Evidence Matrix DataFrame
**Location**: `app.py` lines 1045-1074 (`create_evidence_matrix` function)

For each study (paper), the system creates a row with:
- **Paper metadata**: Paper number, PMID, Title (truncated to 50 chars), Dose-Response info
- **KC columns**: One column for each of the 12 Key Characteristics

#### Step 2: Encode KC Status as Numeric Values
**Location**: `app.py` lines 1058-1070

Each KC status is converted to a numeric value:

| Status | Numeric Value | Meaning |
|--------|---------------|---------|
| `SUPPORTED` | **1** | Direct evidence supporting the KC |
| `ASSOCIATED` | **0.7** | Associated evidence (weaker support) |
| `CAUSALLY_LINKED` | **0.5** | Indirect causation evidence |
| `NOT_MENTIONED` | **0** | KC not mentioned in the study |
| `REFUTED` | **-1** | Evidence refutes the KC |

**Example**:
```python
# Study 1 (PMID: 41386882)
KC1_status = "SUPPORTED"  → KC1 = 1
KC2_status = "NOT_MENTIONED" → KC2 = 0
KC5_status = "SUPPORTED" → KC5 = 1
KC12_status = "SUPPORTED" → KC12 = 1
# All other KCs = 0
```

#### Step 3: Create Heatmap Visualization
**Location**: `app.py` lines 1235-1267 (`create_heatmap` function)

**Visualization Details**:
- **X-axis**: 12 Key Characteristics (KC1-KC12) with full names
- **Y-axis**: Each study (Paper number + truncated title)
- **Color Scheme**: 
  - 🟢 **Green** (value = 1): KC is SUPPORTED
  - ⚪ **White** (value = 0): KC is NOT_MENTIONED
  - 🔴 **Red** (value = -1): KC is REFUTED
  - 🟡 **Yellow** (value = 0.7 or 0.5): KC is ASSOCIATED or CAUSALLY_LINKED

**Colormap**: `RdYlGn` (Red-Yellow-Green diverging colormap)
- **Center**: 0 (white for NOT_MENTIONED)
- **Range**: -1 (red) to 1 (green)

**Annotations**: Each cell shows the numeric value (1, 0.7, 0.5, 0, or -1)

### Example Calculation

For **Acetaminophen** analysis with 15 studies:

```
Study 1 (PMID: 41386882):
  KC1 = 1 (SUPPORTED)
  KC5 = 1 (SUPPORTED)
  KC12 = 1 (SUPPORTED)
  All others = 0

Study 2 (PMID: 41386555):
  KC1 = 1 (SUPPORTED)
  KC5 = 1 (SUPPORTED)
  KC7 = 1 (SUPPORTED)
  KC8 = 1 (SUPPORTED)
  All others = 0
```

The heatmap shows:
- **Rows**: 15 studies
- **Columns**: 12 KCs
- **Cell values**: 1 (green), 0.7 (yellow), 0.5 (yellow), 0 (white), or -1 (red)

### Interpretation

- **Dense green columns**: KCs supported by many studies (e.g., KC1, KC5)
- **Sparse columns**: KCs rarely mentioned (e.g., KC4, KC10)
- **Red cells**: Studies that refute a KC (rare)
- **Patterns**: Clusters of green indicate commonly co-occurring KCs

---

## 2. Risk-of-Bias Summary

### Purpose
The Risk-of-Bias Summary shows the distribution of overall risk-of-bias judgments across all studies.

### Calculation Steps

#### Step 1: Assess Risk-of-Bias for Each Study
**Location**: `risk_of_bias.py` lines 49-200 (`assess_rob_with_llm` function)

For each study, the LLM assesses **7 OHAT domains**:
1. Selection Bias
2. Confounding
3. Performance Bias
4. Detection/Measurement Bias
5. Attrition Bias
6. Selective Reporting
7. Other Sources of Bias

**Judgment Options**:
- `Low`: Study design minimizes bias
- `Some concerns`: Some issues that may introduce bias
- `High`: Significant risk of bias
- `Critical`: Critical flaws that invalidate the study
- `N/A`: Domain not applicable
- `Insufficient information`: Not enough information to assess

#### Step 2: Determine Overall Judgment
**Location**: `risk_of_bias.py` (within `assess_rob_with_llm`)

The **overall judgment** is determined by the LLM based on:
- Individual domain judgments
- Study design quality
- Reporting completeness

**Logic** (simplified):
- If all domains = `Low` → Overall = `Low`
- If any domain = `High` or `Critical` → Overall = `High` or `Critical`
- If mix of `Low` and `Some concerns` → Overall = `Some concerns`
- If insufficient information → Overall = `Insufficient information`

#### Step 3: Count Judgments
**Location**: `rob_visualization.py` lines 109-141 (`create_rob_summary_figure` function)

**Calculation**:
```python
judgment_counts = {
    "Low": 0,
    "Some concerns": 0,
    "High": 0,
    "Critical": 0
}

for each study:
    overall_judgment = study.overall_judgment
    judgment_counts[overall_judgment] += 1
```

#### Step 4: Create Bar Chart
**Location**: `rob_visualization.py` lines 119-141

**Visualization**:
- **X-axis**: Judgment categories (Low, Some concerns, High, Critical)
- **Y-axis**: Number of studies
- **Bars**: Colored bars showing count for each category
- **Colors**:
  - 🟢 **Green** (`#2ecc71`): Low risk
  - 🟠 **Orange** (`#f39c12`): Some concerns
  - 🔴 **Red** (`#e74c3c`): High risk
  - 🟣 **Purple** (`#8e44ad`): Critical risk

**Annotations**: Each bar shows the count (e.g., "8" for Low risk)

### Example Calculation

For **Acetaminophen** analysis with 15 studies:

**Step 1**: Each study assessed for 7 domains
```
Study 1 (PMID: 41386882):
  Selection Bias: Low
  Confounding: Insufficient information
  Performance Bias: Low
  Detection/Measurement Bias: Insufficient information
  Attrition Bias: Low
  Selective Reporting: Insufficient information
  Other Sources: Low
  → Overall: Insufficient information

Study 2 (PMID: 41386555):
  All domains: Low
  → Overall: Low

Study 3 (PMID: 41366830):
  Confounding: Some concerns
  Detection/Measurement Bias: Some concerns
  Others: Low
  → Overall: Some concerns
```

**Step 2**: Count overall judgments
```
Low: 8 studies
Some concerns: 6 studies
High: 0 studies
Critical: 0 studies
Insufficient information: 1 study
```

**Step 3**: Create bar chart
- Bar 1 (Low): Height = 8, Color = Green
- Bar 2 (Some concerns): Height = 6, Color = Orange
- Bar 3 (High): Height = 0 (not shown)
- Bar 4 (Critical): Height = 0 (not shown)

### Summary Statistics
**Location**: `risk_of_bias.py` lines 340-370 (`calculate_rob_summary_stats` function)

The system also calculates:
- **Total studies**: 15
- **Low risk percentage**: (8/15) × 100 = 53.3%
- **Some concerns percentage**: (6/15) × 100 = 40.0%
- **High risk percentage**: (0/15) × 100 = 0%
- **Full-text used**: 0/15 (0%)

---

## 3. Risk-of-Bias Heatmap (by KC and Domain)

### Purpose
Shows risk-of-bias assessments **grouped by Key Characteristic and domain**, revealing which KCs have higher-quality supporting evidence.

### Calculation Steps

#### Step 1: Filter KCs
**Location**: `rob_visualization.py` lines 35-43

Only KCs that are **SUPPORTED** in at least one study are included:
```python
for each KC:
    if KC is SUPPORTED in any study:
        include KC in heatmap
    else:
        skip KC
```

#### Step 2: Build Matrix
**Location**: `rob_visualization.py` lines 45-64

For each KC-Domain pair:
1. Find all studies that **support** the KC
2. Get the domain judgment from each of those studies
3. Calculate **average judgment** (numeric)

**Judgment Mapping**:
```python
judgment_map = {
    "Low": 0,
    "Some concerns": 1,
    "High": 2,
    "Critical": 3,
    "N/A": -1,
    "Insufficient information": -1  # Treated as N/A
}
```

**Example**:
```
KC1 (Reactive/Bioactivation) - Selection Bias:
  Study 1: Low (0)
  Study 2: Low (0)
  Study 3: Low (0)
  ... (all 15 studies support KC1)
  Average = (0 + 0 + ... + 0) / 15 = 0.0 → "Low"
```

#### Step 3: Create Heatmap
**Location**: `rob_visualization.py` lines 74-106

**Visualization**:
- **X-axis**: 7 OHAT domains
- **Y-axis**: KCs that are supported (e.g., KC1, KC2, KC5, KC7, KC8, KC12)
- **Cell values**: Average judgment (0.0 to 3.0, or -1 for N/A)
- **Color Scheme**:
  - 🟢 **Green** (0.0): Low risk
  - 🟠 **Orange** (1.0): Some concerns
  - 🔴 **Red** (2.0): High risk
  - 🟣 **Purple** (3.0): Critical risk
  - ⚪ **Gray** (-1): N/A or Insufficient information

**Annotations**: Each cell shows the numeric average (e.g., "0.0", "1.0")

### Example Calculation

For **Acetaminophen**:

**KC1 (Reactive/Bioactivation)** - supported by 15 studies:
```
Selection Bias: (15 × Low) / 15 = 0.0 → Green
Confounding: Mix of Low and Insufficient → ~0.5 → Yellow-Orange
Performance Bias: (15 × Low) / 15 = 0.0 → Green
...
```

**KC2 (Cell Death)** - supported by 8 studies:
```
Selection Bias: (8 × Low) / 8 = 0.0 → Green
Confounding: Mix of Low and Some concerns → ~0.5 → Yellow-Orange
...
```

### Interpretation

- **Green cells**: KCs supported by high-quality studies (low bias)
- **Orange/Red cells**: KCs supported by studies with bias concerns
- **Patterns**: 
  - Consistent green across domains → High-quality evidence
  - Orange/Red in specific domains → Systematic bias issues
  - Gray cells → Insufficient information for that KC-domain pair

---

## Summary: Key Differences

| Visualization | Purpose | Dimensions | Calculation |
|---------------|---------|------------|-------------|
| **Evidence Matrix Heatmap** | Shows which KCs each study supports | Papers × KCs | Binary/multi-level encoding (1, 0.7, 0.5, 0, -1) |
| **Risk-of-Bias Summary** | Overall study quality distribution | Judgment categories × Count | Count studies by overall judgment |
| **Risk-of-Bias Heatmap** | Quality of evidence per KC-domain | KCs × Domains | Average domain judgments for KC-supporting studies |

---

## Code References

1. **Evidence Matrix**: `app.py` lines 1045-1074 (`create_evidence_matrix`)
2. **Evidence Heatmap**: `app.py` lines 1235-1267 (`create_heatmap`)
3. **RoB Assessment**: `risk_of_bias.py` lines 49-200 (`assess_rob_with_llm`)
4. **RoB Summary Stats**: `risk_of_bias.py` lines 340-370 (`calculate_rob_summary_stats`)
5. **RoB Summary Chart**: `rob_visualization.py` lines 109-141 (`create_rob_summary_figure`)
6. **RoB Heatmap**: `rob_visualization.py` lines 13-106 (`create_rob_heatmap_figure`)

---

## Example: Acetaminophen Results

### Evidence Matrix Heatmap
- **15 studies** × **12 KCs**
- **KC1** (Bioactivation): 15/15 green (100% support)
- **KC5** (Oxidative Stress): 15/15 green (100% support)
- **KC7** (Mitochondrial Dysfunction): 12/15 green (80% support)
- **KC2, KC8, KC12**: Mixed support (6-9 studies)
- **KC3, KC4, KC6, KC9, KC10, KC11**: Mostly white (rarely mentioned)

### Risk-of-Bias Summary
- **Low**: 8/15 (53.3%)
- **Some concerns**: 6/15 (40.0%)
- **High**: 0/15 (0%)
- **Critical**: 0/15 (0%)
- **Insufficient information**: 1/15 (6.7%)

### Risk-of-Bias Heatmap
- **KC1** (15 supporting studies): Mostly green (low bias), some orange in Confounding/Detection domains
- **KC5** (15 supporting studies): Similar pattern to KC1
- **KC7** (12 supporting studies): Mostly green, some orange in Confounding
- **KC2, KC8, KC12** (6-9 supporting studies): Mix of green and orange

This indicates that the **primary mechanisms** (KC1, KC5, KC7) are supported by relatively high-quality studies, while **secondary mechanisms** (KC2, KC8, KC12) have more variable study quality.
