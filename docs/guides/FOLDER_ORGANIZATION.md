# Folder Organization

## Structure

```
Key_char_liver/
├── app.py                    # Main application (run this)
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
├── README.md                 # Main documentation
│
├── Core Modules (used by app.py):
│   ├── search_enhanced.py
│   ├── fulltext_retrieval.py
│   ├── evidence_models.py
│   ├── evidence_profiles.py
│   ├── provenance.py
│   ├── plot_utils.py
│   ├── prisma.py
│   ├── risk_of_bias.py
│   ├── rob_visualization.py
│   ├── certainty_grading.py
│   ├── reliability.py
│   ├── multi_reviewer.py
│   ├── exceptions.py
│   ├── utils.py
│   ├── gpu_utils.py
│   ├── mpi_support.py
│   ├── confidence_scoring.py
│   ├── rag_system.py
│   ├── hierarchical_processing.py
│   ├── active_learning.py
│   ├── calibration.py
│   ├── prompt_templates.py
│   ├── prompt_improvements.py
│   ├── causal_reasoning.py
│   ├── hepatotoxicity_agent.py
│   └── reproducibility.py
│
├── scripts/                  # Utility scripts (not needed to run app)
│   ├── create_presentation.py
│   ├── create_results_presentation.py
│   ├── prepare_all_results_for_reload.py
│   ├── optimize_performance.py
│   ├── compare_with_gold_standard.py
│   └── ... (other utility scripts)
│
├── docs/
│   ├── presentations/        # Presentation files and scripts
│   │   ├── AI_Toxicologist_Presentation.pptx
│   │   ├── PRESENTATION_SCRIPT.md
│   │   └── SCIENTIFIC_PRESENTATION_*.md
│   │
│   ├── explanations/         # Detailed explanations
│   │   ├── HOW_LLM_DETERMINES_KC_STATUS.md
│   │   ├── PROGRAMMATIC_IMPLEMENTATION.md
│   │   └── HEATMAP_AND_ROB_EXPLANATION.md
│   │
│   └── guides/               # Guides and documentation
│       ├── PERFORMANCE_OPTIMIZATION.md
│       ├── API_DOCUMENTATION.md
│       └── ... (other guides)
│
├── utilities/                # Additional utilities
│   └── (text files, cursor files, etc.)
│
├── tests/                   # Test files
│   └── test_*.py
│
└── results/                 # Analysis results
    └── (chemical folders)
```

## Files Needed to Run the App

**Required**:
- `app.py` - Main application
- `config.py` - Configuration
- All core modules listed above
- `requirements.txt` - Dependencies

**Optional**:
- `scripts/` - Utility scripts for post-processing
- `docs/` - Documentation and explanations
- `tests/` - Test files

## Running the App

Simply run:
```bash
python app.py
```

All core modules are in the root directory and will be imported automatically.

## Utility Scripts

Scripts in `scripts/` folder are for:
- Creating presentations
- Preparing results for reload
- Comparing results
- Performance optimization
- Testing and validation

These are **not required** to run the main application.
