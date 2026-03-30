#!/bin/bash
# Script to organize the folder by moving utility scripts and documentation

cd "$(dirname "$0")"

# Create directories
mkdir -p scripts utilities docs/presentations docs/explanations docs/guides

echo "Organizing folder structure..."

# Move utility scripts (not imported by app.py)
echo "Moving utility scripts..."
mv -f create_presentation.py scripts/ 2>/dev/null
mv -f create_presentation_fixed.py scripts/ 2>/dev/null
mv -f create_results_presentation.py scripts/ 2>/dev/null
mv -f create_comprehensive_html_export.py scripts/ 2>/dev/null
mv -f prepare_all_results_for_reload.py scripts/ 2>/dev/null
mv -f prepare_existing_results_for_chat.py scripts/ 2>/dev/null
mv -f check_validation_vs_web.py scripts/ 2>/dev/null
mv -f compare_validation_vs_web.py scripts/ 2>/dev/null
mv -f compare_with_gold_standard.py scripts/ 2>/dev/null
mv -f diagnose_kc_detection.py scripts/ 2>/dev/null
mv -f enable_liberal_mode.py scripts/ 2>/dev/null
mv -f extract_gold_standard.py scripts/ 2>/dev/null
mv -f run_validation_nihms.py scripts/ 2>/dev/null
mv -f run_analysis_bg.py scripts/ 2>/dev/null
mv -f test_model_output.py scripts/ 2>/dev/null
mv -f optimize_performance.py scripts/ 2>/dev/null
mv -f agent_pubmed_downloader.py scripts/ 2>/dev/null
mv -f agent_rag_system.py scripts/ 2>/dev/null
mv -f protocol_registration.py scripts/ 2>/dev/null
mv -f publication_limitations.py scripts/ 2>/dev/null

# Move PowerPoint presentations
echo "Moving presentations..."
mv -f AI_Toxicologist_Presentation*.pptx docs/presentations/ 2>/dev/null
mv -f ~\$AI_Toxicologist_Presentation.pptx docs/presentations/ 2>/dev/null

# Move documentation/explanation files
echo "Moving documentation..."
mv -f *_EXPLANATION.md docs/explanations/ 2>/dev/null
mv -f *_GUIDE.md docs/guides/ 2>/dev/null
mv -f *_SCRIPT.md docs/presentations/ 2>/dev/null
mv -f PRESENTATION_SCRIPT.md docs/presentations/ 2>/dev/null
mv -f SCIENTIFIC_PRESENTATION_*.md docs/presentations/ 2>/dev/null
mv -f SCIENTIFIC_EXPLANATION_*.md docs/presentations/ 2>/dev/null
mv -f HOW_LLM_DETERMINES_*.md docs/explanations/ 2>/dev/null
mv -f KC_STATUS_DECISION_*.md docs/explanations/ 2>/dev/null
mv -f PROGRAMMATIC_IMPLEMENTATION.md docs/explanations/ 2>/dev/null
mv -f HEATMAP_AND_ROB_EXPLANATION.md docs/explanations/ 2>/dev/null
mv -f ACETAMINOPHEN_RESULTS_EXPLANATION.md docs/explanations/ 2>/dev/null

# Move summary/report files
echo "Moving summary files..."
mv -f *_SUMMARY.md docs/guides/ 2>/dev/null
mv -f *_REVIEW.md docs/guides/ 2>/dev/null
mv -f *_COMPLETE.md docs/guides/ 2>/dev/null
mv -f *_FIX.md docs/guides/ 2>/dev/null
mv -f *_INSTRUCTIONS.md docs/guides/ 2>/dev/null
mv -f CODE_*.md docs/guides/ 2>/dev/null
mv -f VALIDATION_*.md docs/guides/ 2>/dev/null
mv -f COMPARISON_*.md docs/guides/ 2>/dev/null

# Move feature documentation
echo "Moving feature documentation..."
mv -f *_FEATURE.md docs/guides/ 2>/dev/null
mv -f MULTI_REVIEWER_*.md docs/guides/ 2>/dev/null
mv -f GPU_MPI_*.md docs/guides/ 2>/dev/null
mv -f RELOAD_RESULTS_*.md docs/guides/ 2>/dev/null
mv -f ROB_INTERACTIVE_*.md docs/guides/ 2>/dev/null
mv -f EVIDENCE_QUOTES_*.md docs/guides/ 2>/dev/null
mv -f RELEVANCE_FILTERING_*.md docs/guides/ 2>/dev/null

# Move other documentation
mv -f API_DOCUMENTATION.md docs/guides/ 2>/dev/null
mv -f PERFORMANCE_*.md docs/guides/ 2>/dev/null
mv -f QUICK_*.md docs/guides/ 2>/dev/null
mv -f SPEED_*.md docs/guides/ 2>/dev/null
mv -f IMPROVEMENTS.md docs/guides/ 2>/dev/null
mv -f IMPLEMENTATION_*.md docs/guides/ 2>/dev/null
mv -f PUBLICATION_*.md docs/guides/ 2>/dev/null
mv -f PREDICTION_*.md docs/guides/ 2>/dev/null
mv -f LLM_*.md docs/guides/ 2>/dev/null
mv -f SCIENTIFIC_IMPROVEMENTS.md docs/guides/ 2>/dev/null
mv -f BUG_FIX_*.md docs/guides/ 2>/dev/null
mv -f QUICK_FIX_*.md docs/guides/ 2>/dev/null
mv -f QUICK_IMPROVEMENTS_*.md docs/guides/ 2>/dev/null

# Move shell scripts
echo "Moving shell scripts..."
mv -f *.sh scripts/ 2>/dev/null

# Move text files (if any)
echo "Moving text files..."
mv -f *.txt utilities/ 2>/dev/null 2>/dev/null

# Move cursor files (if any)
echo "Moving cursor files..."
mv -f cursor* utilities/ 2>/dev/null

echo "Organization complete!"
echo ""
echo "New structure:"
echo "  scripts/ - Utility and helper scripts"
echo "  utilities/ - Additional utilities and text files"
echo "  docs/presentations/ - Presentation files and scripts"
echo "  docs/explanations/ - Detailed explanations"
echo "  docs/guides/ - Guides and documentation"
