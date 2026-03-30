# Validation Script vs Web Interface Comparison

## Summary

Both the validation script (`run_validation_nihms.py`) and the web interface (`app.py`) call the same function `analyze_chemical()` with identical parameters (except for the optional `progress` parameter in the web interface, which only affects UI updates).

## Code Path Comparison

### Validation Script Call
```python
# Line 87-92 in run_validation_nihms.py
results = analyze_chemical(
    chemical_name=chemical_name,
    model_names=model_names or ["llama3.2", "mixtral"],
    enable_rob=True,
    enable_certainty=True
)
```

### Web Interface Call
```python
# Line 2169 in app.py (inside analyze_with_progress function)
return analyze_chemical(chem, models, rob, cert, progress)
```

## Key Findings

1. **Same Function**: Both call `analyze_chemical()` from `app.py` (line 1176)
2. **Same Parameters**: 
   - `chemical_name` (lowercased inside function at line 1187)
   - `model_names` (list of models)
   - `enable_rob` (boolean)
   - `enable_certainty` (boolean)
   - `progress` (optional, only in web interface - does NOT affect analysis logic)

3. **Same Code Path**: Both should execute identical analysis logic

4. **Configuration**: Both use the same config system (`get_config()`)
   - `enable_enhanced_prompts: True`
   - `prompt_mode: "enhanced"`
   - `enable_rag: True`
   - `enable_hierarchical: True`

5. **Acetaminophen Detection**: The acetaminophen-specific prompt selection logic (lines 597-613) checks:
   - `chemical_name.lower()` 
   - `search_terms` (passed to `analyze_abstract_with_llm`)
   - Both should work correctly

## Potential Differences

### 1. Model Selection
- **Validation**: Uses `model_names or ["llama3.2", "mixtral"]` (defaults to 2 models)
- **Web Interface**: Uses user-selected models from checkboxes (could be 1 or more models)

**Impact**: If web interface uses different models, results could differ, but shouldn't cause all KCs to be NOT_MENTIONED.

### 2. Chemical Name Format
- **Validation**: May pass "Acetaminophen" (capitalized)
- **Web Interface**: User likely types "acetaminophen" (lowercase)

**Impact**: Both are lowercased at line 1187, so this shouldn't matter.

### 3. Environment Variables
- **Validation**: May run in different environment
- **Web Interface**: Runs in Gradio server environment

**Impact**: Could affect config if environment variables are set differently.

## Current Issue

The web interface shows **0/26 papers supporting any KC** for Acetaminophen, while validation is reported to work correctly.

## Diagnostic Steps Taken

1. ✅ Verified both call same function
2. ✅ Verified acetaminophen detection logic
3. ✅ Verified enhanced prompts are enabled
4. ✅ Checked study records structure (all KCs show NOT_MENTIONED)
5. ✅ Found that some records have "No reasoning provided" (suggests models aren't analyzing)

## Next Steps to Investigate

1. **Check if validation actually works**: Run validation script and verify it produces correct results
2. **Compare model outputs**: Test what models actually output for acetaminophen abstracts
3. **Check for errors**: Look for silent failures or exceptions in the web interface
4. **Verify prompt selection**: Add logging to confirm acetaminophen-specific prompts are being used
5. **Check consolidation logic**: Verify multi-reviewer consolidation isn't losing KC statuses

## Recommendations

1. Add debug logging to `analyze_abstract_with_llm` to see:
   - Which prompt is being used
   - Raw LLM response
   - Parsed KC statuses before consolidation

2. Test a single abstract manually to see if the issue is:
   - Model output (models not detecting KCs)
   - Parsing (models detect but parsing fails)
   - Consolidation (parsing works but consolidation loses data)

3. Compare actual validation run results with web interface results side-by-side
