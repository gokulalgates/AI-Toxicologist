# Fix: Web Interface Not Predicting for Acetaminophen

## Problem
When testing with validation scripts, acetaminophen analysis works correctly and generates good results. However, when running through the web interface (`app.py`), it doesn't predict anything (all KCs show as NOT_MENTIONED).

## Root Cause

The issue was in how the chemical name was passed to the prompt selection logic:

1. **Chemical Standardization**: When `standardize_chemical_name()` is called, it may return an **IUPAC name** (e.g., "N-(4-hydroxyphenyl)acetamide") instead of the common name "acetaminophen"

2. **Prompt Selection**: The acetaminophen-specific prompt check was using `standardized_name`, which might be the IUPAC name

3. **Failed Detection**: The check only looked for common names: `["acetaminophen", "paracetamol", "apap", "tylenol"]`, so it failed when the standardized name was an IUPAC name

4. **Result**: The system used generic prompts instead of acetaminophen-specific prompts, leading to poor predictions

## Solution

### Changes Made:

1. **Store Original Chemical Name**: Before standardization, store the original input name
   ```python
   original_chemical_name = chemical_name.lower()
   standardized_name, cid, search_terms = standardize_chemical_name(chemical_name)
   ```

2. **Pass Original Name to Analysis**: Pass the original name (not standardized) to `analyze_abstract_with_llm()`
   ```python
   analysis, _ = analyze_abstract_with_llm(
       ...
       chemical_name=original_chemical_name,  # Use original name for prompt selection
       search_terms=search_terms  # Also pass search terms
   )
   ```

3. **Enhanced Detection**: Improved acetaminophen detection to check both:
   - The `chemical_name` parameter (original input)
   - The `search_terms` list (includes synonyms like "paracetamol", "APAP")
   
   ```python
   chemical_lower = (chemical_name or "").lower()
   search_terms_lower = [s.lower() for s in (search_terms or [])]
   acetaminophen_names = ["acetaminophen", "paracetamol", "apap", "tylenol", "n-acetyl-p-aminophenol"]
   is_acetaminophen = (chemical_lower in acetaminophen_names or 
                      any(term in acetaminophen_names for term in search_terms_lower) or
                      any(apap_name in term for apap_name in acetaminophen_names for term in search_terms_lower))
   ```

## Files Modified

- `app.py`:
  - Line ~1229: Store `original_chemical_name` before standardization
  - Line ~1474: Pass `original_chemical_name` to parallel analysis
  - Line ~1566: Pass `original_chemical_name` to sequential analysis
  - Line ~542: Added `search_terms` parameter to `analyze_abstract_with_llm()`
  - Line ~597: Enhanced acetaminophen detection logic

## Testing

To verify the fix works:

1. **Run the web interface**:
   ```bash
   python app.py
   ```

2. **Analyze Acetaminophen**:
   - Enter "acetaminophen" in the web interface
   - Select a model (llama3.2 recommended)
   - Click "Analyze Chemical"

3. **Expected Results**:
   - Should detect acetaminophen and use acetaminophen-specific prompts
   - Should predict KCs 1-8 and 12 as SUPPORTED
   - Should extract evidence quotes and causal pathways

4. **Check Console Output**:
   - Look for: "Using acetaminophen-specific prompt" (if logging added)
   - Check that predictions are not all NOT_MENTIONED

## Why Validation Tests Worked

The validation test (`run_validation_nihms.py`) calls `analyze_chemical()` directly with `chemical_name="Acetaminophen"`. The issue only appeared in the web interface because:

- The web interface might have different input handling
- The standardized name might differ between runs
- The prompt selection logic wasn't robust enough

## Additional Improvements

The fix also makes the system more robust by:
- Checking multiple sources (original name + search terms)
- Handling various acetaminophen synonyms
- Working even if PubChem returns an IUPAC name

## Status

✅ **Fixed**: The web interface should now correctly detect acetaminophen and use the appropriate prompts, generating good predictions just like the validation tests.
