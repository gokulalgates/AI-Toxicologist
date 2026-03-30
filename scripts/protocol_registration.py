"""
Protocol Registration Templates for Systematic Reviews

This module provides templates and utilities for registering systematic review protocols
on platforms like PROSPERO or Open Science Framework (OSF).
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ProtocolRegistration:
    """Protocol registration information following PROSPERO/OSF standards"""
    # Basic Information
    title: str
    review_question: str
    objectives: List[str]

    # Eligibility Criteria
    inclusion_criteria: Dict[str, List[str]]  # e.g., {"population": [...], "intervention": [...], "outcome": [...]}
    exclusion_criteria: List[str]

    # Search Strategy
    databases: List[str]  # e.g., ["PubMed", "Embase", "Web of Science"]
    search_terms: Dict[str, List[str]]  # e.g., {"chemical": [...], "outcome": [...]}
    search_filters: Optional[Dict[str, Any]] = None

    # Study Selection
    selection_process: str  # Description of screening process
    number_of_reviewers: int = 1

    # Data Extraction
    data_extraction_items: List[str]
    extraction_process: str

    # Risk of Bias
    rob_instrument: str  # e.g., "OHAT", "ROBINS-I", "RoB 2"
    rob_domains: List[str]

    # Certainty Assessment
    certainty_framework: str  # e.g., "GRADE", "OHAT"

    # Analysis Plan
    synthesis_method: str  # e.g., "narrative", "meta-analysis", "network analysis"

    # Registration Metadata
    registration_date: Optional[str] = None
    registration_id: Optional[str] = None
    registration_platform: Optional[str] = None  # "PROSPERO", "OSF", etc.

    # Contact Information
    contact_email: Optional[str] = None
    affiliation: Optional[str] = None


def create_prospero_template(protocol: ProtocolRegistration) -> Dict[str, Any]:
    """
    Create PROSPERO registration template
    
    PROSPERO is the international prospective register of systematic reviews
    """
    prospero_template = {
        "Review title": protocol.title,
        "Review question": protocol.review_question,
        "Objectives": {
            "Primary": protocol.objectives[0] if protocol.objectives else "",
            "Secondary": protocol.objectives[1:] if len(protocol.objectives) > 1 else []
        },
        "Eligibility criteria": {
            "Inclusion criteria": protocol.inclusion_criteria,
            "Exclusion criteria": protocol.exclusion_criteria
        },
        "Search strategy": {
            "Databases": protocol.databases,
            "Search terms": protocol.search_terms,
            "Search filters": protocol.search_filters or {}
        },
        "Study selection": {
            "Selection process": protocol.selection_process,
            "Number of reviewers": protocol.number_of_reviewers
        },
        "Data extraction": {
            "Items to extract": protocol.data_extraction_items,
            "Extraction process": protocol.extraction_process
        },
        "Risk of bias": {
            "Instrument": protocol.rob_instrument,
            "Domains": protocol.rob_domains
        },
        "Certainty assessment": {
            "Framework": protocol.certainty_framework
        },
        "Synthesis": {
            "Method": protocol.synthesis_method
        },
        "Registration": {
            "Date": protocol.registration_date or datetime.now().isoformat(),
            "ID": protocol.registration_id or "PENDING",
            "Platform": protocol.registration_platform or "PROSPERO"
        },
        "Contact": {
            "Email": protocol.contact_email,
            "Affiliation": protocol.affiliation
        }
    }

    return prospero_template


def create_osf_template(protocol: ProtocolRegistration) -> Dict[str, Any]:
    """
    Create Open Science Framework (OSF) registration template
    """
    osf_template = {
        "title": protocol.title,
        "description": protocol.review_question,
        "category": "Systematic Review",
        "tags": ["toxicology", "hepatotoxicity", "systematic-review", "ai-assisted"],
        "protocol": {
            "objectives": protocol.objectives,
            "eligibility_criteria": {
                "inclusion": protocol.inclusion_criteria,
                "exclusion": protocol.exclusion_criteria
            },
            "search_strategy": {
                "databases": protocol.databases,
                "search_terms": protocol.search_terms
            },
            "data_collection": {
                "selection_process": protocol.selection_process,
                "extraction_items": protocol.data_extraction_items
            },
            "risk_of_bias": {
                "instrument": protocol.rob_instrument,
                "domains": protocol.rob_domains
            },
            "certainty_assessment": {
                "framework": protocol.certainty_framework
            },
            "synthesis": {
                "method": protocol.synthesis_method
            }
        },
        "registration": {
            "date": protocol.registration_date or datetime.now().isoformat(),
            "id": protocol.registration_id or "PENDING",
            "platform": "OSF"
        }
    }

    return osf_template


def save_protocol_registration(
    protocol: ProtocolRegistration,
    output_file: str,
    format: str = "json"
) -> str:
    """
    Save protocol registration to file
    
    Args:
        protocol: ProtocolRegistration object
        output_file: Path to output file
        format: "json" or "prospero" or "osf"
    
    Returns:
        Path to saved file
    """
    if format == "prospero":
        template = create_prospero_template(protocol)
    elif format == "osf":
        template = create_osf_template(protocol)
    else:
        template = asdict(protocol)

    with open(output_file, 'w') as f:
        json.dump(template, f, indent=2)

    return output_file


def create_default_protocol(chemical_name: str) -> ProtocolRegistration:
    """
    Create a default protocol template for a chemical
    
    This can be customized for specific reviews
    """
    return ProtocolRegistration(
        title=f"Systematic Review of Hepatotoxicity Mechanisms for {chemical_name}",
        review_question=f"What are the key characteristics (mechanisms) of hepatotoxicity for {chemical_name}?",
        objectives=[
            f"Identify and characterize the key mechanisms of hepatotoxicity for {chemical_name}",
            "Assess the quality of evidence for each mechanism",
            "Evaluate the certainty of evidence using GRADE/OHAT framework"
        ],
        inclusion_criteria={
            "population": ["Human studies", "Animal studies", "In vitro studies"],
            "intervention": [f"Exposure to {chemical_name}"],
            "outcome": [
                "Hepatotoxicity", "Liver injury", "Liver damage",
                "Key Characteristics of Human Hepatotoxicants"
            ],
            "study_design": ["All study types"]
        },
        exclusion_criteria=[
            "Studies not reporting hepatotoxicity outcomes",
            "Studies with insufficient data",
            "Non-English publications (if applicable)"
        ],
        databases=["PubMed"],  # Can be expanded to include Embase, Web of Science
        search_terms={
            "chemical": [chemical_name],
            "outcome": ["hepatotoxicity", "liver injury", "DILI", "drug-induced liver injury"]
        },
        selection_process="Two-stage screening: title/abstract followed by full-text",
        number_of_reviewers=1,  # Can be increased for human review
        data_extraction_items=[
            "Study characteristics (species, model, dose, route, duration)",
            "Key Characteristic assessments (KC1-KC12)",
            "Causal links between KCs",
            "Risk of bias assessment",
            "Certainty of evidence"
        ],
        extraction_process="Structured data extraction using predefined forms",
        rob_instrument="OHAT",
        rob_domains=[
            "Selection Bias",
            "Performance Bias",
            "Attrition Bias",
            "Detection Bias",
            "Reporting Bias"
        ],
        certainty_framework="GRADE",
        synthesis_method="Narrative synthesis with evidence profiles and network analysis"
    )
