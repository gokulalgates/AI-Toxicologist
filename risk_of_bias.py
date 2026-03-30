"""
Risk-of-Bias assessment framework
Supports OHAT (for toxicology studies), ROBINS-I, and RoB 2
Includes LLM-based assessment
"""

from typing import List, Dict, Literal, Optional
from evidence_models import RiskOfBiasDomain, RiskOfBiasAssessment
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json
import re
import logging

logger = logging.getLogger(__name__)

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
    instrument: str = "OHAT",
    fulltext_available: bool = False
) -> RiskOfBiasAssessment:
    """
    Assess risk-of-bias using LLM with OHAT framework
    """
    try:
        # Retry mechanism for robustness
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                llm = ChatOllama(model=model_name, temperature=0)
                
                domains_list = OHAT_DOMAINS if instrument == "OHAT" else ROBINS_I_DOMAINS
        
                SYSTEM_PROMPT_ROB = """### TASK
You are a systematic review expert assessing Risk-of-Bias for a toxicology study.

### {instrument} DOMAINS
{domains_list}

### INSTRUCTIONS
For EACH domain, assess the risk of bias based on the provided text (abstract or full-text):
- **Low**: Study design and methods minimize bias
- **Some concerns**: Some issues that may introduce bias
- **High**: Significant risk of bias
- **Critical**: Critical flaws that invalidate the study
- **N/A**: Domain not applicable to this study
- **Insufficient information**: The text does not contain enough information to assess this domain (CRITICAL: Use this if methods/details are missing)

CRITICAL: If the text does not contain sufficient information to assess a domain (e.g., methods section missing, no details on blinding, etc.), return "Insufficient information" rather than guessing or defaulting to "Some concerns".

Provide:
1. Judgment for each domain (use "Insufficient information" when appropriate)
2. Brief rationale (1-2 sentences) explaining why this judgment was made
3. Supporting quote from text (if available)
4. information_available: true if sufficient info exists, false if insufficient

### STUDY TYPE AND SPECIES EXTRACTION (IMPROVEMENT #3)
CRITICAL: Extract the following information from the text:
- **study_type**: Identify the study type (e.g., "in vitro", "in vivo", "animal study", "human cohort", "case-control", "RCT", "case report", "observational")
- **species**: Identify the species/model used (e.g., "Human", "Rat", "Mouse", "primary hepatocytes", "HepG2", "HepaRG", "zebrafish")
- **cell_line**: If in vitro, specify the cell line (e.g., "HepG2", "primary human hepatocytes", "HepaRG")

Look for keywords like:
- Study type: "in vitro", "cell culture", "animal model", "clinical trial", "cohort study", "case-control"
- Species: "human", "rat", "mouse", "rabbit", "zebrafish", "primary hepatocytes", "HepG2", "HepaRG"

### OUTPUT FORMAT
Return JSON with:
- "domains": [{{"domain": "Selection Bias", "judgment": "Low" | "Some concerns" | "High" | "Critical" | "N/A" | "Insufficient information", "rationale": "...", "quote": "...", "information_available": true/false}}, ...]
- "overall_judgment": "Low" | "Some concerns" | "High" | "Critical" | "Insufficient information"
- "study_type": "in vitro" | "in vivo" | "animal study" | "human cohort" | etc. (or null if not specified)
- "species": "Human" | "Rat" | "Mouse" | "primary hepatocytes" | etc. (or null if not specified)
- "cell_line": "HepG2" | "HepaRG" | etc. (or null if not in vitro or not specified)

Determine overall judgment based on the most serious concerns across domains. If multiple domains have "Insufficient information", the overall judgment should be "Insufficient information"."""

                prompt = SYSTEM_PROMPT_ROB.format(
                    instrument=instrument,
                    domains_list="\n".join([f"- {d}" for d in domains_list])
                )
                
                # Determine if we have full-text or just abstract based on fulltext_available parameter
                # Use fulltext_available if provided, otherwise fall back to length heuristic
                if fulltext_available and len(abstract_text) > 1000:
                    text_type = "Full-text"
                    # For full-text, show more content (up to 8000 chars)
                    text_preview = abstract_text[:8000] if len(abstract_text) > 8000 else abstract_text
                    if len(abstract_text) > 8000:
                        text_preview += "\n\n[Text truncated for length - showing first 8000 characters]"
                else:
                    text_type = "Abstract"
                    # For abstract, show up to 3000 chars
                    text_preview = abstract_text[:3000] if len(abstract_text) > 3000 else abstract_text
                
                # Use Pydantic parser for better JSON generation
                parser = PydanticOutputParser(pydantic_object=RoBAssessmentOutput)
                format_instructions = parser.get_format_instructions()
                
                # Add format instructions to prompt for better JSON generation
                full_prompt = f"""{prompt}

{format_instructions}

Title: {title}
PMID: {pmid}
Text Type: {text_type}
Text: {text_preview}

### CRITICAL OUTPUT REQUIREMENTS
- Return ONLY valid JSON, no markdown, no code blocks, no explanations
- Do NOT include any text before or after the JSON object
- Start with {{ and end with }}
- Ensure all strings are properly quoted with double quotes
- Do NOT include trailing commas
- Return a single, complete JSON object"""
                
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
                except Exception as pydantic_error:
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
                        except json.JSONDecodeError as e:
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
                    logger.warning(f"Failed to parse RoB JSON after all strategies. Response preview: {response_text[:1000]}")
                    raise ValueError(f"No valid JSON found in response. Response preview: {response_text[:500]}")
                
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
                
                # Determine if full-text was used
                # Use the passed parameter - if fulltext_available is True, we trust that full-text was actually used
                # The caller is responsible for ensuring full-text is substantial before setting fulltext_available=True
                fulltext_used = fulltext_available
                
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
                if attempt < max_retries:
                    logger.warning(f"Retry {attempt+1}/{max_retries} for RoB assessment of {pmid}: {e}")
                else:
                    raise e

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in LLM-based RoB assessment for PMID {pmid}: {error_msg}")
        # Log more details if it's a JSON error
        if "JSON" in error_msg or "json" in error_msg.lower():
            logger.info("This is likely a JSON parsing issue. The LLM response may contain extra text or malformed JSON.")
            logger.info("Falling back to 'Insufficient information' assessment.")
        # Return assessment with insufficient information rather than defaulting
        return RiskOfBiasAssessment(
            study_id=pmid,
            instrument=instrument,
            domains=[],  # Empty = insufficient information
            overall_judgment="Insufficient information",
            assessed_by=f"LLM-Failed (Error: {type(e).__name__})",
            assessment_date=None,
            fulltext_used=fulltext_available  # Respect the input flag even on failure
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
