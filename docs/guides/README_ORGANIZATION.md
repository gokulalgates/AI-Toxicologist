# Folder Organization Guide

## 📁 Current Structure

```
Key_char_liver/
│
├── 🚀 CORE APPLICATION FILES (Run the app)
│   ├── app.py                    # Main application - RUN THIS
│   ├── config.py                 # Configuration settings
│   ├── requirements.txt          # Python dependencies
│   └── README.md                 # Main documentation
│
├── 📦 CORE MODULES (Required by app.py)
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
├── 🔧 scripts/                   # Utility scripts (NOT needed to run app)
│   ├── create_presentation.py
│   ├── create_results_presentation.py
│   ├── prepare_all_results_for_reload.py
│   ├── optimize_performance.py
│   ├── compare_with_gold_standard.py
│   └── ... (other utility scripts)
│
├── 📚 docs/
│   ├── presentations/            # Presentation files and scripts
│   │   ├── AI_Toxicologist_Presentation.pptx
│   │   ├── PRESENTATION_SCRIPT.md
│   │   └── SCIENTIFIC_PRESENTATION_*.md
│   │
│   ├── explanations/             # Detailed technical explanations
│   │   ├── HOW_LLM_DETERMINES_KC_STATUS.md
│   │   ├── PROGRAMMATIC_IMPLEMENTATION.md
│   │   └── HEATMAP_AND_ROB_EXPLANATION.md
│   │
│   └── guides/                   # User guides and documentation
│       ├── PERFORMANCE_OPTIMIZATION.md
│       ├── API_DOCUMENTATION.md
│       └── ... (other guides)
│
├── 🗂️ utilities/                 # Additional utilities
│   └── (shell scripts, text files, etc.)
│
├── 🧪 tests/                     # Test files
│   └── test_*.py
│
└── 📊 results/                   # Analysis results
    └── (chemical folders with analysis outputs)
```

## 🎯 Quick Start

**To run the application:**
```bash
python app.py
```

**All core modules are in the root directory** - no need to modify Python path.

## 📋 File Categories

### ✅ Core Files (Keep in Root)
These files are **required** to run the app:
- `app.py` - Main application
- `config.py` - Configuration
- All `*_models.py`, `*_utils.py`, `*_enhanced.py` files
- All prompt and processing modules

### 🔧 Utility Scripts (Moved to `scripts/`)
These are helper scripts for post-processing:
- Presentation generators
- Result preparation scripts
- Comparison/validation scripts
- Performance optimization scripts

### 📚 Documentation (Moved to `docs/`)
- **presentations/**: PowerPoint files and presentation scripts
- **explanations/**: Detailed technical explanations
- **guides/**: User guides and documentation

### 🗂️ Utilities (Moved to `utilities/`)
- Shell scripts
- Text files
- Other utilities

## 🔍 Finding Files

**Need to create a presentation?**
→ Check `scripts/create_presentation.py` or `docs/presentations/`

**Want to understand how KC status is determined?**
→ Check `docs/explanations/HOW_LLM_DETERMINES_KC_STATUS.md`

**Looking for performance tips?**
→ Check `docs/guides/PERFORMANCE_OPTIMIZATION.md`

**Need to compare results?**
→ Check `scripts/compare_with_gold_standard.py`

## 📝 Notes

- **Core modules stay in root** for easy imports
- **Utility scripts** are organized but not required
- **Documentation** is categorized for easy access
- **Tests** remain in `tests/` folder

## 🚨 Important

**Do NOT move core modules** (files imported by `app.py`) - they must stay in the root directory for imports to work.
