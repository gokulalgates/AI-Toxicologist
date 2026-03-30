# Bug Fix Summary: KC Status Not Being Extracted

## Problem
The web interface (and validation script) were showing all KCs as `NOT_MENTIONED` for Acetaminophen, even though:
1. ✅ Acetaminophen detection was working correctly
2. ✅ Acetaminophen-specific prompts were being used
3. ✅ LLM models were returning correct KC statuses (SUPPORTED, etc.)

## Root Cause
**Location**: `app.py` line 904

The bug was in the `analyze_abstract_with_llm` function when converting the Pydantic result object to a dictionary. The code was using the wrong key name:

**Before (BUGGY)**:
```python
kc_dict[f"{kc_key}_status"] = status  # This created "KC1_status" (uppercase)
```

**After (FIXED)**:
```python
kc_dict[status_key] = status  # This creates "kc1_status" (lowercase)
```

The issue was that:
- `kc_key` = `"KC1"` (uppercase)
- `status_key` = `"kc1_status"` (lowercase)
- The code was using `f"{kc_key}_status"` which created `"KC1_status"` instead of `"kc1_status"`

## Impact
- All downstream code expects lowercase `kc1_status`, `kc2_status`, etc.
- The consolidation logic in `multi_reviewer.py` looks for `kc{i}_status` (lowercase)
- The summary generation looks for `kc{i}_status` (lowercase)
- Because the keys didn't match, all KC statuses appeared as `NOT_MENTIONED`

## Fix Applied
Changed line 904 in `app.py` from:
```python
kc_dict[f"{kc_key}_status"] = status
```
to:
```python
kc_dict[status_key] = status
```

## Verification
Tested with a simple acetaminophen abstract and confirmed:
- ✅ KC1: SUPPORTED
- ✅ KC2: SUPPORTED  
- ✅ KC5: SUPPORTED
- ✅ KC7: SUPPORTED
- ✅ KC8: SUPPORTED
- ✅ KC12: SUPPORTED

## Additional Debug Logging
Added debug logging to show:
- When acetaminophen is detected
- Which prompt mode is being used
- Which prompt is selected

This will help diagnose similar issues in the future.

## Next Steps
1. Re-run the full analysis for Acetaminophen to verify end-to-end
2. Check if this affects other chemicals (likely affects all)
3. Consider adding unit tests to catch this type of key mismatch
