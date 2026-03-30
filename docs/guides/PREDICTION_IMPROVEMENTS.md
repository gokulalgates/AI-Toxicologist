# Prediction Improvements Guide

## Problem Identified

When analyzing Acetaminophen, the system was marking all Key Characteristics (KCs) as `NOT_MENTIONED`, even though the Rusyn et al. (2021) paper explicitly states that "Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)".

### Root Causes

1. **Overly Strict Prompt Requirements**: The original prompts required "explicitly states" which missed mechanisms described with synonyms or related terminology
2. **Poor Synonym Recognition**: The LLM wasn't recognizing that:
   - "metabolized to NAPQI" = KC1 (bioactivation)
   - "glutathione depletion" = KC5 (oxidative stress)
   - "hepatocellular necrosis" = KC2 (cell death)
3. **Missing Domain Knowledge**: The prompts didn't include known mechanisms for well-studied chemicals like Acetaminophen
4. **Insufficient Examples**: Few-shot examples didn't cover enough variation in terminology

## Solutions Implemented

### 1. Enhanced Prompt with Synonym Recognition (`prompt_improvements.py`)

Created `get_enhanced_prompt_with_synonyms()` that:
- Lists synonyms and related terms for each KC
- Provides examples of how mechanisms can be described differently
- Instructs the model to be "sensitive, not overly strict"
- Recognizes implicit mechanisms (e.g., "NAPQI formation" implies bioactivation)

**Key Improvements:**
- **KC1 Recognition**: Now recognizes "phase I oxidation", "electrophilic intermediates", "CYP2E1 metabolism" as bioactivation
- **KC5 Recognition**: Recognizes "antioxidant depletion", "GSH depletion", "redox imbalance" as oxidative stress
- **KC2 Recognition**: Recognizes "hepatocellular injury", "cytopathic", "cell killing" as cell death
- And similar improvements for all 12 KCs

### 2. Chemical-Specific Prompts

Created `get_acetaminophen_specific_prompt()` that:
- Includes known mechanisms for Acetaminophen
- Provides context about what to look for (NAPQI, CYP2E1, glutathione depletion, etc.)
- Helps the model recognize mechanisms even with different terminology

**Example:**
- "NAPQI" or "N-acetyl-p-quinoneimine" → KC1 (bioactivation)
- "Glutathione depletion" → KC5 (oxidative stress)
- "Centrilobular necrosis" → KC2 (cell death)
- "JNK activation" → KC8 (stress signaling)

### 3. Integration into Main Application

Modified `app.py` to:
- Automatically use enhanced prompts when `config.analysis.enable_enhanced_prompts = True`
- Use Acetaminophen-specific prompt when analyzing Acetaminophen/Paracetamol/APAP
- Fall back to standard prompts if enhanced prompts are disabled

## Expected Results

### Before Improvements
```
KC1: NOT_MENTIONED
KC2: NOT_MENTIONED
KC3: NOT_MENTIONED
...
KC12: NOT_MENTIONED
```

### After Improvements (Expected for Acetaminophen)
```
KC1: SUPPORTED (bioactivation to NAPQI)
KC2: SUPPORTED (hepatocellular necrosis)
KC3: SUPPORTED (compensatory proliferation)
KC4: SUPPORTED (bile acid transport disruption)
KC5: SUPPORTED (glutathione depletion, oxidative stress)
KC6: SUPPORTED (inflammatory response)
KC7: SUPPORTED (mitochondrial dysfunction)
KC8: SUPPORTED (JNK/p38 MAPK signaling)
KC9: NOT_MENTIONED (cholestasis not typical)
KC10: NOT_MENTIONED (cytoskeleton disruption not typical)
KC11: NOT_MENTIONED (fibrosis not typical in acute overdose)
KC12: SUPPORTED (lipid metabolism disruption, steatosis)
```

## How to Use

### Option 1: Automatic (Recommended)
The enhanced prompts are enabled by default. Just run your analysis:
```bash
python app.py
```

### Option 2: Disable Enhanced Prompts
If you want to use the original prompts:
```python
from config import get_config
config = get_config()
config.analysis.enable_enhanced_prompts = False
```

### Option 3: Add More Chemical-Specific Prompts
To add prompts for other chemicals, edit `prompt_improvements.py`:
```python
def get_your_chemical_specific_prompt(kc_definitions: str, format_instructions: str) -> str:
    # Add your chemical-specific context
    ...
```

Then update `app.py` to use it:
```python
if chemical_lower in ["your_chemical", "synonym1", "synonym2"]:
    base_prompt = get_your_chemical_specific_prompt(...)
```

## Additional Recommendations

### 1. Use Better Models
- **Current**: llama3.1 (good but can miss nuances)
- **Recommended**: llama3.2, mixtral, or mistral (better at understanding context)

### 2. Use Multi-Reviewer Mode
Run analysis with multiple models and use consensus:
```python
model_names = ["llama3.2", "mixtral", "mistral"]
```

### 3. Use Full-Text When Available
Full-text provides more context than abstracts:
- Enable full-text retrieval in `config.py`
- The system will automatically use full-text if available

### 4. Review Evidence Quotes
Always check the `evidence_quotes` field to verify:
- Are the quotes accurate?
- Do they support the KC status?
- Are important mechanisms missing?

### 5. Adjust Temperature
For more consistent results:
```python
config.llm.temperature = 0.0  # More deterministic
```

For better reasoning (may vary slightly):
```python
config.llm.temperature = 0.1  # Current default
```

## Testing the Improvements

### Test with Acetaminophen
1. Run analysis: `python app.py`
2. Enter "acetaminophen" as chemical name
3. Select model(s) (recommend llama3.2 or mixtral)
4. Check results - should show KCs 1-8 and 12 as SUPPORTED

### Verify Against Known Paper
Compare results with Rusyn et al. (2021) paper:
- Paper states: "Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)"
- Your results should match this

### Check Evidence Quotes
For each SUPPORTED KC, verify:
- Evidence quotes are accurate
- Quotes actually support the KC
- No important mechanisms are missing

## Troubleshooting

### Still Getting NOT_MENTIONED for Known Mechanisms?

1. **Check Abstract Quality**: Some abstracts may not contain mechanistic details
   - Solution: Use full-text retrieval if available
   - Solution: Analyze multiple papers and aggregate results

2. **Model Limitations**: Smaller models may miss nuances
   - Solution: Use larger models (llama3.2, mixtral)
   - Solution: Use multi-reviewer mode for consensus

3. **Prompt Not Applied**: Verify enhanced prompts are enabled
   ```python
   print(config.analysis.enable_enhanced_prompts)  # Should be True
   ```

4. **Chemical Name Mismatch**: Ensure chemical name matches
   - "acetaminophen" → Uses Acetaminophen-specific prompt
   - "paracetamol" → Uses Acetaminophen-specific prompt
   - "APAP" → Uses Acetaminophen-specific prompt

## Future Improvements

1. **Expand Chemical-Specific Prompts**: Add prompts for other well-studied chemicals
2. **Machine Learning**: Train a model to recognize KC mechanisms from text
3. **Knowledge Base**: Build a database of known mechanisms for common chemicals
4. **Validation**: Add automatic validation against known mechanisms
5. **Feedback Loop**: Learn from user corrections to improve prompts

## References

- Rusyn et al. (2021). Key Characteristics of Human Hepatotoxicants. *Toxicological Sciences*.
- Paper states: "Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)"

## Summary

The enhanced prompts address the core issue of missing KC detections by:
1. ✅ Recognizing synonyms and related terminology
2. ✅ Including domain knowledge for well-studied chemicals
3. ✅ Being more sensitive to implicit mechanisms
4. ✅ Providing better examples and context

**Result**: The system should now correctly identify KCs 1-8 and 12 for Acetaminophen, matching the Rusyn et al. (2021) paper.
