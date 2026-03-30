# Validation Using NIHMS Paper as Gold Standard

## Overview

This validation compares the AI system's assessments against expert-level assessments from the foundational paper on Key Characteristics of Human Hepatotoxicants (Rusyn et al. Hepatology 2021, NIHMS-1779672).

## Gold Standard Source

**Paper**: Rusyn et al. "Key Characteristics of Human Hepatotoxicants as a Basis for Identification and Characterization of the Causes of Liver Toxicity"  
**Journal**: Hepatology, 2021  
**DOI**: 10.1002/hep.31999  
**NIHMS ID**: nihms-1779672

### Expert Assessment for Acetaminophen

The paper explicitly states:
> "Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)"

And provides detailed mechanistic evidence for each:

- **KC1 (Bioactivation)**: SUPPORTED - Metabolized to reactive NAPQI
- **KC2 (Cell Death)**: SUPPORTED - Hepatocellular death
- **KC3 (Proliferation/Regeneration)**: SUPPORTED - Proliferation of hepatocytes
- **KC4 (Transport Disruption)**: SUPPORTED - Efflux transporters upregulated
- **KC5 (Oxidative Stress)**: SUPPORTED - Enhanced ROS production
- **KC6 (Immune Response)**: SUPPORTED - Neutrophils activated
- **KC7 (Mitochondrial Dysfunction)**: SUPPORTED - Key factor in injury
- **KC8 (Stress Signaling)**: SUPPORTED - JNK activation
- **KC9 (Cholestasis)**: NOT_MENTIONED
- **KC10 (Cytoskeleton)**: NOT_MENTIONED
- **KC11 (Fibrosis)**: NOT_MENTIONED
- **KC12 (Metabolism Disruption)**: SUPPORTED - Decreases in export proteins

## Validation Process

### Step 1: Gold Standard Creation ✅
- Extracted expert assessments from the NIHMS paper
- Created `gold_standard_nihms.json` with structured data
- Chemical: Acetaminophen
- KCs SUPPORTED: KC1, KC2, KC3, KC4, KC5, KC6, KC7, KC8, KC12

### Step 2: AI Analysis 🔄 (Currently Running)
- Running AI system on Acetaminophen
- Using multi-reviewer mode (llama3.2, mixtral)
- Analyzing relevant abstracts from PubMed
- Extracting KC assessments for each study

### Step 3: Comparison (Pending)
- Aggregate AI KC assessments across studies
- Compare AI consensus vs gold standard
- Calculate performance metrics:
  - Precision (correctly identified SUPPORTED / total AI SUPPORTED)
  - Recall (correctly identified SUPPORTED / total gold standard SUPPORTED)
  - F1 Score (harmonic mean of precision and recall)
  - Accuracy (overall agreement)

### Step 4: Report Generation (Pending)
- Generate `validation_report_nihms.json` with:
  - Per-KC metrics
  - Overall performance metrics
  - Detailed comparison

## Expected Output

The validation will produce:

1. **Gold Standard File**: `gold_standard_nihms.json`
2. **AI Results**: Analysis results in `results/Acetaminophen/`
3. **Validation Report**: `validation_report_nihms.json`

### Metrics to Report

For each KC:
- **True Positives**: KC is SUPPORTED in both gold standard and AI
- **False Positives**: KC is SUPPORTED in AI but NOT_MENTIONED in gold standard
- **False Negatives**: KC is SUPPORTED in gold standard but NOT_MENTIONED in AI
- **True Negatives**: KC is NOT_MENTIONED in both

### Success Criteria

- **High Recall**: AI should identify most KCs that experts identified (minimize false negatives)
- **High Precision**: AI should not over-predict KCs (minimize false positives)
- **Balanced F1**: Good balance between precision and recall

## Running the Validation

```bash
# Run validation script
python run_validation_nihms.py

# This will:
# 1. Create gold standard from paper
# 2. Run AI analysis (or use existing results)
# 3. Compare and generate report
```

## Notes

- The gold standard is based on expert consensus from a foundational paper
- This is a chemical-level comparison (not study-level)
- AI results are aggregated across multiple studies
- The comparison uses consensus logic (>50% of studies must support a KC)

## Interpretation

After validation completes, review:
1. Which KCs did AI correctly identify? (True Positives)
2. Which KCs did AI miss? (False Negatives - most critical)
3. Which KCs did AI over-predict? (False Positives)
4. Overall performance metrics

This validation provides quantitative evidence of the AI system's accuracy compared to expert-level assessments.
