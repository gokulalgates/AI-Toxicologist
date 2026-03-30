# Multi-Reviewer System Feature

## Overview

The AI Toxicologist now supports a **Multi-Reviewer Mode** where multiple high-end LLM models act as independent reviewers, similar to how human systematic reviews use multiple reviewers. This significantly improves reliability and reduces bias.

## How It Works

### 1. **Independent Review**
- Each selected model independently analyzes all abstracts
- Models don't see each other's results (no cross-contamination)
- Each model produces its own KC assessments for every paper

### 2. **Consensus Consolidation**
- Results are consolidated using **majority voting**
- For each KC in each paper, the consensus status is determined by the majority vote
- Confidence scores reflect the level of agreement (e.g., 3/3 = 100%, 2/3 = 67%)

### 3. **Agreement Statistics**
- **Inter-model agreement**: Cohen's κ calculated pairwise between all models
- **Per-paper agreement**: Average agreement rate across all KCs for each paper
- **Per-KC agreement**: Agreement rates for each Key Characteristic

### 4. **Paper Ranking**
Papers are ranked by a combined score considering:
- **Consensus strength**: How much models agree
- **Evidence quality**: Number of supported KCs with high consensus
- **Ranking method**: "combined" (default), "agreement", or "evidence"

## Usage

### Single Reviewer Mode (Default)
1. Select **one model** from the checkbox list
2. Analysis runs with that single model
3. Standard output format

### Multi-Reviewer Mode
1. Select **2-3 models** from the checkbox list (recommended: `llama3.2`, `mixtral`, `mistral`)
2. Each model independently reviews all papers
3. Results are consolidated with consensus statistics
4. Papers are ranked by consensus strength

## Output Features

### Summary Statistics
- Overall agreement rate across all papers
- Pairwise Cohen's κ between models
- Top-ranked papers by consensus strength

### Evidence Matrix
- Shows consensus status for each paper-KC combination
- High consensus (≥67%): Strong evidence
- Low consensus (<67%): Disputed evidence
- Perfect consensus (100%): Unanimous agreement

### Ranking
Papers are automatically ranked by:
1. Consensus strength (agreement rate)
2. Evidence quality (number of supported KCs)
3. Combined score (weighted combination)

## Benefits

1. **Higher Reliability**: Multiple independent assessments reduce single-model bias
2. **Quality Control**: Low agreement flags potentially problematic papers
3. **Confidence Scoring**: Know which findings have strong vs. weak consensus
4. **Publication-Grade**: Mimics standard systematic review practices

## Performance Considerations

- **Time**: Multi-reviewer mode takes ~N× longer (N = number of models)
- **Resources**: Each model runs sequentially (can be parallelized in future)
- **Recommended**: Use 2-3 high-end models for best balance of speed and reliability

## Technical Details

### Consensus Methods
- **Majority Voting** (default): Most common status wins
- **Weighted** (future): Weight by model quality/performance

### Agreement Metrics
- **Cohen's κ**: Measures inter-rater agreement beyond chance
- **Gwet's AC1**: Alternative metric less affected by prevalence
- **Agreement Rate**: Simple percentage agreement

### Ranking Methods
- **Combined** (default): Weighted combination of agreement + evidence
- **Agreement**: Rank by consensus strength only
- **Evidence**: Rank by number of supported KCs only

## Example Output

```
Multi-Reviewer Agreement Statistics:
------------------------------------------------------------
Overall Agreement: 78.5% 
  (Range: 45.2% - 95.8%)

Inter-Model Agreement (Cohen's κ):
  • llama3.2 vs mixtral: κ = 0.723 (Substantial)
  • llama3.2 vs mistral: κ = 0.689 (Substantial)
  • mixtral vs mistral: κ = 0.756 (Substantial)
  Mean κ: 0.723

Top Ranked Papers (by Consensus Strength):
  1. PMID 12345678: Agreement=95.8%, Score=0.847
  2. PMID 23456789: Agreement=91.2%, Score=0.812
  3. PMID 34567890: Agreement=87.5%, Score=0.789
  ...
```

## Future Enhancements

- [ ] Parallel model execution (faster processing)
- [ ] Weighted consensus by model performance
- [ ] Disagreement analysis (why models disagree)
- [ ] Visualization of agreement heatmaps
- [ ] Export ranked paper lists
