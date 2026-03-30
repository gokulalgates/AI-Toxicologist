"""
GRADE/OHAT Certainty Grading Rules Engine
Implements systematic rules for assessing certainty of evidence per KC
"""

from typing import List, Dict, Literal, Tuple, Optional
from evidence_models import CertaintyAssessment, RiskOfBiasAssessment
from risk_of_bias import calculate_rob_summary_stats
import re


def calculate_initial_certainty(study_type: str, species: str = None) -> Literal["High", "Moderate", "Low", "Very Low"]:
    """
    Determine initial certainty based on study type and species
    GRADE: Start High for RCTs, Moderate for observational, Low for non-human
    OHAT: Start Low for non-human/in vitro evidence
    
    For toxicology studies, RCTs are extremely rare. Most evidence is:
    - Human: Observational studies (cohort, case-control, case reports) -> Moderate
    - Animal: In vivo studies -> Low
    - In vitro: Cell culture, organoids -> Very Low
    """
    # Human studies
    if species == "Human":
        if study_type == "RCT":
            return "High"  # Rare in toxicology
        elif study_type in ["Observational", "Cohort", "Case-Control", "Case Report"]:
            return "Moderate"
        else:
            return "Moderate"  # Default for human studies
    
    # Animal studies
    elif species in ["Rat", "Mouse", "Rabbit", "Dog", "Monkey", "Pig"]:
        return "Low"
    
    # In vitro studies
    elif species in ["in vitro", "cell culture", "primary hepatocytes", "cell line"]:
        return "Very Low"
    
    # Unknown/unspecified
    else:
        return "Low"  # Default for unknown (conservative)


def rate_up_certainty(
    initial_certainty: str,
    factors: List[str]
) -> tuple[Literal["High", "Moderate", "Low", "Very Low"], List[str]]:
    """
    Rate up certainty based on positive factors
    Factors: large_effect, dose_response, consistency, coherence, biological_plausibility
    """
    certainty_levels = ["Very Low", "Low", "Moderate", "High"]
    current_idx = certainty_levels.index(initial_certainty)
    applied_factors = []
    
    # Large effect size (rate up by 1-2 levels)
    if "large_effect" in factors:
        current_idx = min(current_idx + 2, 3)
        applied_factors.append("Large effect size")
    
    # Dose-response relationship (rate up by 1 level)
    if "dose_response" in factors:
        current_idx = min(current_idx + 1, 3)
        applied_factors.append("Dose-response relationship")
    
    # Consistency across studies (rate up by 1 level)
    if "consistency" in factors:
        current_idx = min(current_idx + 1, 3)
        applied_factors.append("Consistent findings across studies")
    
    # Coherence (rate up by 1 level)
    if "coherence" in factors:
        current_idx = min(current_idx + 1, 3)
        applied_factors.append("Coherent with known biology")
    
    # Biological plausibility (rate up by 1 level)
    if "biological_plausibility" in factors:
        current_idx = min(current_idx + 1, 3)
        applied_factors.append("Strong biological plausibility")
    
    return certainty_levels[current_idx], applied_factors


def rate_down_certainty(
    initial_certainty: str,
    factors: List[str]
) -> tuple[Literal["High", "Moderate", "Low", "Very Low"], List[str]]:
    """
    Rate down certainty based on negative factors
    Factors: risk_of_bias, inconsistency, indirectness, imprecision, publication_bias
    """
    certainty_levels = ["Very Low", "Low", "Moderate", "High"]
    current_idx = certainty_levels.index(initial_certainty)
    applied_factors = []
    
    # Risk of bias (rate down by 1-2 levels)
    if "risk_of_bias" in factors:
        current_idx = max(current_idx - 1, 0)
        applied_factors.append("Risk of bias concerns")
    
    # Inconsistency (rate down by 1-2 levels)
    if "inconsistency" in factors:
        current_idx = max(current_idx - 1, 0)
        applied_factors.append("Inconsistent findings")
    
    # Indirectness (rate down by 1-2 levels)
    if "indirectness" in factors:
        current_idx = max(current_idx - 1, 0)
        applied_factors.append("Indirect evidence (non-human/in vitro)")
    
    # Imprecision (rate down by 1 level)
    if "imprecision" in factors:
        current_idx = max(current_idx - 1, 0)
        applied_factors.append("Imprecise estimates (wide confidence intervals)")
    
    # Publication bias (rate down by 1 level)
    if "publication_bias" in factors:
        current_idx = max(current_idx - 1, 0)
        applied_factors.append("Suspected publication bias")
    
    return certainty_levels[current_idx], applied_factors


def assess_dose_response(
    kc: str,
    kc_analyses: List[Dict],
    study_metadata_list: List[Dict]
) -> bool:
    """
    Assess if evidence shows a dose-response relationship for a KC
    
    Dose-response requires:
    1. Multiple studies with different dose levels
    2. Graded effects (higher dose = stronger effect)
    3. Explicit mention of dose-response in text
    
    Args:
        kc: Key Characteristic identifier
        kc_analyses: List of KC analysis dicts
        study_metadata_list: List of study metadata dicts
        
    Returns:
        True if dose-response relationship is detected, False otherwise
    """
    kc_num = kc.replace("KC", "").lower()
    status_key = f"kc{kc_num}_status"
    
    # Get studies that support this KC
    supporting_studies = [
        (analysis, metadata) 
        for analysis, metadata in zip(kc_analyses, study_metadata_list)
        if analysis.get(status_key, "NOT_MENTIONED") == "SUPPORTED"
    ]
    
    if len(supporting_studies) < 2:
        return False  # Need at least 2 studies for dose-response
    
    # Check evidence quotes and reasoning for dose-response keywords
    dose_response_keywords = [
        "dose-response", "dose response", "dose-dependent", "dose dependent",
        "dose-related", "dose related", "concentration-dependent", "concentration dependent",
        "increased with dose", "higher dose", "lower dose", "graded",
        "dose escalation", "dose range"
    ]
    
    dose_response_mentions = 0
    
    for analysis, metadata in supporting_studies:
        # Check reasoning
        reasoning = analysis.get("reasoning", "").lower()
        if any(keyword in reasoning for keyword in dose_response_keywords):
            dose_response_mentions += 1
        
        # Check evidence quotes
        evidence_quotes = analysis.get("evidence_quotes", {}).get(kc, [])
        for quote in evidence_quotes:
            if any(keyword in quote.lower() for keyword in dose_response_keywords):
                dose_response_mentions += 1
                break  # Count once per study
    
    # Require explicit mention in at least 2 studies
    if dose_response_mentions >= 2:
        return True
    
    # Alternative: Check if metadata contains dose information and we can infer pattern
    # (This is less reliable, so we use it only as secondary check)
    doses_mentioned = []
    for analysis, metadata in supporting_studies:
        dose_info = metadata.get("dose", "")
        if dose_info and dose_info != "N/A":
            # Try to extract numeric dose values
            dose_match = re.search(r'(\d+\.?\d*)\s*(mg|g|μg|ng|mM|μM|nM)', dose_info, re.IGNORECASE)
            if dose_match:
                doses_mentioned.append((dose_match.group(1), dose_match.group(2)))
    
    # If we have multiple different doses, it's suggestive but not definitive
    # We still require explicit mention in text
    if len(set(doses_mentioned)) >= 2 and dose_response_mentions >= 1:
        return True
    
    return False


def assess_consistency(
    kc: str,
    kc_analyses: List[Dict]
) -> Tuple[bool, str]:
    """
    Assess consistency of evidence for a KC
    
    Consistency requires:
    1. Same direction of effect across studies
    2. Similar magnitude (if quantifiable)
    
    Args:
        kc: Key Characteristic identifier
        kc_analyses: List of KC analysis dicts
        
    Returns:
        Tuple of (is_consistent, rationale)
    """
    kc_num = kc.replace("KC", "").lower()
    status_key = f"kc{kc_num}_status"
    
    # IMPROVEMENT #2: Count all positive evidence types
    supported_count = sum(1 for analysis in kc_analyses 
                         if analysis.get(status_key, "NOT_MENTIONED") in ["SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"])
    refuted_count = sum(1 for analysis in kc_analyses 
                       if analysis.get(status_key, "NOT_MENTIONED") == "REFUTED")
    total_count = len(kc_analyses)
    
    if total_count == 0:
        return False, "No studies available"
    
    # Check for conflicting evidence
    if supported_count > 0 and refuted_count > 0:
        return False, f"Conflicting evidence: {supported_count} support, {refuted_count} refute"
    
    # Check consistency ratio
    consistency_ratio = supported_count / total_count if total_count > 0 else 0
    
    if consistency_ratio >= 0.8:
        return True, f"High consistency: {supported_count}/{total_count} studies support"
    elif consistency_ratio >= 0.5:
        return True, f"Moderate consistency: {supported_count}/{total_count} studies support"
    elif consistency_ratio < 0.3:
        return False, f"Low consistency: only {supported_count}/{total_count} studies support"
    else:
        return False, f"Inconsistent: {supported_count}/{total_count} studies support"


def assess_certainty_per_kc(
    kc: str,
    kc_analyses: List[Dict],
    rob_assessments: List[RiskOfBiasAssessment],
    study_metadata_list: List[Dict]
) -> CertaintyAssessment:
    """
    Assess certainty for a specific KC based on all evidence
    """
    # Count studies supporting this KC
    # KC format is "KC1", "KC2", etc., status key is "kc1_status", "kc2_status", etc.
    kc_num = kc.replace("KC", "").lower()
    # IMPROVEMENT #2: Count all positive evidence types (SUPPORTED, ASSOCIATED, CAUSALLY_LINKED)
    supported_count = sum(1 for analysis in kc_analyses 
                         if analysis.get(f"kc{kc_num}_status", "NOT_MENTIONED") in ["SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"])
    total_count = len(kc_analyses)
    
    # Also check the boolean KC field for backward compatibility
    if supported_count == 0:
        supported_count = sum(1 for analysis in kc_analyses 
                             if analysis.get(kc, False))
    
    if supported_count == 0:
        return CertaintyAssessment(
            kc=kc,
            initial_certainty="Very Low",
            final_certainty="Very Low",
            rationale="No evidence found for this KC"
        )
    
    # IMPROVEMENT #4: Use study type and species from RoB assessments (more reliable)
    study_types = []
    species_list = []
    
    # First, try to get from RoB assessments (more structured)
    for rob in rob_assessments:
        if hasattr(rob, 'study_type') and rob.study_type:
            study_types.append(rob.study_type)
        if hasattr(rob, 'species') and rob.species:
            species_list.append(rob.species)
    
    # Fallback to metadata if RoB doesn't have it
    if not study_types:
        for metadata in study_metadata_list:
            study_types.append(metadata.get("study_type", "Unknown"))
    if not species_list:
        for metadata in study_metadata_list:
            species_list.append(metadata.get("species", "Unknown"))
    
    # Use most common study type/species (IMPROVEMENT #4: Prioritize human studies)
    # Weight by study quality: human studies get priority
    if species_list:
        human_studies = [s for s in species_list if "human" in str(s).lower() or "Human" in str(s)]
        if human_studies:
            most_common_species = "Human"  # Prioritize human evidence
            most_common_type = "human cohort" if "cohort" in str(study_types).lower() else "human observational"
        else:
            most_common_species = max(set(species_list), key=species_list.count) if species_list else None
            most_common_type = max(set(study_types), key=study_types.count) if study_types else "Unknown"
    else:
        most_common_species = None
        most_common_type = "Unknown"
    
    initial_certainty = calculate_initial_certainty(most_common_type, most_common_species)
    
    # Assess factors for rating up/down
    factors_up = []
    factors_down = []
    
    # Check consistency using dedicated function
    is_consistent, consistency_rationale = assess_consistency(kc, kc_analyses)
    if is_consistent and total_count >= 3:
        factors_up.append("consistency")
    elif not is_consistent:
        factors_down.append("inconsistency")
    
    # Check risk of bias
    if rob_assessments:
        rob_stats = calculate_rob_summary_stats(rob_assessments)
        low_risk_pct = rob_stats.get("low_risk_percentage", 0)
        high_risk_pct = (rob_stats.get("overall_distribution", {}).get("High", 0) + 
                        rob_stats.get("overall_distribution", {}).get("Critical", 0)) / rob_stats.get("total_studies", 1) * 100
        
        # Rate down if high proportion of high/critical risk studies
        if high_risk_pct >= 50:
            factors_down.append("risk_of_bias")
        # Also rate down if many have insufficient information (can't assess quality)
        insufficient_pct = rob_stats.get("insufficient_info_count", 0) / rob_stats.get("total_studies", 1) * 100
        if insufficient_pct >= 50:
            factors_down.append("risk_of_bias")  # Can't assess quality
    
    # Check indirectness (non-human studies)
    if most_common_species and most_common_species not in ["Human"]:
        factors_down.append("indirectness")
    
    # Check imprecision (few studies or wide confidence intervals)
    # GRADE: Rate down if <400 events (for dichotomous) or wide CI
    # For KC presence/absence, we use study count as proxy
    if total_count < 3:
        factors_down.append("imprecision")
    
    # Check for dose-response relationship
    # CRITICAL: Dose-response requires evidence of graded effects across doses
    # Simply having multiple studies does NOT imply dose-response
    dose_response_detected = assess_dose_response(kc, kc_analyses, study_metadata_list)
    if dose_response_detected:
        factors_up.append("dose_response")
    
    # Apply rating up/down
    final_certainty, applied_up = rate_up_certainty(initial_certainty, factors_up)
    final_certainty, applied_down = rate_down_certainty(final_certainty, factors_down)
    
    # Build rationale
    rationale_parts = [f"Initial certainty: {initial_certainty} (based on {most_common_type} studies"]
    if most_common_species:
        rationale_parts.append(f"in {most_common_species}")
    rationale_parts.append(")")
    
    if applied_up:
        rationale_parts.append(f"Rated up due to: {', '.join(applied_up)}")
    if applied_down:
        rationale_parts.append(f"Rated down due to: {', '.join(applied_down)}")
    
    rationale_parts.append(f"Final certainty: {final_certainty}")
    rationale = ". ".join(rationale_parts)
    
    return CertaintyAssessment(
        kc=kc,
        initial_certainty=initial_certainty,
        factors_up=applied_up,
        factors_down=applied_down,
        final_certainty=final_certainty,
        rationale=rationale
    )


def create_certainty_summary_table(certainty_assessments: List[CertaintyAssessment]) -> Dict:
    """
    Create a summary table of certainty assessments for all KCs
    """
    summary = {
        "kc": [],
        "initial_certainty": [],
        "final_certainty": [],
        "factors_up": [],
        "factors_down": [],
        "rationale": []
    }
    
    for assessment in certainty_assessments:
        summary["kc"].append(assessment.kc)
        summary["initial_certainty"].append(assessment.initial_certainty)
        summary["final_certainty"].append(assessment.final_certainty)
        summary["factors_up"].append(", ".join(assessment.factors_up) if assessment.factors_up else "None")
        summary["factors_down"].append(", ".join(assessment.factors_down) if assessment.factors_down else "None")
        summary["rationale"].append(assessment.rationale)
    
    return summary
