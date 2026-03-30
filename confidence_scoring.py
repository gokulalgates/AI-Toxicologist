"""
Confidence Scoring Module
Implements self-consistency and logprob-based confidence estimation for LLM predictions
"""

from collections import Counter
from typing import Dict, List, Tuple

import numpy as np


def calculate_self_consistency_confidence(
    analyses: List[Dict],
    kc: str
) -> float:
    """
    Calculate confidence based on self-consistency across multiple runs
    
    Args:
        analyses: List of analysis dicts from multiple runs
        kc: Key Characteristic identifier (e.g., "KC1")
    
    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not analyses:
        return 0.0

    kc_num = kc.replace("KC", "").lower()
    status_key = f"kc{kc_num}_status"

    # Get all statuses for this KC
    statuses = [analysis.get(status_key, "NOT_MENTIONED") for analysis in analyses]

    # Calculate agreement (proportion of most common status)
    if not statuses:
        return 0.0

    status_counts = Counter(statuses)
    most_common_count = status_counts.most_common(1)[0][1]
    agreement = most_common_count / len(statuses)

    return agreement


def analyze_with_confidence(
    abstract_text: str,
    title: str,
    model_name: str,
    num_runs: int = 3,
    analyze_func=None
) -> Tuple[Dict, float]:
    """
    Analyze abstract multiple times and calculate confidence
    
    Args:
        abstract_text: Abstract text to analyze
        title: Paper title
        model_name: Model to use
        num_runs: Number of times to run analysis (default: 3)
        analyze_func: Function to analyze abstract (from app.py)
    
    Returns:
        Tuple of (consensus_analysis, confidence_score)
    """
    if analyze_func is None:
        raise ValueError("analyze_func must be provided")

    # Run analysis multiple times
    analyses = []
    for i in range(num_runs):
        try:
            analysis, _ = analyze_func(abstract_text, title, model_name)
            analyses.append(analysis)
        except Exception as e:
            print(f"Warning: Analysis run {i+1} failed: {e}")
            continue

    if not analyses:
        # Return empty analysis with low confidence
        empty_analysis = {f"kc{i}_status": "NOT_MENTIONED" for i in range(1, 13)}
        return empty_analysis, 0.0

    # Calculate consensus for each KC
    consensus_analysis = {}
    kc_names = [f"KC{i}" for i in range(1, 13)]

    overall_confidence_scores = []

    for kc in kc_names:
        kc_num = kc.replace("KC", "").lower()
        status_key = f"kc{kc_num}_status"

        # Get confidence for this KC
        kc_confidence = calculate_self_consistency_confidence(analyses, kc)
        overall_confidence_scores.append(kc_confidence)

        # Get consensus status
        statuses = [a.get(status_key, "NOT_MENTIONED") for a in analyses]
        status_counts = Counter(statuses)
        consensus_status = status_counts.most_common(1)[0][0]

        consensus_analysis[status_key] = consensus_status
        consensus_analysis[kc] = consensus_status == "SUPPORTED"
        consensus_analysis[f"{kc}_confidence"] = kc_confidence

    # Overall confidence is average across all KCs
    overall_confidence = np.mean(overall_confidence_scores) if overall_confidence_scores else 0.0

    # Copy other fields from first analysis
    for key in ["reasoning", "causal_links", "evidence_quotes", "dose_response", "pmid", "title"]:
        if key in analyses[0]:
            consensus_analysis[key] = analyses[0][key]

    consensus_analysis["confidence_score"] = overall_confidence
    consensus_analysis["num_runs"] = len(analyses)

    return consensus_analysis, overall_confidence


def filter_low_confidence_predictions(
    analyses: List[Dict],
    confidence_threshold: float = 0.6
) -> Tuple[List[Dict], List[Dict]]:
    """
    Filter out low-confidence predictions
    
    Args:
        analyses: List of analysis dicts with confidence scores
        confidence_threshold: Minimum confidence to keep (default: 0.6)
    
    Returns:
        Tuple of (high_confidence_analyses, low_confidence_analyses)
    """
    high_confidence = []
    low_confidence = []

    for analysis in analyses:
        confidence = analysis.get("confidence_score", 0.0)
        if confidence >= confidence_threshold:
            high_confidence.append(analysis)
        else:
            low_confidence.append(analysis)

    return high_confidence, low_confidence


def calculate_kc_confidence_distribution(
    analyses: List[Dict]
) -> Dict[str, Dict]:
    """
    Calculate confidence distribution per KC
    
    Args:
        analyses: List of analysis dicts with confidence scores
    
    Returns:
        Dict mapping KC to confidence statistics
    """
    kc_names = [f"KC{i}" for i in range(1, 13)]
    kc_confidences = {kc: [] for kc in kc_names}

    for analysis in analyses:
        for kc in kc_names:
            confidence_key = f"{kc}_confidence"
            if confidence_key in analysis:
                kc_confidences[kc].append(analysis[confidence_key])

    # Calculate statistics
    stats = {}
    for kc, confidences in kc_confidences.items():
        if confidences:
            stats[kc] = {
                "mean": np.mean(confidences),
                "std": np.std(confidences),
                "min": np.min(confidences),
                "max": np.max(confidences),
                "median": np.median(confidences)
            }
        else:
            stats[kc] = {
                "mean": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "median": 0.0
            }

    return stats
