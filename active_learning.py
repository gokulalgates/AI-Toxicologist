"""
Active Learning Module
Prioritizes abstracts based on uncertainty, information gain, and impact
"""

from collections import defaultdict
from typing import Dict, List, Optional

import numpy as np


def score_abstract_uncertainty(
    abstract: Dict,
    existing_analyses: Optional[List[Dict]] = None
) -> float:
    """
    Score abstract by prediction uncertainty
    
    Higher score = more uncertain = higher priority for analysis
    
    Args:
        abstract: Abstract dict with title, abstract, etc.
        existing_analyses: Optional list of existing analyses for this chemical
    
    Returns:
        Uncertainty score (0.0 to 1.0)
    """
    # Simple heuristic: abstracts with less common words might be more uncertain
    # In practice, this would use model confidence scores

    text = abstract.get("abstract", "") + " " + abstract.get("title", "")

    # Count unique words (more unique = potentially more novel = more uncertain)
    words = text.lower().split()
    unique_ratio = len(set(words)) / len(words) if words else 0.0

    # Length factor (very short or very long abstracts might be more uncertain)
    length_factor = 1.0
    text_length = len(text)
    if text_length < 200:
        length_factor = 1.2  # Very short = uncertain
    elif text_length > 5000:
        length_factor = 1.1  # Very long = potentially complex

    uncertainty = min(unique_ratio * length_factor, 1.0)
    return uncertainty


def score_abstract_information_gain(
    abstract: Dict,
    existing_analyses: List[Dict],
    kc: Optional[str] = None
) -> float:
    """
    Score abstract by potential information gain
    
    Higher score = more novel information = higher priority
    
    Args:
        abstract: Abstract to score
        existing_analyses: List of existing analyses
        kc: Optional KC to focus on
    
    Returns:
        Information gain score (0.0 to 1.0)
    """
    if not existing_analyses:
        return 1.0  # First abstract has maximum information gain

    # Count how many KCs are already well-covered
    kc_coverage = defaultdict(int)
    for analysis in existing_analyses:
        for i in range(1, 13):
            kc_name = f"KC{i}"
            kc_num = kc_name.replace("KC", "").lower()
            status_key = f"kc{kc_num}_status"
            if analysis.get(status_key) == "SUPPORTED":
                kc_coverage[kc_name] += 1

    # If focusing on specific KC, check its coverage
    if kc:
        coverage = kc_coverage.get(kc, 0)
        # Lower coverage = higher information gain
        info_gain = 1.0 / (1.0 + coverage * 0.5)
        return min(info_gain, 1.0)

    # Overall information gain based on least covered KCs
    if not kc_coverage:
        return 1.0

    min_coverage = min(kc_coverage.values()) if kc_coverage else 0
    max_coverage = max(kc_coverage.values()) if kc_coverage else 0

    # Higher gain if coverage is uneven (some KCs need more data)
    coverage_variance = np.var(list(kc_coverage.values())) if kc_coverage else 0
    info_gain = min(0.5 + coverage_variance / 10.0, 1.0)

    return info_gain


def score_abstract_impact(
    abstract: Dict
) -> float:
    """
    Score abstract by impact factors
    
    Args:
        abstract: Abstract dict
    
    Returns:
        Impact score (0.0 to 1.0)
    """
    impact_score = 0.5  # Base score

    # Recent papers might be more impactful
    year = abstract.get("year")
    if year:
        current_year = 2024  # Update as needed
        age = current_year - year
        if age <= 2:
            impact_score += 0.2  # Very recent
        elif age <= 5:
            impact_score += 0.1  # Recent

    # High-impact journals (simplified heuristic)
    journal = abstract.get("journal", "").lower()
    high_impact_journals = [
        "nature", "science", "cell", "lancet", "nejm",
        "toxicological sciences", "toxicology", "hepatology"
    ]
    if any(hij in journal for hij in high_impact_journals):
        impact_score += 0.2

    # Title keywords suggesting importance
    title = abstract.get("title", "").lower()
    important_keywords = [
        "mechanism", "pathway", "causal", "novel", "first",
        "systematic", "meta-analysis", "review"
    ]
    keyword_count = sum(1 for kw in important_keywords if kw in title)
    impact_score += min(keyword_count * 0.05, 0.1)

    return min(impact_score, 1.0)


def select_abstracts_for_analysis(
    abstracts: List[Dict],
    existing_analyses: Optional[List[Dict]] = None,
    max_select: int = 20,
    weights: Optional[Dict[str, float]] = None
) -> List[Dict]:
    """
    Select abstracts using active learning
    
    Args:
        abstracts: List of all abstracts
        existing_analyses: Optional existing analyses
        max_select: Maximum number to select
        weights: Optional weights for scoring factors
                 {"uncertainty": 0.4, "information_gain": 0.4, "impact": 0.2}
    
    Returns:
        Selected abstracts sorted by priority
    """
    if weights is None:
        weights = {
            "uncertainty": 0.4,
            "information_gain": 0.4,
            "impact": 0.2
        }

    scored_abstracts = []

    for abstract in abstracts:
        uncertainty_score = score_abstract_uncertainty(abstract, existing_analyses)
        info_gain_score = score_abstract_information_gain(abstract, existing_analyses or [])
        impact_score = score_abstract_impact(abstract)

        # Combined score
        combined_score = (
            uncertainty_score * weights["uncertainty"] +
            info_gain_score * weights["information_gain"] +
            impact_score * weights["impact"]
        )

        scored_abstracts.append({
            **abstract,
            "active_learning_score": combined_score,
            "uncertainty_score": uncertainty_score,
            "information_gain_score": info_gain_score,
            "impact_score": impact_score
        })

    # Sort by score (descending)
    scored_abstracts.sort(key=lambda x: x["active_learning_score"], reverse=True)

    # Return top max_select
    return scored_abstracts[:max_select]


def prioritize_by_kc_coverage(
    abstracts: List[Dict],
    target_kcs: List[str],
    existing_analyses: Optional[List[Dict]] = None
) -> List[Dict]:
    """
    Prioritize abstracts that might cover target KCs
    
    Args:
        abstracts: List of abstracts
        target_kcs: List of KC identifiers to prioritize
        existing_analyses: Optional existing analyses
    
    Returns:
        Prioritized abstracts
    """
    # Simple keyword matching for KC-related content
    kc_keywords = {
        "KC1": ["metabolism", "bioactivation", "reactive", "metabolite", "cyp", "phase i"],
        "KC2": ["apoptosis", "necrosis", "cell death", "hepatocyte death"],
        "KC5": ["oxidative stress", "ros", "reactive oxygen", "antioxidant"],
        "KC7": ["mitochondrial", "mitochondria", "atp", "respiratory chain"],
        "KC11": ["fibrosis", "fibrotic", "collagen", "scarring"],
    }

    scored_abstracts = []

    for abstract in abstracts:
        text = (abstract.get("abstract", "") + " " + abstract.get("title", "")).lower()

        kc_matches = 0
        for kc in target_kcs:
            keywords = kc_keywords.get(kc, [])
            if any(kw in text for kw in keywords):
                kc_matches += 1

        score = kc_matches / len(target_kcs) if target_kcs else 0.0

        scored_abstracts.append({
            **abstract,
            "kc_coverage_score": score
        })

    scored_abstracts.sort(key=lambda x: x["kc_coverage_score"], reverse=True)
    return scored_abstracts
