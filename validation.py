"""
Validation and Benchmarking Infrastructure for Systematic Review Research

This module provides:
- Gold standard comparison framework
- Performance metrics (precision, recall, F1)
- Ablation study support
- Human-in-the-loop validation tools
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class GoldStandardRecord:
    """A single gold standard record from human expert review"""
    pmid: str
    chemical_name: str
    # Relevance screening
    is_relevant: bool
    # KC assessments (human expert judgment)
    kc_assessments: Dict[str, str]  # KC -> "SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED", "REFUTED", "NOT_MENTIONED"
    # Risk of Bias
    rob_overall: str  # "Low", "Some concerns", "High", "Critical"
    rob_domains: Dict[str, str]  # Domain -> Judgment
    # Certainty assessments
    certainty_assessments: Dict[str, str]  # KC -> "High", "Moderate", "Low", "Very Low"
    # Metadata
    reviewer_id: str
    review_date: str
    notes: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for a specific task"""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int


def calculate_relevance_metrics(
    gold_standard: List[GoldStandardRecord],
    ai_predictions: Dict[str, bool]  # pmid -> is_relevant
) -> PerformanceMetrics:
    """
    Calculate precision, recall, F1 for relevance screening
    
    Args:
        gold_standard: List of gold standard records
        ai_predictions: Dict mapping PMID to AI's relevance prediction
    
    Returns:
        PerformanceMetrics object
    """
    tp = fp = fn = tn = 0

    for record in gold_standard:
        gold_relevant = record.is_relevant
        ai_relevant = ai_predictions.get(record.pmid, False)

        if gold_relevant and ai_relevant:
            tp += 1
        elif gold_relevant and not ai_relevant:
            fn += 1
        elif not gold_relevant and ai_relevant:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0

    return PerformanceMetrics(
        precision=precision,
        recall=recall,
        f1_score=f1,
        accuracy=accuracy,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn
    )


def calculate_kc_extraction_metrics(
    gold_standard: List[GoldStandardRecord],
    ai_predictions: Dict[str, Dict[str, str]],  # pmid -> {KC -> status}
    kc: str
) -> PerformanceMetrics:
    """
    Calculate metrics for KC extraction for a specific KC
    
    Treats SUPPORTED/ASSOCIATED/CAUSALLY_LINKED as positive, others as negative
    """
    tp = fp = fn = tn = 0

    positive_statuses = {"SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"}

    for record in gold_standard:
        gold_status = record.kc_assessments.get(kc, "NOT_MENTIONED")
        ai_status = ai_predictions.get(record.pmid, {}).get(kc, "NOT_MENTIONED")

        gold_positive = gold_status in positive_statuses
        ai_positive = ai_status in positive_statuses

        if gold_positive and ai_positive:
            tp += 1
        elif gold_positive and not ai_positive:
            fn += 1
        elif not gold_positive and ai_positive:
            fp += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0

    return PerformanceMetrics(
        precision=precision,
        recall=recall,
        f1_score=f1,
        accuracy=accuracy,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        true_negatives=tn
    )


def calculate_certainty_metrics(
    gold_standard: List[GoldStandardRecord],
    ai_predictions: Dict[str, Dict[str, str]],  # pmid -> {KC -> certainty}
    kc: str
) -> Dict[str, float]:
    """
    Calculate agreement metrics for certainty assessment
    
    Returns dict with:
    - exact_agreement: Percentage of exact matches
    - weighted_agreement: Weighted by certainty level hierarchy
    - kappa: Cohen's kappa (if applicable)
    """
    certainty_levels = {"Very Low": 0, "Low": 1, "Moderate": 2, "High": 3}

    exact_matches = 0
    total = 0
    weighted_diffs = []

    for record in gold_standard:
        gold_certainty = record.certainty_assessments.get(kc)
        ai_certainty = ai_predictions.get(record.pmid, {}).get(kc)

        if gold_certainty and ai_certainty:
            total += 1
            if gold_certainty == ai_certainty:
                exact_matches += 1

            gold_level = certainty_levels.get(gold_certainty, 0)
            ai_level = certainty_levels.get(ai_certainty, 0)
            weighted_diffs.append(abs(gold_level - ai_level))

    exact_agreement = exact_matches / total if total > 0 else 0.0
    avg_weighted_diff = sum(weighted_diffs) / len(weighted_diffs) if weighted_diffs else 0.0

    return {
        "exact_agreement": exact_agreement,
        "average_weighted_difference": avg_weighted_diff,
        "total_comparisons": total
    }


def compare_ai_vs_gold_standard(
    gold_standard_file: str,
    ai_results_file: str,
    output_file: Optional[str] = None
) -> Dict[str, Any]:
    """
    Comprehensive comparison of AI results vs gold standard
    
    Args:
        gold_standard_file: Path to JSON file with gold standard records
        ai_results_file: Path to JSON file with AI results
        output_file: Optional path to save comparison report
    
    Returns:
        Dict with all comparison metrics
    """
    # Load data
    with open(gold_standard_file) as f:
        gold_data = json.load(f)

    with open(ai_results_file) as f:
        ai_data = json.load(f)

    # Convert to GoldStandardRecord objects
    gold_records = [GoldStandardRecord(**record) for record in gold_data]

    # Extract AI predictions
    ai_relevance = {record["pmid"]: record.get("is_relevant", False)
                    for record in ai_data if "pmid" in record}

    ai_kc_predictions = {}
    for record in ai_data:
        if "pmid" in record:
            pmid = record["pmid"]
            ai_kc_predictions[pmid] = {}
            for kc in ["KC1", "KC2", "KC3", "KC4", "KC5", "KC6",
                      "KC7", "KC8", "KC9", "KC10", "KC11", "KC12"]:
                kc_key = kc.lower().replace("kc", "kc") + "_status"
                ai_kc_predictions[pmid][kc] = record.get(kc_key, "NOT_MENTIONED")

    # Calculate metrics
    comparison = {
        "relevance_screening": {},
        "kc_extraction": {},
        "certainty_assessment": {}
    }

    # Relevance metrics
    relevance_metrics = calculate_relevance_metrics(gold_records, ai_relevance)
    comparison["relevance_screening"] = {
        "precision": relevance_metrics.precision,
        "recall": relevance_metrics.recall,
        "f1_score": relevance_metrics.f1_score,
        "accuracy": relevance_metrics.accuracy,
        "confusion_matrix": {
            "true_positives": relevance_metrics.true_positives,
            "false_positives": relevance_metrics.false_positives,
            "false_negatives": relevance_metrics.false_negatives,
            "true_negatives": relevance_metrics.true_negatives
        }
    }

    # KC extraction metrics for each KC
    for kc in ["KC1", "KC2", "KC3", "KC4", "KC5", "KC6",
               "KC7", "KC8", "KC9", "KC10", "KC11", "KC12"]:
        kc_metrics = calculate_kc_extraction_metrics(gold_records, ai_kc_predictions, kc)
        comparison["kc_extraction"][kc] = {
            "precision": kc_metrics.precision,
            "recall": kc_metrics.recall,
            "f1_score": kc_metrics.f1_score,
            "accuracy": kc_metrics.accuracy,
            "confusion_matrix": {
                "true_positives": kc_metrics.true_positives,
                "false_positives": kc_metrics.false_positives,
                "false_negatives": kc_metrics.false_negatives,
                "true_negatives": kc_metrics.true_negatives
            }
        }

    # Certainty metrics
    ai_certainty_predictions = {}
    for record in ai_data:
        if "pmid" in record and "certainty_assessments" in record:
            ai_certainty_predictions[record["pmid"]] = record["certainty_assessments"]

    for kc in ["KC1", "KC2", "KC3", "KC4", "KC5", "KC6",
               "KC7", "KC8", "KC9", "KC10", "KC11", "KC12"]:
        certainty_metrics = calculate_certainty_metrics(gold_records, ai_certainty_predictions, kc)
        comparison["certainty_assessment"][kc] = certainty_metrics

    # Save if requested
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(comparison, f, indent=2)

    return comparison


def create_ablation_study_config(
    base_config: Dict[str, Any],
    ablation_variants: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create configurations for ablation studies
    
    Args:
        base_config: Base configuration
        ablation_variants: List of dicts specifying what to disable/modify
    
    Returns:
        List of configurations for each ablation variant
    """
    configs = []

    for variant in ablation_variants:
        config = base_config.copy()
        config.update(variant)
        config["ablation_name"] = variant.get("name", "unknown")
        configs.append(config)

    return configs


def generate_ablation_report(
    ablation_results: List[Dict[str, Any]],
    output_file: Optional[str] = None
) -> str:
    """
    Generate a report comparing ablation study results
    
    Args:
        ablation_results: List of result dicts, each with 'config' and 'metrics'
        output_file: Optional path to save report
    
    Returns:
        Report text
    """
    report_lines = [
        "# Ablation Study Report",
        "",
        "## Configuration Variants",
        ""
    ]

    for i, result in enumerate(ablation_results):
        config = result.get("config", {})
        report_lines.append(f"### Variant {i+1}: {config.get('ablation_name', 'Unknown')}")
        report_lines.append(f"- Configuration: {json.dumps(config, indent=2)}")
        report_lines.append("")

    report_lines.extend([
        "## Performance Comparison",
        ""
    ])

    # Compare metrics
    if ablation_results:
        metrics_to_compare = ["precision", "recall", "f1_score", "accuracy"]
        for metric in metrics_to_compare:
            report_lines.append(f"### {metric.replace('_', ' ').title()}")
            for result in ablation_results:
                config_name = result.get("config", {}).get("ablation_name", "Unknown")
                metrics = result.get("metrics", {})
                value = metrics.get(metric, "N/A")
                report_lines.append(f"- {config_name}: {value}")
            report_lines.append("")

    report_text = "\n".join(report_lines)

    if output_file:
        with open(output_file, 'w') as f:
            f.write(report_text)

    return report_text
