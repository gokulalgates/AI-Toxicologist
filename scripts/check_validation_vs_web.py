"""
Compare validation script vs web interface execution paths
"""


print("="*80)
print("COMPARING VALIDATION SCRIPT vs WEB INTERFACE")
print("="*80)
print()

# Check 1: How validation script calls analyze_chemical
print("1. VALIDATION SCRIPT CALL:")
print("-" * 80)
with open('run_validation_nihms.py') as f:
    validation_lines = f.readlines()
    for i, line in enumerate(validation_lines):
        if 'analyze_chemical' in line and 'def' not in line:
            print(f"Line {i+1}: {line.strip()}")
            # Show context
            for j in range(max(0, i-3), min(len(validation_lines), i+5)):
                if j != i:
                    print(f"  {j+1}: {validation_lines[j].rstrip()}")
            break

print("\n2. WEB INTERFACE CALL:")
print("-" * 80)
with open('app.py') as f:
    app_lines = f.readlines()
    for i, line in enumerate(app_lines):
        if 'return analyze_chemical' in line and 'analyze_with_progress' in '\n'.join(app_lines[max(0, i-20):i]):
            print(f"Line {i+1}: {line.strip()}")
            # Show function definition
            for j in range(max(0, i-20), i+1):
                if 'def analyze_with_progress' in app_lines[j]:
                    print(f"\nFunction definition (line {j+1}):")
                    for k in range(j, min(len(app_lines), j+18)):
                        print(f"  {k+1}: {app_lines[k].rstrip()}")
                    break
            break

print("\n3. CHECKING analyze_chemical FUNCTION PARAMETERS:")
print("-" * 80)
for i, line in enumerate(app_lines):
    if 'def analyze_chemical' in line:
        print(f"Function definition (line {i+1}):")
        for j in range(i, min(len(app_lines), i+10)):
            print(f"  {j+1}: {app_lines[j].rstrip()}")
        break

print("\n4. CHECKING IF PROGRESS PARAMETER AFFECTS EXECUTION:")
print("-" * 80)
# Check if progress parameter is used in a way that could affect results
progress_usage = []
for i, line in enumerate(app_lines):
    if 'progress' in line.lower() and 'def analyze_chemical' not in line:
        # Check if it's actually used in a way that could affect logic
        if 'progress(' in line or 'if progress' in line:
            progress_usage.append((i+1, line.strip()))
            if len(progress_usage) >= 5:
                break

print("Progress parameter usage (first 5 instances):")
for line_num, line_text in progress_usage:
    print(f"  Line {line_num}: {line_text}")

print("\n5. CHECKING CONFIG DIFFERENCES:")
print("-" * 80)
# Check if there are any config differences
from config import get_config

config = get_config()
print(f"enable_enhanced_prompts: {config.analysis.enable_enhanced_prompts}")
print(f"prompt_mode: {config.analysis.prompt_mode}")
print(f"enable_rag: {config.analysis.enable_rag}")
print(f"enable_hierarchical: {config.analysis.enable_hierarchical}")

print("\n6. CHECKING MODEL NAMES:")
print("-" * 80)
# Check what models validation uses vs what web interface might use
validation_models = None
for i, line in enumerate(validation_lines):
    if 'model_names' in line and ('=' in line or '[' in line):
        print(f"Validation models (line {i+1}): {line.strip()}")
        if '["' in line or "['" in line:
            validation_models = line.strip()
        break

print("\n7. KEY FINDINGS:")
print("-" * 80)
print("Both call analyze_chemical() with:")
print("  - chemical_name (lowercased in function)")
print("  - model_names (list)")
print("  - enable_rob (bool)")
print("  - enable_certainty (bool)")
print("  - progress (optional, only in web interface)")
print()
print("The progress parameter should NOT affect results, only UI updates.")
print("Both should use the same code path for analysis.")
