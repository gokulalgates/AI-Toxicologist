"""
Compare validation script vs web interface code paths
"""


def compare_code_paths():
    """Compare how validation script and web interface call analyze_chemical"""

    print("="*80)
    print("COMPARING VALIDATION SCRIPT vs WEB INTERFACE")
    print("="*80)
    print()

    # Read validation script
    with open('run_validation_nihms.py') as f:
        validation_code = f.read()

    # Read web interface code
    with open('app.py') as f:
        app_code = f.read()

    print("1. VALIDATION SCRIPT CALL:")
    print("-" * 80)
    # Find the analyze_chemical call in validation
    import re
    validation_call = re.search(r'analyze_chemical\([^)]+\)', validation_code)
    if validation_call:
        print(validation_call.group())
        # Show context
        lines = validation_code.split('\n')
        for i, line in enumerate(lines):
            if 'analyze_chemical' in line:
                print(f"   Line {i+1}: {line.strip()}")
                # Show a few lines before and after
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if j != i:
                        print(f"   Line {j+1}: {lines[j]}")
                break
    print()

    print("2. WEB INTERFACE CALL:")
    print("-" * 80)
    # Find analyze_with_progress function
    web_call = re.search(r'return analyze_chemical\([^)]+\)', app_code)
    if web_call:
        print(web_call.group())
        # Show context
        lines = app_code.split('\n')
        for i, line in enumerate(lines):
            if 'return analyze_chemical' in line and 'analyze_with_progress' in lines[max(0, i-20):i]:
                print(f"   Line {i+1}: {line.strip()}")
                # Show function definition
                for j in range(max(0, i-20), i):
                    if 'def analyze_with_progress' in lines[j]:
                        print(f"\n   Function definition (line {j+1}):")
                        for k in range(j, min(len(lines), j+15)):
                            print(f"   Line {k+1}: {lines[k]}")
                        break
                break
    print()

    print("3. KEY DIFFERENCES:")
    print("-" * 80)
    print("Validation script:")
    print("  - Calls: analyze_chemical(chemical_name='Acetaminophen', model_names=['llama3.2', 'mixtral'], enable_rob=True, enable_certainty=True)")
    print("  - No progress parameter")
    print("  - Chemical name: 'Acetaminophen' (capitalized)")
    print()
    print("Web interface:")
    print("  - Calls: analyze_chemical(chem, models, rob, cert, progress)")
    print("  - Has progress parameter (Gradio Progress)")
    print("  - Chemical name: user input (likely lowercase 'acetaminophen')")
    print()

    print("4. CHECKING analyze_chemical FUNCTION:")
    print("-" * 80)
    # Check if chemical_name.lower() affects things
    lines = app_code.split('\n')
    for i, line in enumerate(lines):
        if 'def analyze_chemical' in line:
            print(f"   Function starts at line {i+1}")
            # Show first 30 lines of function
            print("\n   First 30 lines of analyze_chemical:")
            for j in range(i+1, min(len(lines), i+31)):
                print(f"   {j+1}: {lines[j]}")
            break

    print()
    print("5. CHECKING PROMPT SELECTION:")
    print("-" * 80)
    # Check how acetaminophen detection works
    for i, line in enumerate(lines):
        if 'is_acetaminophen' in line or 'acetaminophen_names' in line:
            print(f"   Line {i+1}: {line.strip()}")
            # Show context
            for j in range(max(0, i-5), min(len(lines), i+10)):
                if j != i:
                    marker = ">>>" if abs(j-i) <= 2 else "   "
                    print(f"{marker} {j+1}: {lines[j]}")

if __name__ == "__main__":
    compare_code_paths()
