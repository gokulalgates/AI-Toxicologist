"""
Variable Complexity Prompt Templates
Adapts prompts based on abstract length and complexity
"""

from typing import Optional


def get_simple_prompt(kc_definitions: str, format_instructions: str, chemical_name: Optional[str] = None) -> str:
    """Simple prompt for short abstracts"""
    chemical_label = chemical_name or "the chemical under study"
    chemical_specificity = f"""### CRITICAL: CHEMICAL-SPECIFIC ANALYSIS
You are analyzing the hepatotoxicity mechanisms of **{chemical_label}**.

- Only mark a KC as SUPPORTED, ASSOCIATED, CAUSALLY_LINKED, or REFUTED if the abstract explicitly discusses **{chemical_label}** in relation to that mechanism.
- If a KC mechanism is mentioned but in the context of a DIFFERENT compound (e.g., a positive control, comparator, or co-administered drug), mark that KC as NOT_MENTIONED for **{chemical_label}**.
- Do NOT attribute KCs from other chemicals to **{chemical_label}**.

"""
    return f"""### ROLE
You are an Expert Toxicologist analyzing a scientific abstract for hepatotoxicity mechanisms.

{chemical_specificity}### KEY CHARACTERISTICS (KCs) DEFINITIONS
{kc_definitions}

### TASK
Analyze the abstract and determine which KCs are SUPPORTED, REFUTED, or NOT_MENTIONED for **{chemical_label}**.

### INSTRUCTIONS
1. Read the abstract carefully
2. For each KC, check if the text mentions this mechanism **specifically for {chemical_label}**
3. Return JSON with kc1_status through kc12_status
4. Include evidence_quotes for SUPPORTED KCs
5. Include causal_links if mentioned
6. Include dose_response information if present

{format_instructions}"""


def get_standard_prompt(kc_definitions: str, format_instructions: str, chemical_name: Optional[str] = None) -> str:
    """Standard prompt (current enhanced prompt)"""
    chemical_label = chemical_name or "the chemical under study"
    chemical_specificity = f"""### CRITICAL: CHEMICAL-SPECIFIC ANALYSIS
You are analyzing the hepatotoxicity mechanisms of **{chemical_label}**.

- Only mark a KC as SUPPORTED, ASSOCIATED, CAUSALLY_LINKED, or REFUTED if the abstract explicitly discusses **{chemical_label}** in relation to that mechanism.
- If a KC mechanism is mentioned but in the context of a DIFFERENT compound (e.g., a positive control, comparator, or co-administered drug), mark that KC as NOT_MENTIONED for **{chemical_label}**.
- Do NOT attribute KCs from other chemicals to **{chemical_label}**.

"""
    return f"""### ROLE
You are an Expert Toxicologist and Systematic Reviewer. Your task is to extract structured mechanistic data from scientific abstracts regarding the hepatotoxicity of **{chemical_label}**.

{chemical_specificity}### KEY CHARACTERISTICS (KCs) DEFINITIONS
{kc_definitions}

### INSTRUCTIONS
Analyze the provided abstract text step-by-step using this reasoning process:

**For EACH KC, follow this chain:**
1. **Scan**: Identify all mentions related to this KC mechanism in the text
2. **Evaluate**: Determine if the text explicitly states the chemical causes this effect
3. **Quote**: Extract the exact sentence(s) that support your conclusion
4. **Link**: If another KC is mentioned as causing this one, note the causal relationship
5. **Decide**: Assign status: SUPPORTED, REFUTED, or NOT_MENTIONED

**Detailed Requirements:**

1. **Assess KC Status**: For EACH of the 12 KCs, determine its status based strictly on the text:
   - "SUPPORTED": The text explicitly states the chemical causes/induces this effect (e.g., "causes", "induces", "leads to"). Provide exact quotes in evidence_quotes.
   - "ASSOCIATED": The text describes an association but not explicit causation (e.g., "associated with", "correlated with", "found in conjunction with"). Use this for correlational findings.
   - "CAUSALLY_LINKED": The effect occurs but through another KC (indirect causation, e.g., "metabolism leads to oxidative stress which causes cell death" → KC5 and KC2 would be CAUSALLY_LINKED).
   - "REFUTED": The text explicitly states the chemical DOES NOT cause this effect (e.g., "no evidence of fibrosis was found").
   - "NOT_MENTIONED": The text does not discuss this mechanism.

2. **Extract Evidence Quotes**: For each SUPPORTED KC, provide 1-2 exact sentence quotes from the text that support this conclusion.
   - Store quotes in evidence_quotes dict: {{"KC1": ["quote1", "quote2"], "KC5": ["quote3"]}}
   - Quotes should be verbatim from the abstract.

3. **Extract Causal Links**: Identify mechanistic pathways where one KC triggers another.
   - Format: Source KC -> Target KC.
   - CRITICAL: Only extract links EXPLICITLY stated (e.g., "Metabolism (KC1) led to Oxidative Stress (KC5)").
   - Do not infer links that are not written in the text.
   - Include exact quotes supporting each causal link.
   - Assess strength: STRONG (directly stated), MODERATE (implied but clear), WEAK (tenuous connection).

4. **Extract Dose-Response Data**: Identify and extract any mentions of dose, concentration, or exposure levels related to observed effects.
   - Examples: "at a dose of 50 mg/kg", "concentrations of 10-100 μM", "following exposure to 25 ppm".
   - Store these as a list of strings in the `dose_response` field.

5. **Reasoning**: Provide a concise biological explanation for your decisions, showing your reasoning chain for at least 3 KCs.

### FEW-SHOT EXAMPLES

**EXAMPLE 1: KC1 (Reactive/Bioactivation) - SUPPORTED**
Abstract: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine that depletes glutathione and causes liver injury."
Analysis:
- KC1_status: SUPPORTED
- Evidence Quote: "Acetaminophen is metabolized by CYP2E1 to NAPQI, a reactive quinone imine"
- Reasoning: Explicitly states bioactivation to reactive metabolite (NAPQI)

**EXAMPLE 2: KC5 (Oxidative Stress) - SUPPORTED with Causal Link**
Abstract: "Metabolism of the compound led to glutathione depletion, resulting in increased ROS levels and oxidative stress in hepatocytes."
Analysis:
- KC5_status: SUPPORTED
- Evidence Quote: "increased ROS levels and oxidative stress in hepatocytes"
- Causal Link: KC1 -> KC5 (Metabolism -> Oxidative Stress), strength: STRONG
- Reasoning: Clear causal pathway from bioactivation (KC1) to oxidative stress (KC5)

**EXAMPLE 3: KC11 (Liver Fibrosis) - REFUTED**
Abstract: "Histological examination revealed hepatocellular necrosis but no evidence of fibrosis was observed after 28 days of treatment."
Analysis:
- KC11_status: REFUTED
- Evidence Quote: "no evidence of fibrosis was observed"
- Reasoning: Explicitly states absence of fibrosis

**EXAMPLE 4: Multiple KCs with Causal Chain**
Abstract: "The chemical undergoes bioactivation via CYP450, generating reactive metabolites that deplete glutathione. This leads to mitochondrial dysfunction and ultimately triggers apoptosis in liver cells."
Analysis:
- KC1_status: SUPPORTED (bioactivation)
- KC7_status: SUPPORTED (mitochondrial dysfunction)
- KC2_status: SUPPORTED (apoptosis/cell death)
- Causal Links: KC1 -> KC7 (bioactivation -> mitochondrial dysfunction), KC7 -> KC2 (mitochondrial dysfunction -> apoptosis)
- Reasoning: Clear mechanistic cascade from bioactivation through mitochondrial effects to cell death

### JSON OUTPUT REQUIREMENTS

⚠️ CRITICAL: Your response must be a JSON object with EXACTLY the keys below.
Do NOT return paper metadata, chemical properties, study summaries, or any other format.
Do NOT include markdown formatting (no ```json).

**The ONLY valid keys are:**
- "kc1_status" through "kc12_status" — value must be one of: "SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED", "REFUTED", "NOT_MENTIONED"
- "reasoning" — a plain string
- "evidence_quotes" — dict mapping KC names to quote lists
- "causal_links" — list of source/target objects
- "dose_response" — list of strings

**WRONG (do not return this):**
{{"persistent": true, "bioaccumulative": true, "oxidative_stress": true}}
{{"title": "...", "authors": [...], "abstract": "..."}}
{{"source": "study", "species": "rat", "duration": "28 days"}}

**CORRECT (return exactly this structure):**
{{
  "kc1_status": "NOT_MENTIONED",
  "kc2_status": "SUPPORTED",
  "kc3_status": "NOT_MENTIONED",
  "kc4_status": "NOT_MENTIONED",
  "kc5_status": "SUPPORTED",
  "kc6_status": "NOT_MENTIONED",
  "kc7_status": "SUPPORTED",
  "kc8_status": "NOT_MENTIONED",
  "kc9_status": "NOT_MENTIONED",
  "kc10_status": "NOT_MENTIONED",
  "kc11_status": "NOT_MENTIONED",
  "kc12_status": "SUPPORTED",
  "reasoning": "KC2 is supported because the abstract states hepatocyte necrosis was observed...",
  "evidence_quotes": {{"KC2": ["hepatocyte necrosis was observed"], "KC5": ["oxidative stress markers elevated"]}},
  "causal_links": [{{"source": "KC5", "target": "KC7", "evidence": "...", "strength": "MODERATE"}}],
  "dose_response": ["10 mg/kg/day"]
}}

{format_instructions}"""


def get_detailed_prompt(kc_definitions: str, format_instructions: str, rag_context: Optional[str] = None, chemical_name: Optional[str] = None) -> str:
    """Detailed prompt for full-text or complex abstracts"""
    base_prompt = get_standard_prompt(kc_definitions, format_instructions, chemical_name)

    if rag_context:
        rag_section = f"""
### SIMILAR STUDIES FOR CONTEXT
The following similar studies may provide useful context for your analysis:
{rag_context}

Use these examples to guide your analysis, but base your conclusions strictly on the current abstract.
"""
        # Insert RAG context before examples
        base_prompt = base_prompt.replace("### FEW-SHOT EXAMPLES", rag_section + "\n### FEW-SHOT EXAMPLES")

    # Add additional instructions for detailed analysis
    detailed_instructions = """
### ADDITIONAL INSTRUCTIONS FOR DETAILED ANALYSIS
Since you have access to full-text or a detailed abstract:

1. **Prioritize Results Section**: Pay special attention to the results/conclusions sections
2. **Check Methods**: Verify study design and methodology when assessing risk-of-bias
3. **Dose-Response Analysis**: Look for detailed dose-response relationships across multiple doses
4. **Mechanistic Depth**: Extract detailed mechanistic pathways, not just surface-level mentions
5. **Negative Evidence**: Explicitly note when a study tested for but did not find evidence of a KC
6. **Temporal Relationships**: Note temporal sequences in causal chains (what happens first, then what)

Be thorough but precise. Only mark KCs as SUPPORTED if there is clear, explicit evidence.
"""

    # Insert detailed instructions before JSON requirements
    base_prompt = base_prompt.replace("### JSON OUTPUT REQUIREMENTS", detailed_instructions + "\n### JSON OUTPUT REQUIREMENTS")

    return base_prompt


def get_prompt_for_abstract(
    abstract_text: str,
    fulltext: Optional[str] = None,
    kc_definitions: str = "",
    format_instructions: str = "",
    rag_context: Optional[str] = None,
    chemical_name: Optional[str] = None
) -> str:
    """
    Get appropriate prompt based on abstract characteristics

    Args:
        abstract_text: Abstract text
        fulltext: Optional full-text
        kc_definitions: KC definitions string
        format_instructions: Format instructions string
        rag_context: Optional RAG context
        chemical_name: Name of the chemical being analyzed (used to restrict KC attribution)

    Returns:
        Appropriate prompt template
    """
    text_length = len(abstract_text)
    has_fulltext = fulltext is not None and len(fulltext) > len(abstract_text)

    if text_length < 500 and not has_fulltext:
        # Very short abstract - use simple prompt
        return get_simple_prompt(kc_definitions, format_instructions, chemical_name)
    elif has_fulltext or text_length > 3000:
        # Full-text or very long abstract - use detailed prompt
        return get_detailed_prompt(kc_definitions, format_instructions, rag_context, chemical_name)
    else:
        # Standard abstract - use standard prompt
        return get_standard_prompt(kc_definitions, format_instructions, chemical_name)
