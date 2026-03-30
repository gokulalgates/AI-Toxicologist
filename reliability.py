"""
Reliability assessment: Cohen's kappa and Gwet's AC1 for inter-rater agreement
"""

from typing import Dict, List

import numpy as np


def cohens_kappa(ratings_1: List[str], ratings_2: List[str]) -> Dict:
    """
    Calculate Cohen's kappa for inter-rater agreement
    ratings_1, ratings_2: Lists of ratings (e.g., ["SUPPORTED", "NOT_MENTIONED", ...])
    Returns: dict with kappa, interpretation, and agreement matrix
    """
    if len(ratings_1) != len(ratings_2):
        raise ValueError("Ratings lists must have same length")

    # Get unique categories
    categories = sorted(set(ratings_1 + ratings_2))

    # Build confusion matrix
    n = len(categories)
    matrix = np.zeros((n, n), dtype=int)

    category_to_idx = {cat: i for i, cat in enumerate(categories)}

    for r1, r2 in zip(ratings_1, ratings_2):
        idx1 = category_to_idx[r1]
        idx2 = category_to_idx[r2]
        matrix[idx1, idx2] += 1

    # Calculate observed agreement
    po = np.trace(matrix) / np.sum(matrix)

    # Calculate expected agreement
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)
    pe = np.sum(row_sums * col_sums) / (np.sum(matrix) ** 2)

    # Calculate kappa
    if pe == 1:
        kappa = 1.0  # Perfect agreement
    else:
        kappa = (po - pe) / (1 - pe)

    # Interpretation
    if kappa < 0:
        interpretation = "Poor (worse than chance)"
    elif kappa < 0.2:
        interpretation = "Slight"
    elif kappa < 0.4:
        interpretation = "Fair"
    elif kappa < 0.6:
        interpretation = "Moderate"
    elif kappa < 0.8:
        interpretation = "Substantial"
    else:
        interpretation = "Almost perfect"

    return {
        "kappa": kappa,
        "interpretation": interpretation,
        "observed_agreement": po,
        "expected_agreement": pe,
        "agreement_matrix": matrix.tolist(),
        "categories": categories
    }


def gwets_ac1(ratings_1: List[str], ratings_2: List[str]) -> Dict:
    """
    Calculate Gwet's AC1 (alternative to kappa, less affected by prevalence)
    Better for imbalanced data (e.g., many NOT_MENTIONED vs few SUPPORTED)
    """
    if len(ratings_1) != len(ratings_2):
        raise ValueError("Ratings lists must have same length")

    categories = sorted(set(ratings_1 + ratings_2))
    n_categories = len(categories)

    # Build agreement matrix
    matrix = np.zeros((n_categories, n_categories), dtype=int)
    category_to_idx = {cat: i for i, cat in enumerate(categories)}

    for r1, r2 in zip(ratings_1, ratings_2):
        idx1 = category_to_idx[r1]
        idx2 = category_to_idx[r2]
        matrix[idx1, idx2] += 1

    n_total = np.sum(matrix)

    # Observed agreement
    po = np.trace(matrix) / n_total

    # Expected agreement (chance-corrected)
    # AC1 uses different formula than kappa
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)

    # Probability of agreement by chance (AC1 formula)
    pe = (1 / (n_categories * (n_categories - 1))) * np.sum(
        row_sums * col_sums - np.diag(np.outer(row_sums, col_sums))
    ) / (n_total ** 2)

    # AC1
    if pe == 1:
        ac1 = 1.0
    else:
        ac1 = (po - pe) / (1 - pe)

    return {
        "ac1": ac1,
        "observed_agreement": po,
        "expected_agreement": pe,
        "agreement_matrix": matrix.tolist(),
        "categories": categories
    }


def compare_llm_vs_human(llm_ratings: List[str], human_ratings: List[str],
                         metric: str = "both") -> Dict:
    """
    Compare LLM ratings vs human ratings
    Returns reliability metrics
    """
    if metric in ["kappa", "both"]:
        kappa_result = cohens_kappa(llm_ratings, human_ratings)
    else:
        kappa_result = None

    if metric in ["ac1", "both"]:
        ac1_result = gwets_ac1(llm_ratings, human_ratings)
    else:
        ac1_result = None

    result = {}
    if kappa_result:
        result["cohens_kappa"] = kappa_result
    if ac1_result:
        result["gwets_ac1"] = ac1_result

    # Add recommendation
    if kappa_result:
        kappa_val = kappa_result["kappa"]
        if kappa_val < 0.4:
            result["recommendation"] = "Low agreement - refine rules/prompts"
        elif kappa_val < 0.6:
            result["recommendation"] = "Moderate agreement - acceptable but could improve"
        else:
            result["recommendation"] = "Good agreement - acceptable for use"

    return result
