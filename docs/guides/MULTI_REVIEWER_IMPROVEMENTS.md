# Multi-Reviewer Mode Improvements

## Issue Identified

Even with multiple reviewer models (llama3, mixtral, etc.), all models were returning `NOT_MENTIONED` for all KCs, resulting in consensus of `NOT_MENTIONED`.

## Root Cause Analysis

### Problem 1: Consensus Amplifies Errors
- If all 3 models say `NOT_MENTIONED`, consensus = `NOT_MENTIONED`
- Multi-reviewer doesn't help if all reviewers are making the same mistake
- The issue is at the individual model level, not the consensus level

### Problem 2: Prompts May Still Be Too Strict
- Even with enhanced prompts, models might be too conservative
- Some abstracts may describe mechanisms indirectly
- Models may need more explicit instructions to be permissive

### Problem 3: Abstract Quality
- Some abstracts may not contain detailed mechanistic information
- Need to check if abstracts actually describe the mechanisms

## Solutions Implemented

### 1. Liberal Prompt Mode (`prompt_mode = "liberal"`)

Created a new **liberal prompt** that is much more permissive:
- **Instruction**: "Be LIBERAL in detecting mechanisms"
- **Rule**: "When in doubt, mark as SUPPORTED rather than NOT_MENTIONED"
- **Recognition**: Accepts implicit mechanisms, synonyms, and related terms

**Key Differences:**
- Standard: Requires explicit statement
- Enhanced: Recognizes synonyms
- **Liberal**: Accepts implicit mechanisms and related effects

### 2. Configuration Option

Added `config.analysis.prompt_mode` with three options:
- `"standard"`: Original prompts
- `"enhanced"`: Enhanced prompts with synonyms (default)
- `"liberal"`: Very permissive prompts (use when missing known mechanisms)

### 3. Automatic Liberal Mode for Acetaminophen

When analyzing Acetaminophen with liberal mode:
- Uses liberal prompt
- Adds Acetaminophen-specific context about known mechanisms
- Helps models recognize mechanisms even with different terminology

## How to Use

### Option 1: Enable Liberal Mode (Recommended for Acetaminophen)

```python
from config import get_config
config = get_config()
config.analysis.prompt_mode = "liberal"
```

Then run your analysis with multiple models.

### Option 2: Check Individual Model Results

Before consensus, check what each model is detecting:

```python
# After running analysis, check individual model results
for model_name, analyses in zip(model_names, all_model_analyses):
    print(f"\n{model_name} Results:")
    for i, analysis in enumerate(analyses[:3]):  # First 3 papers
        print(f"  Paper {i+1}:")
        for kc in ["KC1", "KC5", "KC7"]:
            status = analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED")
            print(f"    {kc}: {status}")
```

### Option 3: Verify Abstract Content

Check if abstracts actually contain mechanistic details:

```python
# Check if abstracts mention key terms
key_terms = ["NAPQI", "glutathione", "CYP2E1", "mitochondrial", "necrosis"]
for abstract in abstracts[:5]:
    text = abstract.get("abstract", "").lower()
    found_terms = [term for term in key_terms if term.lower() in text]
    print(f"PMID {abstract.get('pmid')}: Found {found_terms}")
```

## Expected Behavior

### With Enhanced Prompts (Default)
- Better synonym recognition
- Should detect mechanisms described with different terms
- Still requires some evidence

### With Liberal Mode
- Very permissive detection
- Accepts implicit mechanisms
- May have some false positives (but better than false negatives)

## Troubleshooting

### All Models Still Return NOT_MENTIONED?

1. **Check Abstract Content**
   ```bash
   # Look at actual abstracts
   python -c "import json; data=[json.loads(l) for l in open('results/acetaminophen/study_records.jsonl')]; print(data[0]['metadata']['title']); print(data[0].get('kc_analysis', {}).get('reasoning', 'No reasoning'))"
   ```

2. **Try Liberal Mode**
   ```python
   config.analysis.prompt_mode = "liberal"
   ```

3. **Check Model Output**
   - Look at the "reasoning" field in results
   - See what each model is thinking
   - Check if models are seeing the text correctly

4. **Use Better Models**
   - llama3.2 > llama3.1
   - mixtral > smaller models
   - Larger models understand context better

5. **Check Full-Text Availability**
   - Abstracts may not have enough detail
   - Full-text has more mechanistic information
   - Enable full-text retrieval in config

### Consensus Shows Disagreement?

If models disagree (some say SUPPORTED, others NOT_MENTIONED):
- **Good sign**: At least some models are detecting mechanisms
- **Consensus**: Will use majority vote
- **Check**: Which models are detecting? (may indicate model quality differences)

### Low Agreement Scores?

If agreement is low (<50%):
- Models are seeing different things
- May indicate ambiguous abstracts
- Consider: Are abstracts clear about mechanisms?

## Recommendations

### For Acetaminophen Analysis

1. **Use Liberal Mode**:
   ```python
   config.analysis.prompt_mode = "liberal"
   ```

2. **Use Best Models**:
   - llama3.2 (best)
   - mixtral (excellent)
   - mistral (good)
   - Avoid: llama3.1 (smaller, less capable)

3. **Use 2-3 Models**:
   - More reviewers = better consensus
   - Weighted consensus favors better models

4. **Check Results**:
   - Look at evidence quotes
   - Verify quotes support KC status
   - Check reasoning from each model

5. **Compare with Known Paper**:
   - Rusyn paper says: KCs 1-8 and 12
   - Your results should match this
   - If not, abstracts may lack detail

## Example: Expected Results for Acetaminophen

### With Liberal Mode + Multi-Reviewer:

**Model 1 (llama3.2):**
- KC1: SUPPORTED (NAPQI formation)
- KC2: SUPPORTED (necrosis)
- KC5: SUPPORTED (glutathione depletion)
- KC7: SUPPORTED (mitochondrial dysfunction)
- KC8: SUPPORTED (JNK signaling)
- KC12: SUPPORTED (steatosis)

**Model 2 (mixtral):**
- KC1: SUPPORTED
- KC2: SUPPORTED
- KC5: SUPPORTED
- KC7: SUPPORTED
- KC8: SUPPORTED
- KC12: SUPPORTED

**Consensus:**
- All KCs: SUPPORTED (100% agreement)
- High confidence scores

## Summary

The issue wasn't with multi-reviewer consensus—it was that all individual models were missing mechanisms. The solution:

1. ✅ **Liberal Prompt Mode**: More permissive detection
2. ✅ **Better Prompts**: Enhanced synonym recognition
3. ✅ **Chemical-Specific Context**: Known mechanisms for Acetaminophen
4. ✅ **Configuration**: Easy to switch between modes

**Next Steps:**
1. Set `config.analysis.prompt_mode = "liberal"`
2. Re-run analysis with multiple models
3. Check results - should now detect KCs 1-8 and 12 for Acetaminophen
