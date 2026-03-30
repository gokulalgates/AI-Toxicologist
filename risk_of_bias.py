"""
Risk-of-Bias assessment framework
Supports OHAT (for toxicology studies), ROBINS-I, and RoB 2
Includes LLM-based assessment
"""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from evidence_models import RiskOfBiasAssessment, RiskOfBiasDomain

# OHAT Risk-of-Bias domains for toxicology studies
OHAT_DOMAINS = [
    "Selection Bias",
    "Confounding",
    "Performance Bias",
    "Detection/Measurement Bias",
    "Attrition Bias",
    "Selective Reporting",
    "Other Sources of Bias"
]

# ROBINS-I domains for observational studies
ROBINS_I_DOMAINS = [
    "Bias due to confounding",
    "Bias in selection of participants",
    "Bias in classification of interventions",
    "Bias due to deviations from intended interventions",
    "Bias due to missing data",
    "Bias in measurement of outcomes",
    "Bias in selection of reported result"
]


class RoBAssessmentOutput(BaseModel):
    """Pydantic model for LLM-based RoB assessment"""
    domains: List[Dict] = Field(description="List of domain assessments with domain, judgment, rationale, quote")
    overall_judgment: str = Field(description="Overall judgment: Low, Some concerns, High, or Critical")
    study_type: Optional[str] = Field(None, description="Study type: in vitro, in vivo, animal, human cohort, case-control, RCT, etc.")
    species: Optional[str] = Field(None, description="Species: Human, Rat, Mouse, Rabbit, primary hepatocytes, HepG2, etc.")
    cell_line: Optional[str] = Field(None, description="Specific cell line if in vitro study")


def assess_rob_with_llm(
    abstract_text: str,
    title: str,
    pmid: str,
    model_name: str = "llama3.2",
    instrument: str = "OHAT"
) -> RiskOfBiasAssessment:
    """
    Assess risk-of-bias using LLM with OHAT framework
    """
    try:
        llm = ChatOllama(model=model_name, temperature=0)

        domains_list = OHAT_DOMAINS if instrument == "OHAT" else ROBINS_I_DOMAINS

        SYSTEM_PROMPT_ROB = """### TASK
You are a systematic review expert assessing Risk-of-Bias for a toxicology study using the {instrument} framework.

### CRITICAL: YOU MUST RETURN A RISK-OF-BIAS ASSESSMENT JSON
DO NOT return study descriptions, methods summaries, or any other format.
ONLY return a Risk-of-Bias assessment with domains and judgments.

### {instrument} DOMAINS
{domains_list}

### INSTRUCTIONS
For EACH domain listed above, assess the risk of bias based on the provided text (abstract or full-text).

**Assessment Guidelines:**
- **Low**: Study design and methods minimize bias. Use this when the text provides evidence of good study design (e.g., randomization mentioned, blinding described, appropriate controls).
- **Some concerns**: Some issues that may introduce bias. Use this when there are potential problems but not severe enough for "High" (e.g., unclear randomization method, partial blinding).
- **High**: Significant risk of bias. Use this when there are clear methodological flaws (e.g., no randomization, no blinding, inappropriate controls).
- **Critical**: Critical flaws that invalidate the study. Use this rarely, only for fundamental design flaws.
- **N/A**: Domain not applicable to this study type (e.g., blinding not applicable to in vitro studies).
- **Insufficient information**: ONLY use this when the text truly lacks ANY information about the domain. If ANY relevant information exists, make an assessment based on that information.

**IMPORTANT ASSESSMENT PRINCIPLES:**
1. **Assess based on what IS available**: If the text mentions randomization (even briefly), assess Selection Bias. Don't require exhaustive details.
2. **Make reasonable inferences**: If a study describes "randomized controlled trial", you can infer low selection bias even if randomization method isn't detailed.
3. **Use "Some concerns" when uncertain**: If information is partial but allows assessment, use "Some concerns" rather than "Insufficient information".
4. **Full-text studies**: If full-text is provided, assume sufficient information exists unless explicitly missing. Full-texts typically contain methods sections.
5. **Abstract-only studies**: Be more lenient - abstracts often contain key methodological information. Only use "Insufficient information" if truly no relevant information exists.

**When to use "Insufficient information":**
- The text provides NO information about the domain (not even implied)
- The domain is completely unaddressed in the text
- For full-text: Only use if methods section is missing or completely uninformative

**When NOT to use "Insufficient information":**
- If randomization is mentioned (even briefly) → Assess Selection Bias
- If controls are mentioned → Assess Confounding
- If outcomes are described → Assess Detection/Measurement Bias
- If study design is described → Assess based on that design

For EACH domain, provide:
1. Judgment (one of: "Low", "Some concerns", "High", "Critical", "N/A", "Insufficient information")
2. Brief rationale (1-2 sentences) explaining why this judgment was made, citing specific text when possible
3. Supporting quote from text (if available, otherwise empty string)
4. information_available: true if sufficient info exists to make assessment, false only if truly no information exists

### STUDY TYPE AND SPECIES EXTRACTION
Extract the following information from the text:
- **study_type**: Identify the study type (e.g., "in vitro", "in vivo", "animal study", "human cohort", "case-control", "RCT", "case report", "observational") or null if not specified
- **species**: Identify the species/model used (e.g., "Human", "Rat", "Mouse", "primary hepatocytes", "HepG2", "HepaRG", "zebrafish") or null if not specified
- **cell_line**: If in vitro, specify the cell line (e.g., "HepG2", "primary human hepatocytes", "HepaRG") or null if not in vitro or not specified

### REQUIRED JSON OUTPUT FORMAT
You MUST return ONLY a JSON object with this exact structure:
{{
  "domains": [
    {{
      "domain": "Selection Bias",
      "judgment": "Low",
      "rationale": "Brief explanation",
      "quote": "Supporting quote or empty string",
      "information_available": true
    }},
    {{
      "domain": "Performance Bias",
      "judgment": "Some concerns",
      "rationale": "Brief explanation",
      "quote": "Supporting quote or empty string",
      "information_available": true
    }}
    // ... one object for EACH domain listed above
  ],
  "overall_judgment": "Low",
  "study_type": "in vitro",
  "species": "HepG2",
  "cell_line": "HepG2"
}}

### CRITICAL REQUIREMENTS
1. Return ONLY the JSON object, no other text
2. Include ALL domains from the {instrument} domains list above
3. Each domain must have: domain, judgment, rationale, quote, information_available
4. overall_judgment must be one of: "Low", "Some concerns", "High", "Critical", "Insufficient information"
5. study_type, species, cell_line can be null if not specified
6. Do NOT include study descriptions, methods summaries, or any other fields

### OVERALL JUDGMENT GUIDELINES
Determine overall judgment based on the most serious concerns across domains that CAN be assessed.

**Overall Judgment Rules:**
1. If ANY domain is "High" or "Critical" → Overall = "High" or "Critical" (whichever is most serious)
2. If multiple domains have "Some concerns" → Overall = "Some concerns"
3. If most domains are "Low" with few "Some concerns" → Overall = "Low" or "Some concerns"
4. If most domains are "Low" → Overall = "Low"
5. **"Insufficient information" for overall**: ONLY use if the majority of domains (>50%) have "Insufficient information" AND no other serious concerns exist. If you can assess even a few domains, base overall judgment on those assessments.

**Example:**
- 3 domains: "Low", 2 domains: "Some concerns", 2 domains: "Insufficient information"
- Overall = "Some concerns" (based on assessable domains)

**For full-text studies**: Overall judgment should rarely be "Insufficient information" since full-texts typically contain methods sections."""

        prompt = SYSTEM_PROMPT_ROB.format(
            instrument=instrument,
            domains_list="\n".join([f"- {d}" for d in domains_list])
        )

        # Determine if we have full-text or just abstract
        # Use a higher threshold to distinguish full-text from abstract
        is_fulltext = len(abstract_text) > 5000  # Abstracts are typically < 2000 chars
        text_type = "Full-text" if is_fulltext else "Abstract"

        # For full-text, include more content (up to 15000 chars) to capture methods section
        # For abstract, use all available text
        if is_fulltext:
            # Include introduction, methods, and results sections (typically first 15000 chars)
            # This captures most of the methods section which is critical for RoB assessment
            text_preview = abstract_text[:15000]
            text_note = f"Full-text provided (showing first 15000 characters of {len(abstract_text)} total). Full-texts typically contain sufficient information for RoB assessment. Assess domains based on available information in the Methods section."
        else:
            text_preview = abstract_text
            text_note = "Abstract provided. Assess domains based on available information. Abstracts often contain key methodological details. Only use 'Insufficient information' if truly no relevant information exists for a domain."

        # Use Pydantic parser for better JSON generation
        parser = PydanticOutputParser(pydantic_object=RoBAssessmentOutput)
        format_instructions = parser.get_format_instructions()

        # Add format instructions to prompt for better JSON generation
        full_prompt = f"""{prompt}

{format_instructions}

Title: {title}
PMID: {pmid}
Text Type: {text_type}
{text_note}
Text: {text_preview}

### CRITICAL OUTPUT REQUIREMENTS
- Return ONLY valid JSON, no markdown, no code blocks, no explanations
- Do NOT include any text before or after the JSON object
- Start with {{ and end with }}
- Ensure all strings are properly quoted with double quotes
- Do NOT include trailing commas
- Return a single, complete JSON object

### REMINDER: YOU ARE ASSESSING RISK-OF-BIAS
- You are NOT describing the study
- You are NOT summarizing methods
- You ARE assessing bias in each domain
- Your output MUST have a "domains" array with Risk-of-Bias judgments
- Each domain must have: domain name, judgment, rationale, quote, information_available

DO NOT return study descriptions, methods summaries, or any other format. ONLY return Risk-of-Bias assessment JSON."""

        response = llm.invoke(full_prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)

        # Clean response text
        cleaned_text = re.sub(r'```json\s*', '', response_text)
        cleaned_text = re.sub(r'```\s*', '', cleaned_text)
        cleaned_text = cleaned_text.strip()

        json_data = None

        # Strategy 1: Try Pydantic parser first (most robust)
        try:
            parsed = parser.parse(cleaned_text)
            json_data = parsed.dict() if hasattr(parsed, 'dict') else parsed.model_dump()
        except Exception:
            # If Pydantic fails, try manual JSON parsing
            pass

        # Strategy 2: Try to find JSON object with balanced braces
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Strategy 2: Try to extract just the first complete JSON object
                # Find the first { and then find the matching }
                brace_count = 0
                start_idx = cleaned_text.find('{')
                if start_idx != -1:
                    end_idx = start_idx
                    for i in range(start_idx, len(cleaned_text)):
                        if cleaned_text[i] == '{':
                            brace_count += 1
                        elif cleaned_text[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i + 1
                                break
                    if brace_count == 0:
                        json_str = cleaned_text[start_idx:end_idx]
                        try:
                            json_data = json.loads(json_str)
                        except json.JSONDecodeError:
                            pass

        # Strategy 3: Try to fix common JSON issues
        if json_data is None:
            # Remove trailing commas before closing braces/brackets
            fixed_text = re.sub(r',\s*}', '}', cleaned_text)
            fixed_text = re.sub(r',\s*]', ']', fixed_text)
            # Try parsing again
            json_match = re.search(r'\{.*\}', fixed_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    json_data = json.loads(json_str)
                except json.JSONDecodeError:
                    # Strategy 4: Try to extract and fix the JSON more aggressively
                    # Remove any text after the last }
                    last_brace = fixed_text.rfind('}')
                    if last_brace != -1:
                        json_str = fixed_text[:last_brace + 1]
                        # Find the matching opening brace
                        brace_count = 0
                        start_idx = json_str.rfind('{')
                        if start_idx != -1:
                            for i in range(start_idx, len(json_str)):
                                if json_str[i] == '{':
                                    brace_count += 1
                                elif json_str[i] == '}':
                                    brace_count -= 1
                            if brace_count == 0:
                                try:
                                    json_data = json.loads(json_str[start_idx:])
                                except json.JSONDecodeError:
                                    pass

        if json_data is None:
            # All parsing strategies failed
            print(f"⚠️  Failed to parse RoB JSON after all strategies. Response preview: {response_text[:1000]}")
            raise ValueError(f"No valid JSON found in response. Response preview: {response_text[:500]}")

        # Validate that we got a Risk-of-Bias assessment, not a study description
        if "domains" not in json_data:
            # Check if it looks like a study description instead
            if "study" in json_data or "methods" in json_data or "description" in json_data:
                print(f"⚠️  LLM returned study description instead of RoB assessment. Response preview: {response_text[:500]}")
                print("   💡 This indicates the LLM misunderstood the task. Retrying with more explicit prompt...")
                # Try once more with a more explicit prompt
                retry_prompt = f"""{full_prompt}

CRITICAL REMINDER: You MUST return a Risk-of-Bias assessment with "domains" array, NOT a study description.
The JSON must have this structure:
{{
  "domains": [{{"domain": "...", "judgment": "...", "rationale": "...", "quote": "...", "information_available": true/false}}, ...],
  "overall_judgment": "...",
  "study_type": "...",
  "species": "...",
  "cell_line": "..."
}}
DO NOT return study descriptions, methods summaries, or any other format."""
                try:
                    retry_response = llm.invoke(retry_prompt)
                    retry_text = retry_response.content if hasattr(retry_response, 'content') else str(retry_response)
                    retry_cleaned = re.sub(r'```json\s*', '', retry_text)
                    retry_cleaned = re.sub(r'```\s*', '', retry_cleaned)
                    retry_cleaned = retry_cleaned.strip()
                    retry_json_match = re.search(r'\{.*\}', retry_cleaned, re.DOTALL)
                    if retry_json_match:
                        retry_json_data = json.loads(retry_json_match.group())
                        if "domains" in retry_json_data:
                            json_data = retry_json_data
                            print("   ✓ Retry successful - got valid RoB assessment")
                        else:
                            raise ValueError("Retry also failed - LLM still returning wrong format")
                    else:
                        raise ValueError("Retry failed - no JSON found")
                except Exception as retry_error:
                    print(f"   ⚠️  Retry also failed: {retry_error}")
                    raise ValueError(f"LLM returned study description instead of RoB assessment. Response preview: {response_text[:500]}")
            else:
                raise ValueError(f"JSON missing required 'domains' field. Response preview: {response_text[:500]}")

        # Convert to RiskOfBiasDomain objects
        domains = []
        for domain_data in json_data.get("domains", []):
            domain = RiskOfBiasDomain(
                domain=domain_data.get("domain", "Unknown"),
                judgment=domain_data.get("judgment", "Insufficient information"),
                rationale=domain_data.get("rationale", "No rationale provided"),
                supporting_quote=domain_data.get("quote"),
                information_available=domain_data.get("information_available", False)
            )
            domains.append(domain)

        overall = json_data.get("overall_judgment", "Insufficient information")

        # Extract study type and species (IMPROVEMENT #3)
        study_type = json_data.get("study_type")
        species = json_data.get("species")
        cell_line = json_data.get("cell_line")

        # Determine if full-text was used (heuristic: if text is long, assume full-text)
        # Use higher threshold to distinguish full-text from abstract
        fulltext_used = len(abstract_text) > 5000  # Full-texts are typically > 5000 chars

        assessment = RiskOfBiasAssessment(
            study_id=pmid,
            instrument=instrument,
            domains=domains,
            overall_judgment=overall,
            assessed_by=f"LLM-{model_name}",
            assessment_date=None,
            fulltext_used=fulltext_used
        )

        # Store study type and species in assessment metadata (will be used by certainty grading)
        assessment.study_type = study_type
        assessment.species = species
        assessment.cell_line = cell_line

        return assessment

    except Exception as e:
        error_msg = str(e)
        print(f"⚠️  Error in LLM-based RoB assessment for PMID {pmid}: {error_msg}")
        # Log more details if it's a JSON error
        if "JSON" in error_msg or "json" in error_msg.lower():
            print("   💡 This is likely a JSON parsing issue. The LLM response may contain extra text or malformed JSON.")
            print("   💡 Falling back to 'Insufficient information' assessment.")
        # Return assessment with insufficient information rather than defaulting
        return RiskOfBiasAssessment(
            study_id=pmid,
            instrument=instrument,
            domains=[],  # Empty = insufficient information
            overall_judgment="Insufficient information",
            assessed_by=f"System-Fallback (Error: {type(e).__name__})",
            assessment_date=None,
            fulltext_used=False
        )


def assess_roh_ohat(study_data: Dict, abstract_text: str) -> RiskOfBiasAssessment:
    """
    Assess risk-of-bias using OHAT framework for toxicology studies
    This is a simplified fallback version - full implementation should use LLM with full-text
    """
    domains = []

    # Return insufficient information rather than guessing
    for domain_name in OHAT_DOMAINS:
        domain = RiskOfBiasDomain(
            domain=domain_name,
            judgment="Insufficient information",
            rationale=f"Insufficient information in abstract to assess {domain_name}. Full-text required.",
            supporting_quote=None,
            information_available=False
        )
        domains.append(domain)

    return RiskOfBiasAssessment(
        study_id=study_data.get("pmid", "unknown"),
        instrument="OHAT",
        domains=domains,
        overall_judgment="Insufficient information",
        assessed_by="System-Fallback",
        assessment_date=None,
        fulltext_used=False
    )


def create_rob_heatmap(rob_assessments: List[RiskOfBiasAssessment], kcs: List[str]) -> Dict:
    """
    Create risk-of-bias heatmap data structure
    Returns data ready for visualization
    """
    # Group by KC and domain
    rob_matrix = {}

    for kc in kcs:
        rob_matrix[kc] = {}
        for assessment in rob_assessments:
            for domain in assessment.domains:
                if domain.domain not in rob_matrix[kc]:
                    rob_matrix[kc][domain.domain] = []
                rob_matrix[kc][domain.domain].append(domain.judgment)

    # Convert to summary (most common judgment per KC-domain pair)
    summary = {}
    for kc, domains in rob_matrix.items():
        summary[kc] = {}
        for domain_name, judgments in domains.items():
            # Count judgments
            judgment_counts = {}
            for j in judgments:
                judgment_counts[j] = judgment_counts.get(j, 0) + 1
            # Get most common
            most_common = max(judgment_counts.items(), key=lambda x: x[1])[0]
            summary[kc][domain_name] = most_common

    return summary


def calculate_rob_summary_stats(rob_assessments: List[RiskOfBiasAssessment]) -> Dict:
    """
    Calculate summary statistics for risk-of-bias assessments
    """
    total = len(rob_assessments)
    if total == 0:
        return {}

    overall_counts = {
        "Low": 0,
        "Some concerns": 0,
        "High": 0,
        "Critical": 0,
        "Insufficient information": 0
    }

    fulltext_count = sum(1 for a in rob_assessments if a.fulltext_used)

    for assessment in rob_assessments:
        overall_counts[assessment.overall_judgment] = overall_counts.get(
            assessment.overall_judgment, 0
        ) + 1

    return {
        "total_studies": total,
        "overall_distribution": overall_counts,
        "low_risk_percentage": (overall_counts["Low"] / total * 100) if total > 0 else 0,
        "insufficient_info_count": overall_counts.get("Insufficient information", 0),
        "fulltext_used_count": fulltext_count,
        "fulltext_percentage": (fulltext_count / total * 100) if total > 0 else 0
    }
