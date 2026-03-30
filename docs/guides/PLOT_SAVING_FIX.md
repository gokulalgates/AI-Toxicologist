# Plot Saving Fix - Implementation Summary

## Problem
Plots and PRISMA diagrams were being generated and displayed in the Gradio interface, but were not being saved to disk. Only data files (JSON, JSONL) were being saved.

## Solution
Added automatic plot saving functionality that saves all generated visualizations to disk in multiple formats.

## Implementation

### New File: `plot_utils.py`
Contains utilities for saving matplotlib figures:
- `save_plot()`: Saves a single figure in multiple formats (PNG, PDF, SVG, JPG)
- `save_all_plots()`: Saves all plots from an analysis session

### Modified File: `app.py`
- Added import: `from plot_utils import save_all_plots`
- Added plot saving code before returning results in `analyze_chemical()` function

## What Gets Saved

All plots are automatically saved to:
```
results/{chemical_name}/plots/
```

### Saved Plots:
1. **Evidence Matrix Heatmap** (`evidence_matrix_heatmap_YYYYMMDD_HHMMSS.png/pdf`)
   - Shows which Key Characteristics are supported by which studies

2. **Causal Pathway Network** (`causal_pathway_network_YYYYMMDD_HHMMSS.png/pdf`)
   - Directed graph showing mechanistic relationships between KCs

3. **PRISMA Flow Diagram** (`prisma_flow_diagram_YYYYMMDD_HHMMSS.png/pdf`)
   - PRISMA 2020 compliant flow diagram showing study selection process

4. **Risk-of-Bias Heatmap** (`risk_of_bias_heatmap_YYYYMMDD_HHMMSS.png/pdf`)
   - Heatmap showing risk-of-bias assessments across studies and domains

5. **Risk-of-Bias Summary** (`risk_of_bias_summary_YYYYMMDD_HHMMSS.png/pdf`)
   - Summary visualization of risk-of-bias distribution

## File Formats

Each plot is saved in **two formats**:
- **PNG** (300 DPI) - For presentations and web use
- **PDF** - For publications and high-quality printing

## Features

- ✅ Automatic saving after analysis completes
- ✅ Timestamped filenames to prevent overwrites
- ✅ Multiple formats (PNG + PDF)
- ✅ High resolution (300 DPI for PNG)
- ✅ Organized in `plots/` subdirectory
- ✅ Error handling (warnings if save fails, doesn't crash analysis)
- ✅ Summary message in output showing where plots were saved

## Example Output Structure

```
results/
  acetaminophen/
    plots/
      evidence_matrix_heatmap_20251120_103045.png
      evidence_matrix_heatmap_20251120_103045.pdf
      causal_pathway_network_20251120_103045.png
      causal_pathway_network_20251120_103045.pdf
      prisma_flow_diagram_20251120_103045.png
      prisma_flow_diagram_20251120_103045.pdf
      risk_of_bias_heatmap_20251120_103045.png
      risk_of_bias_heatmap_20251120_103045.pdf
      risk_of_bias_summary_20251120_103045.png
      risk_of_bias_summary_20251120_103045.pdf
    provenance_2025-11-20T10-30-45.json
    search_log_20251120_103045.json
    study_records.jsonl
```

## Usage

No changes needed! The plots are automatically saved whenever an analysis runs. The summary output will now include a section showing where plots were saved:

```
Plots saved to:
  • heatmap: results/acetaminophen/plots/evidence_matrix_heatmap_20251120_103045.png
  • network: results/acetaminophen/plots/causal_pathway_network_20251120_103045.png
  • prisma: results/acetaminophen/plots/prisma_flow_diagram_20251120_103045.png
  • rob_heatmap: results/acetaminophen/plots/risk_of_bias_heatmap_20251120_103045.png
  • rob_summary: results/acetaminophen/plots/risk_of_bias_summary_20251120_103045.png
```

## Error Handling

If plot saving fails for any reason:
- A warning message is printed to console
- The analysis continues normally
- Plots are still displayed in the Gradio interface
- No data is lost

## Testing

To verify plots are being saved:
1. Run an analysis
2. Check the `results/{chemical_name}/plots/` directory
3. Verify PNG and PDF files are present
4. Open files to confirm they contain the correct plots

## Notes

- Plots are saved with `bbox_inches='tight'` to remove extra whitespace
- PNG files use 300 DPI for high quality
- PDF files are vector format (scalable, no quality loss)
- Timestamps prevent overwriting previous analyses
- Each analysis creates new plot files
