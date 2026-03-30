"""
Enhanced Prompt Improvements for Better KC Detection
Addresses issues with missing KC detections, especially for well-studied chemicals like Acetaminophen
"""

from typing import Dict, Optional


def get_liberal_prompt(kc_definitions: str, format_instructions: str) -> str:
    """
    Very liberal prompt that is more permissive in detecting mechanisms
    Use when standard prompts are too strict and missing known mechanisms
    IMPORTANT: Still detects REFUTED cases when explicitly stated
    """
    return f"""### ROLE
You are an Expert Toxicologist analyzing scientific abstracts for hepatotoxicity mechanisms. 
**IMPORTANT: Be LIBERAL in detecting mechanisms. If a mechanism is described (even indirectly), mark it as SUPPORTED.**
**CRITICAL: Also detect REFUTED cases when the text explicitly states the chemical does NOT cause an effect.**

### KEY CHARACTERISTICS (KCs) DEFINITIONS
{kc_definitions}

### CRITICAL INSTRUCTION: LIBERAL INTERPRETATION WITH REFUTED DETECTION

**When in doubt, mark as SUPPORTED rather than NOT_MENTIONED.**
**BUT: Always detect REFUTED when explicitly stated.**

**Status Decision Rules:**

1. **SUPPORTED**: If ANY of the following apply:
   - The mechanism is explicitly stated
   - The mechanism is described using synonyms or related terms
   - The mechanism is implied by the described effects
   - The mechanism is mentioned as part of a pathway or process

2. **REFUTED**: If the text explicitly states the chemical does NOT cause this effect:
   - "no evidence of", "did not cause", "was not observed"
   - "absence of", "lack of", "no signs of"
   - "did not induce", "failed to cause", "no indication of"
   - **Example**: "Histological examination revealed no evidence of fibrosis" → KC11 = REFUTED
   - **Example**: "Bile flow was not impaired" → KC9 = REFUTED
   - **Example**: "No signs of mitochondrial dysfunction were observed" → KC7 = REFUTED

3. **NOT_MENTIONED**: Only if the mechanism is completely absent and not implied

**Examples of what should be SUPPORTED:**
- "metabolized" → KC1 (bioactivation)
- "reactive metabolite" → KC1 (bioactivation)
- "glutathione depletion" → KC5 (oxidative stress)
- "ROS" or "reactive oxygen species" → KC5 (oxidative stress)
- "necrosis" or "apoptosis" → KC2 (cell death)
- "mitochondrial damage" → KC7 (mitochondrial dysfunction)
- "JNK" or "stress signaling" → KC8 (stress signaling)
- "inflammation" → KC6 (immune response)
- "steatosis" or "fat accumulation" → KC12 (metabolism disruption)

**Examples of what should be REFUTED:**
- "no evidence of fibrosis" → KC11 = REFUTED
- "did not cause cholestasis" → KC9 = REFUTED
- "absence of mitochondrial dysfunction" → KC7 = REFUTED
- "no signs of apoptosis" → KC2 = REFUTED (if apoptosis was tested for)

### INSTRUCTIONS
For EACH KC:
1. **Scan broadly**: Look for ANY mention of related mechanisms, synonyms, or effects
2. **Check for REFUTED**: Look for explicit negation ("no evidence", "did not cause", "absence of")
3. **Be inclusive for SUPPORTED**: If there's ANY evidence (explicit or implicit), mark as SUPPORTED
4. **Extract quotes**: Provide the best supporting quote(s) - including quotes for REFUTED cases
5. **Only mark NOT_MENTIONED if**: The mechanism is completely absent and not implied

### JSON OUTPUT REQUIREMENTS
**CRITICAL: You must return ONLY a KCAnalysis JSON object. Do NOT return paper metadata (title, authors, journal, etc.).**

You must return a valid JSON object matching the KCAnalysis schema. Do not include markdown formatting (```json).

**Required fields:**
- Keys for KCs: "kc1_status", "kc2_status", "kc3_status", ... "kc12_status" (all 12 required)
  - Values must be one of: "SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED", "REFUTED", or "NOT_MENTIONED"
- Key for Evidence Quotes: "evidence_quotes" as a dict: {{"KC1": ["quote1"], "KC5": ["quote2", "quote3"]}}
- Key for Causal Links: "causal_links" as a list of objects: {{"source": "KC1", "target": "KC5", "evidence": "quote...", "strength": "STRONG"}}
- Key for Dose-Response: "dose_response" as a list of strings: ["50 mg/kg", "10-100 μM"]
- Key for Species: "species" as a string (e.g., "Human", "Rat", "Mouse", "In Vitro")
- Key for Study Type: "study_type" as a string (e.g., "In Vivo", "In Vitro", "Review", "Clinical")
- Key for Reasoning: "reasoning" as a string explaining your analysis

**DO NOT include:**
- Paper metadata fields like "title", "authors", "year", "journal", "doi", "abstract", "methods", "results", "conclusion"
- Any fields not in the KCAnalysis schema

{format_instructions}"""


def get_enhanced_prompt_with_synonyms(kc_definitions: str, format_instructions: str) -> str:
    """
    Enhanced prompt with better synonym recognition and mechanism detection
    
    This addresses the issue where KCs are marked as NOT_MENTIONED even when
    mechanisms are described using different terminology.
    """
    return f"""### ROLE
You are an Expert Toxicologist and Systematic Reviewer. Your task is to extract structured mechanistic data from scientific abstracts regarding chemical hepatotoxicity.

### KEY CHARACTERISTICS (KCs) DEFINITIONS
{kc_definitions}

### CRITICAL: SYNONYM AND MECHANISM RECOGNITION

When analyzing text, recognize that mechanisms can be described using various terms:

**KC1 (Reactive/Bioactivation):**
- Look for: "metabolized", "bioactivation", "bioactivated", "metabolism", "reactive metabolite", "reactive intermediate", "NAPQI", "quinone imine", "electrophile", "CYP450", "CYP2E1", "phase I metabolism", "oxidation", "hydroxylation"
- Example: "metabolized to NAPQI" = KC1 SUPPORTED

**KC2 (Cell Death):**
- Look for: "apoptosis", "necrosis", "cell death", "hepatocyte death", "liver cell death", "cytopathic", "lethal", "kills cells", "cell killing", "hepatocellular injury", "liver injury"
- Example: "causes hepatocellular necrosis" = KC2 SUPPORTED

**KC3 (Proliferation/Regeneration):**
- Look for: "proliferation", "regeneration", "cell division", "mitosis", "hepatocyte proliferation", "liver regeneration", "compensatory hyperplasia", "cell growth"
- Example: "induces hepatocyte proliferation" = KC3 SUPPORTED

**KC4 (Transport Disruption):**
- Look for: "transport", "transporter", "bile acid transport", "bilirubin transport", "ABC transporters", "MRP", "BSEP", "uptake", "efflux", "secretion"
- Example: "inhibits bile acid transport" = KC4 SUPPORTED

**KC5 (Oxidative Stress):**
- Look for: "oxidative stress", "ROS", "reactive oxygen species", "free radicals", "antioxidant depletion", "glutathione depletion", "GSH", "lipid peroxidation", "oxidative damage", "redox imbalance"
- Example: "depletes glutathione and increases ROS" = KC5 SUPPORTED

**KC6 (Immune Response):**
- Look for: "immune", "immunological", "inflammation", "inflammatory", "cytokines", "TNF-α", "IL-6", "neutrophils", "macrophages", "Kupffer cells", "immune-mediated", "autoimmune"
- Example: "triggers inflammatory response" = KC6 SUPPORTED

**KC7 (Mitochondrial Dysfunction):**
- Look for: "mitochondrial", "mitochondria", "ATP depletion", "mitochondrial damage", "mitochondrial permeability transition", "MPT", "respiratory chain", "electron transport", "mitochondrial swelling"
- Example: "causes mitochondrial dysfunction" = KC7 SUPPORTED

**KC8 (Stress Signaling):**
- Look for: "stress signaling", "JNK", "c-Jun N-terminal kinase", "MAPK", "ERK", "p38", "stress pathways", "signaling cascade", "kinase activation", "transcription factors", "NF-κB", "AP-1"
- Example: "activates JNK signaling pathway" = KC8 SUPPORTED

**KC9 (Cholestasis):**
- Look for: "cholestasis", "cholestatic", "bile flow", "bile duct", "biliary", "bile accumulation", "bile acid retention", "canalicular", "bile plug"
- Example: "causes cholestasis" = KC9 SUPPORTED

**KC10 (Cytoskeleton Disruption):**
- Look for: "cytoskeleton", "actin", "microtubules", "intermediate filaments", "keratins", "F-actin", "cytoskeletal", "cell shape", "morphology"
- Example: "disrupts cytoskeleton" = KC10 SUPPORTED

**KC11 (Liver Fibrosis):**
- Look for: "fibrosis", "fibrotic", "collagen", "extracellular matrix", "ECM", "stellate cells", "HSC", "scarring", "cirrhosis"
- Example: "leads to liver fibrosis" = KC11 SUPPORTED

**KC12 (Metabolism Disruption):**
- Look for: "metabolism disruption", "metabolic disruption", "lipid metabolism", "fatty acid", "steatosis", "fat accumulation", "lipid accumulation", "protein metabolism", "glucose metabolism", "glycogen"
- Example: "disrupts lipid metabolism" = KC12 SUPPORTED

### INSTRUCTIONS
Analyze the provided abstract text step-by-step using this reasoning process:

**For EACH KC, follow this chain:**
1. **Scan**: Identify all mentions related to this KC mechanism in the text (including synonyms and related terms)
2. **Evaluate**: Determine if the text describes this mechanism, even if not explicitly stated as "causes"
   - Consider: "leads to", "results in", "induces", "triggers", "associated with", "characterized by", "involves"
3. **Quote**: Extract the exact sentence(s) that support your conclusion
4. **Link**: If another KC is mentioned as causing this one, note the causal relationship
5. **Decide**: Assign status: SUPPORTED, REFUTED, or NOT_MENTIONED

**Important Guidelines:**

1. **Be Sensitive, Not Overly Strict**: If a mechanism is clearly described (even with synonyms), mark it as SUPPORTED
   - Example: "metabolized to reactive NAPQI" → KC1 SUPPORTED (even if "bioactivation" not explicitly stated)
   - Example: "depletes glutathione" → KC5 SUPPORTED (oxidative stress mechanism)

2. **Recognize Implicit Mechanisms**: 
   - "NAPQI formation" implies KC1 (bioactivation)
   - "glutathione depletion" implies KC5 (oxidative stress)
   - "hepatocellular necrosis" implies KC2 (cell death)
   - "mitochondrial swelling" implies KC7 (mitochondrial dysfunction)

3. **Context Matters**: Consider the overall context of the study
   - If studying hepatotoxicity and describing mechanisms, be more inclusive
   - If explicitly testing for a mechanism and finding none, mark as REFUTED

4. **Evidence Quotes**: For each SUPPORTED KC, provide exact quotes showing the mechanism

5. **Causal Links**: Extract causal relationships when explicitly stated or clearly implied

### ENHANCED EXAMPLES FOR ACETAMINOPHEN

**EXAMPLE: Acetaminophen - Multiple KCs**
Abstract: "Acetaminophen is metabolized by CYP2E1 to N-acetyl-p-quinoneimine (NAPQI), a reactive metabolite. In overdose, NAPQI depletes glutathione, leading to oxidative stress. This triggers mitochondrial dysfunction and ultimately causes hepatocellular necrosis. The process involves activation of JNK signaling pathways."

Analysis:
- KC1_status: SUPPORTED
  - Evidence: "metabolized by CYP2E1 to NAPQI, a reactive metabolite"
  - Reasoning: Bioactivation clearly described
  
- KC5_status: SUPPORTED
  - Evidence: "NAPQI depletes glutathione, leading to oxidative stress"
  - Reasoning: Glutathione depletion indicates oxidative stress
  
- KC7_status: SUPPORTED
  - Evidence: "triggers mitochondrial dysfunction"
  - Reasoning: Explicitly stated
  
- KC2_status: SUPPORTED
  - Evidence: "causes hepatocellular necrosis"
  - Reasoning: Cell death mechanism
  
- KC8_status: SUPPORTED
  - Evidence: "involves activation of JNK signaling pathways"
  - Reasoning: Stress signaling pathway
  
- Causal Links:
  - KC1 → KC5: "NAPQI depletes glutathione, leading to oxidative stress" (STRONG)
  - KC5 → KC7: "leading to oxidative stress. This triggers mitochondrial dysfunction" (STRONG)
  - KC7 → KC2: "mitochondrial dysfunction and ultimately causes hepatocellular necrosis" (STRONG)

**EXAMPLE: Recognizing Synonyms**
Abstract: "The compound undergoes phase I oxidation, generating electrophilic intermediates that deplete cellular antioxidants."

Analysis:
- KC1_status: SUPPORTED
  - Evidence: "phase I oxidation, generating electrophilic intermediates"
  - Reasoning: "Phase I oxidation" = bioactivation, "electrophilic intermediates" = reactive metabolites
- KC5_status: SUPPORTED
  - Evidence: "deplete cellular antioxidants"
  - Reasoning: Antioxidant depletion indicates oxidative stress

### JSON OUTPUT REQUIREMENTS
**CRITICAL: You must return ONLY a KCAnalysis JSON object. Do NOT return paper metadata (title, authors, journal, etc.).**

You must return a valid JSON object matching the KCAnalysis schema. Do not include markdown formatting (```json).

**Required fields:**
- Keys for KCs: "kc1_status", "kc2_status", "kc3_status", ... "kc12_status" (all 12 required)
  - Values must be one of: "SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED", "REFUTED", or "NOT_MENTIONED"
- Key for Evidence Quotes: "evidence_quotes" as a dict: {{"KC1": ["quote1"], "KC5": ["quote2", "quote3"]}}
- Key for Causal Links: "causal_links" as a list of objects: {{"source": "KC1", "target": "KC5", "evidence": "quote...", "strength": "STRONG"}}
- Key for Dose-Response: "dose_response" as a list of strings: ["50 mg/kg", "10-100 μM"]
- Key for Species: "species" as a string (e.g., "Human", "Rat", "Mouse", "In Vitro")
- Key for Study Type: "study_type" as a string (e.g., "In Vivo", "In Vitro", "Review", "Clinical")
- Key for Reasoning: "reasoning" as a string explaining your analysis

**DO NOT include:**
- Paper metadata fields like "title", "authors", "year", "journal", "doi", "abstract", "methods", "results", "conclusion"
- Any fields not in the KCAnalysis schema

**Example correct format:**
{{
  "kc1_status": "SUPPORTED",
  "kc2_status": "NOT_MENTIONED",
  ...
  "kc12_status": "SUPPORTED",
  "evidence_quotes": {{"KC1": ["quote here"]}},
  "causal_links": [],
  "dose_response": [],
  "reasoning": "Brief explanation"
}}

{format_instructions}"""


def get_acetaminophen_specific_prompt(kc_definitions: str, format_instructions: str) -> str:
    """
    Acetaminophen-specific prompt with known mechanisms
    
    Use this when analyzing Acetaminophen to leverage known mechanisms
    """
    base_prompt = get_enhanced_prompt_with_synonyms(kc_definitions, format_instructions)
    
    acetaminophen_context = """
### ACETAMINOPHEN-SPECIFIC CONTEXT

Acetaminophen (paracetamol, APAP) is a well-studied hepatotoxicant with established mechanisms:

**Known Mechanisms:**
- KC1: Metabolized by CYP2E1/CYP3A4 to NAPQI (N-acetyl-p-quinoneimine)
- KC2: Causes hepatocellular necrosis (centrilobular)
- KC3: Induces compensatory hepatocyte proliferation
- KC4: Can disrupt bile acid transport
- KC5: NAPQI depletes glutathione, causing oxidative stress
- KC6: Triggers inflammatory response (neutrophils, Kupffer cells)
- KC7: Causes mitochondrial dysfunction (permeability transition)
- KC8: Activates stress signaling (JNK, p38 MAPK)
- KC12: Disrupts lipid metabolism (can cause steatosis)

**What to Look For:**
- "NAPQI" or "N-acetyl-p-quinoneimine" → KC1
- "CYP2E1" or "CYP3A4" metabolism → KC1
- "Glutathione depletion" or "GSH depletion" → KC5
- "Centrilobular necrosis" → KC2
- "JNK activation" → KC8
- "Mitochondrial permeability transition" → KC7

**Important:** Still base your analysis on the actual text, but use this context to recognize mechanisms even when described with different terminology.

"""
    
    # Insert Acetaminophen context before examples
    if "### ENHANCED EXAMPLES" in base_prompt:
        enhanced = base_prompt.replace("### ENHANCED EXAMPLES", acetaminophen_context + "\n### ENHANCED EXAMPLES")
    else:
        enhanced = base_prompt + "\n\n" + acetaminophen_context
    
    return enhanced
