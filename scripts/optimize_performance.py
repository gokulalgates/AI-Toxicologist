"""
Quick performance optimization script
Run this to apply fast performance settings
"""

from config import AnalysisConfig, AppConfig, LLMConfig, SearchConfig, get_config, set_config


def apply_fast_settings():
    """Apply fast performance settings"""
    config = get_config()

    # Create optimized config
    fast_config = AppConfig(
        search=SearchConfig(
            max_abstracts_initial=50,  # Reduced from 100
            max_abstracts_analyze=10,  # Reduced from 20
            max_search_terms=8,  # Reduced from 10
        ),
        llm=LLMConfig(
            enable_parallel=True,
            max_workers=8,  # Explicit workers
            gpu_layers=50,  # More GPU layers if VRAM available
            use_gpu=True,
            temperature=0.1,
        ),
        analysis=AnalysisConfig(
            enable_rag=False,  # Disable for speed
            enable_hierarchical=False,  # Disable for speed
            enable_rob_default=True,  # Keep enabled (can disable in UI)
            enable_certainty_default=True,  # Keep enabled (can disable in UI)
            enable_enhanced_prompts=True,
            prompt_mode="enhanced",
        ),
        output=config.output,
        ui=config.ui,
        debug=config.debug,
        log_level=config.log_level,
    )

    set_config(fast_config)
    print("✅ Fast performance settings applied!")
    print("\nSettings:")
    print(f"  • Max abstracts analyzed: {fast_config.search.max_abstracts_analyze}")
    print(f"  • Parallel workers: {fast_config.llm.max_workers}")
    print(f"  • GPU layers: {fast_config.llm.gpu_layers}")
    print(f"  • RAG: {'Enabled' if fast_config.analysis.enable_rag else 'Disabled'}")
    print(f"  • Hierarchical: {'Enabled' if fast_config.analysis.enable_hierarchical else 'Disabled'}")
    return fast_config

def apply_balanced_settings():
    """Apply balanced speed/quality settings"""
    config = get_config()

    balanced_config = AppConfig(
        search=SearchConfig(
            max_abstracts_initial=75,
            max_abstracts_analyze=15,
            max_search_terms=8,
        ),
        llm=LLMConfig(
            enable_parallel=True,
            max_workers=6,
            gpu_layers=40,
            use_gpu=True,
        ),
        analysis=config.analysis,  # Keep all analysis features
        output=config.output,
        ui=config.ui,
        debug=config.debug,
        log_level=config.log_level,
    )

    set_config(balanced_config)
    print("✅ Balanced performance settings applied!")
    return balanced_config

def apply_maximum_speed_settings():
    """Apply maximum speed settings (fastest, but lower quality)"""
    config = get_config()

    max_speed_config = AppConfig(
        search=SearchConfig(
            max_abstracts_initial=30,
            max_abstracts_analyze=5,  # Very few abstracts
            max_search_terms=5,
        ),
        llm=LLMConfig(
            enable_parallel=True,
            max_workers=10,  # More workers
            gpu_layers=50,  # Max GPU layers
            use_gpu=True,
        ),
        analysis=AnalysisConfig(
            enable_rag=False,
            enable_hierarchical=False,
            enable_rob_default=False,  # Disable RoB
            enable_certainty_default=False,  # Disable certainty
            enable_enhanced_prompts=True,
        ),
        output=config.output,
        ui=config.ui,
        debug=config.debug,
        log_level=config.log_level,
    )

    set_config(max_speed_config)
    print("✅ Maximum speed settings applied!")
    print("⚠️  Warning: Quality may be reduced with these settings")
    return max_speed_config

if __name__ == "__main__":
    import sys

    print("="*80)
    print("PERFORMANCE OPTIMIZATION")
    print("="*80)
    print("\nChoose optimization level:")
    print("1. Fast (recommended) - 2-3x faster, minimal quality loss")
    print("2. Balanced - 1.5-2x faster, maintains quality")
    print("3. Maximum Speed - 5-10x faster, reduced quality")
    print("\nCurrent settings will be shown, then you can choose.")

    current = get_config()
    print("\nCurrent Settings:")
    print(f"  • Max abstracts analyzed: {current.search.max_abstracts_analyze}")
    print(f"  • Parallel workers: {current.llm.max_workers}")
    print(f"  • GPU layers: {current.llm.gpu_layers}")
    print(f"  • RAG: {'Enabled' if current.analysis.enable_rag else 'Disabled'}")

    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        choice = input("\nEnter choice (1-3) or press Enter for Fast: ").strip() or "1"

    if choice == "1":
        apply_fast_settings()
    elif choice == "2":
        apply_balanced_settings()
    elif choice == "3":
        apply_maximum_speed_settings()
    else:
        print("Invalid choice, applying Fast settings...")
        apply_fast_settings()

    print("\n" + "="*80)
    print("✅ Settings applied! Restart the app to use new settings.")
    print("="*80)
