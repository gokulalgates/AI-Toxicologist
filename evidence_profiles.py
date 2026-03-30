"""
Evidence Profile Cards per KC
Creates human-readable evidence summaries for each Key Characteristic
"""

from typing import List, Dict
from evidence_models import CertaintyAssessment


def create_evidence_profile_card(
    kc: str,
    kc_name: str,
    kc_analyses: List[Dict],
    certainty_assessment: CertaintyAssessment,
    evidence_quotes: List[str]
) -> str:
    """
    Create a formatted evidence profile card for a single KC
    """
    supported_count = sum(1 for analysis in kc_analyses 
                         if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "SUPPORTED")
    refuted_count = sum(1 for analysis in kc_analyses 
                       if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "REFUTED")
    total_count = len(kc_analyses)
    
    card = f"""
{'='*70}
{kc}: {kc_name}
{'='*70}

EVIDENCE SUMMARY:
  • Studies Supporting: {supported_count}/{total_count}
  • Studies Refuting: {refuted_count}/{total_count}
  • Certainty of Evidence: {certainty_assessment.final_certainty}

CERTAINTY ASSESSMENT:
  • Initial Certainty: {certainty_assessment.initial_certainty}
"""
    
    if certainty_assessment.factors_up:
        card += f"  • Factors Increasing Certainty: {', '.join(certainty_assessment.factors_up)}\n"
    
    if certainty_assessment.factors_down:
        card += f"  • Factors Decreasing Certainty: {', '.join(certainty_assessment.factors_down)}\n"
    
    card += f"\nRATIONALE:\n  {certainty_assessment.rationale}\n"
    
    if evidence_quotes:
        card += f"\nKEY EVIDENCE QUOTES ({len(evidence_quotes)}):\n"
        for i, quote in enumerate(evidence_quotes[:5], 1):  # Limit to top 5
            card += f"  {i}. \"{quote[:200]}{'...' if len(quote) > 200 else ''}\"\n"
    
    return card


def create_all_evidence_profiles(
    kc_analyses: List[Dict],
    certainty_assessments: List[CertaintyAssessment],
    kc_names: Dict[str, str]
) -> str:
    """
    Create evidence profile cards for all KCs that have evidence
    """
    profiles = []
    
    for certainty in certainty_assessments:
        kc = certainty.kc
        kc_name = kc_names.get(kc, kc)
        
        # Collect evidence quotes for this KC
        quotes = []
        for analysis in kc_analyses:
            kc_quotes = analysis.get("evidence_quotes", {}).get(kc, [])
            if isinstance(kc_quotes, list):
                quotes.extend(kc_quotes)
        
        # Only create profile if there's evidence
        supported_count = sum(1 for analysis in kc_analyses 
                             if analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "SUPPORTED")
        
        if supported_count > 0 or certainty.final_certainty != "Very Low":
            profile = create_evidence_profile_card(
                kc, kc_name, kc_analyses, certainty, quotes
            )
            profiles.append(profile)
    
    return "\n".join(profiles)
