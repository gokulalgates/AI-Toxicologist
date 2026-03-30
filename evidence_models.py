"""
Enhanced data models for publication-grade systematic review
Includes sentence-level evidence capture, risk-of-bias, and provenance
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


class EvidenceQuote(BaseModel):
    """Sentence-level evidence quote for a KC"""
    kc: str = Field(description="Key Characteristic identifier (e.g., KC1)")
    quote: str = Field(description="Exact quote from the abstract/text")
    span_start: Optional[int] = Field(None, description="Character position start")
    span_end: Optional[int] = Field(None, description="Character position end")
    page_ref: Optional[str] = Field(None, description="Page/figure reference if available")


class CausalLinkWithEvidence(BaseModel):
    """Causal link with explicit evidence quotes"""
    source: str = Field(description="Source KC (e.g., 'KC1')")
    target: str = Field(description="Target KC (e.g., 'KC5')")
    evidence: str = Field(description="Text evidence supporting this causal link")
    evidence_quotes: List[str] = Field(default_factory=list, description="Exact quotes")
    strength: Literal["STRONG", "MODERATE", "WEAK"] = Field(default="MODERATE")
    direction_explicit: bool = Field(True, description="Whether direction is explicitly stated")


class StudyMetadata(BaseModel):
    """Metadata for each study"""
    pmid: str
    doi: Optional[str] = None
    title: str
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None
    species: Optional[str] = Field(None, description="Human, Rat, Mouse, in vitro, etc.")
    model: Optional[str] = Field(None, description="Specific model details")
    dose: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None
    comparator: Optional[str] = None


class RiskOfBiasDomain(BaseModel):
    """Risk-of-bias assessment for a single domain"""
    domain: str = Field(description="Domain name (e.g., 'Selection Bias', 'Confounding')")
    judgment: Literal["Low", "Some concerns", "High", "Critical", "N/A", "Insufficient information"] = Field(description="RoB judgment")
    rationale: str = Field(description="Justification for judgment")
    supporting_quote: Optional[str] = Field(None, description="Quote supporting the judgment")
    information_available: bool = Field(True, description="Whether abstract/full-text contains enough information to assess this domain")


class RiskOfBiasAssessment(BaseModel):
    """Complete risk-of-bias assessment for a study"""
    study_id: str = Field(description="PMID or study identifier")
    instrument: str = Field(description="RoB instrument used (OHAT, ROBINS-I, RoB 2, etc.)")
    domains: List[RiskOfBiasDomain] = Field(default_factory=list)
    overall_judgment: Literal["Low", "Some concerns", "High", "Critical", "Insufficient information"] = Field(description="Overall RoB")
    assessed_by: Optional[str] = Field(None, description="Reviewer/model identifier")
    assessment_date: Optional[datetime] = Field(default_factory=datetime.now)
    fulltext_used: bool = Field(False, description="Whether full-text was used for assessment (vs abstract only)")
    study_type: Optional[str] = Field(None, description="Study type: in vitro, in vivo, animal, human cohort, etc. (IMPROVEMENT #3)")
    species: Optional[str] = Field(None, description="Species: Human, Rat, Mouse, primary hepatocytes, etc. (IMPROVEMENT #3)")
    cell_line: Optional[str] = Field(None, description="Cell line if in vitro study (IMPROVEMENT #3)")


class KCAnalysisEnhanced(BaseModel):
    """Enhanced KC analysis with sentence-level evidence and RoB"""
    # KC statuses with evidence (IMPROVEMENT #2: Multi-level evidence system)
    # Statuses: SUPPORTED, ASSOCIATED, CAUSALLY_LINKED, REFUTED, NOT_MENTIONED
    # - SUPPORTED: Explicitly states chemical causes this effect
    # - ASSOCIATED: Chemical is associated with this effect (correlation, not explicit causation)
    # - CAUSALLY_LINKED: Effect occurs but through another KC (indirect causation)
    # - REFUTED: Explicitly states chemical does NOT cause this effect
    # - NOT_MENTIONED: Not discussed
    kc1_status: str = Field(default="NOT_MENTIONED")
    kc2_status: str = Field(default="NOT_MENTIONED")
    kc3_status: str = Field(default="NOT_MENTIONED")
    kc4_status: str = Field(default="NOT_MENTIONED")
    kc5_status: str = Field(default="NOT_MENTIONED")
    kc6_status: str = Field(default="NOT_MENTIONED")
    kc7_status: str = Field(default="NOT_MENTIONED")
    kc8_status: str = Field(default="NOT_MENTIONED")
    kc9_status: str = Field(default="NOT_MENTIONED")
    kc10_status: str = Field(default="NOT_MENTIONED")
    kc11_status: str = Field(default="NOT_MENTIONED")
    kc12_status: str = Field(default="NOT_MENTIONED")
    
    # Evidence quotes per KC
    evidence_quotes: Dict[str, List[EvidenceQuote]] = Field(
        default_factory=dict,
        description="Evidence quotes keyed by KC (e.g., 'KC1': [quotes...])"
    )
    
    # Causal links with evidence
    causal_links: List[CausalLinkWithEvidence] = Field(default_factory=list)
    
    # Dose-response data
    dose_response: List[str] = Field(
        default_factory=list,
        description="Dose-response information extracted from text (e.g., '50 mg/kg')"
    )
    
    # Reasoning
    reasoning: str = Field(description="Step-by-step reasoning")
    
    # Abstention flag
    abstain: bool = Field(False, description="Whether model abstained due to uncertainty")
    uncertainty_level: Optional[str] = Field(None, description="Low/Medium/High uncertainty")


class CertaintyAssessment(BaseModel):
    """GRADE/OHAT-style certainty assessment per KC"""
    kc: str = Field(description="Key Characteristic identifier")
    initial_certainty: Literal["High", "Moderate", "Low", "Very Low"] = Field(
        default="Low",
        description="Starting certainty (Low for non-human evidence)"
    )
    factors_up: List[str] = Field(default_factory=list, description="Factors increasing certainty")
    factors_down: List[str] = Field(default_factory=list, description="Factors decreasing certainty")
    final_certainty: Literal["High", "Moderate", "Low", "Very Low"] = Field(description="Final certainty rating")
    rationale: str = Field(description="Justification for final rating")


class StudyRecord(BaseModel):
    """Complete record for a single study in the review"""
    metadata: StudyMetadata
    kc_analysis: KCAnalysisEnhanced
    risk_of_bias: Optional[RiskOfBiasAssessment] = None
    certainty_assessments: List[CertaintyAssessment] = Field(default_factory=list)
    inclusion_reason: Optional[str] = Field(None, description="Why included/excluded")
    screening_stage: Literal["title_abstract", "full_text", "included", "excluded"] = Field(description="Current stage")
    extracted_by: Optional[str] = Field(None, description="Extractor identifier")
    extraction_date: Optional[datetime] = Field(default_factory=datetime.now)
    provenance: Dict[str, str] = Field(default_factory=dict, description="Model version, prompt hash, etc.")


class PRISMARecord(BaseModel):
    """PRISMA flow tracking"""
    chemical_name: str
    search_date: datetime
    databases_searched: List[str] = Field(default_factory=list)
    total_records_identified: int = 0
    duplicates_removed: int = 0
    records_screened_title_abstract: int = 0
    records_excluded_title_abstract: int = 0
    records_sought_full_text: int = 0
    records_not_retrieved: int = 0
    records_assessed_full_text: int = 0
    records_excluded_full_text: int = 0
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)
    studies_included: int = 0
    studies_included_list: List[str] = Field(default_factory=list, description="PMIDs of included studies")
