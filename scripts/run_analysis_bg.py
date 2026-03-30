#!/usr/bin/env python3
"""Run Acetaminophen analysis in background"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import traceback

from app import analyze_chemical

if __name__ == "__main__":
    try:
        print("="*80)
        print("Starting Acetaminophen Analysis")
        print("="*80)
        result = analyze_chemical(
            chemical_name="Acetaminophen",
            model_names=["llama3.2", "mixtral"],
            enable_rob=True,
            enable_certainty=True
        )
        print("\n" + "="*80)
        print("✅ Analysis Complete!")
        print("="*80)
        print("\nNext step: Run validation with:")
        print("  python run_validation_nihms.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)
