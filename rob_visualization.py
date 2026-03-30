"""
Risk-of-Bias visualization functions
Creates heatmaps and summary visualizations
"""

from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

from evidence_models import RiskOfBiasAssessment


def create_rob_heatmap_figure(
    rob_assessments: List[RiskOfBiasAssessment],
    kcs: List[str],
    kc_analyses: List[Dict]
) -> plt.Figure:
    """
    Create a heatmap showing risk-of-bias across KCs and domains
    """
    # Map judgments to numeric values
    judgment_map = {"Low": 0, "Some concerns": 1, "High": 2, "Critical": 3, "N/A": -1}

    # Get all unique domains
    all_domains = set()
    for assessment in rob_assessments:
        for domain in assessment.domains:
            all_domains.add(domain.domain)
    all_domains = sorted(list(all_domains))

    # Build matrix: KCs (rows) x Domains (cols)
    matrix = []
    row_labels = []

    for kc in kcs:
        # Only include KCs that are supported in at least one study
        kc_supported = any(
            analysis.get(f"{kc.lower()}_status", "NOT_MENTIONED") == "SUPPORTED"
            for analysis in kc_analyses
        )

        if not kc_supported:
            continue

        row = []
        for domain_name in all_domains:
            # Get judgments for this KC-domain pair
            judgments = []
            for i, assessment in enumerate(rob_assessments):
                # Check if this study supports the KC
                if kc_analyses[i].get(f"{kc.lower()}_status", "NOT_MENTIONED") == "SUPPORTED":
                    for domain in assessment.domains:
                        if domain.domain == domain_name:
                            judgments.append(judgment_map.get(domain.judgment, 1))

            if judgments:
                # Use most common judgment (or average if tied)
                avg_judgment = np.mean(judgments)
                row.append(avg_judgment)
            else:
                row.append(-1)  # N/A

        matrix.append(row)
        row_labels.append(kc)

    if not matrix:
        # Create empty figure with message
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No risk-of-bias data available",
                ha='center', va='center', fontsize=14)
        ax.axis('off')
        return fig

    # Create heatmap
    fig, ax = plt.subplots(figsize=(max(12, len(all_domains) * 1.5), max(8, len(row_labels) * 0.8)))

    # Create custom colormap
    from matplotlib.colors import ListedColormap
    colors = ['#2ecc71', '#f39c12', '#e74c3c', '#8e44ad', '#ecf0f1']  # Green, Orange, Red, Purple, Gray
    cmap = ListedColormap(colors)

    sns.heatmap(
        matrix,
        annot=True,
        fmt='.1f',
        cmap=cmap,
        xticklabels=all_domains,
        yticklabels=row_labels,
        cbar_kws={'label': 'Risk: 0=Low, 1=Some concerns, 2=High, 3=Critical'},
        linewidths=0.5,
        linecolor='gray',
        ax=ax,
        vmin=-1,
        vmax=3
    )

    ax.set_title("Risk-of-Bias Assessment Heatmap\n(by Key Characteristic and Domain)",
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel("Risk-of-Bias Domains", fontsize=12, fontweight='bold')
    ax.set_ylabel("Key Characteristics", fontsize=12, fontweight='bold')

    plt.xticks(rotation=45, ha='right')
    plt.yticks(rotation=0)
    plt.tight_layout()

    return fig


def create_rob_summary_figure(rob_assessments: List[RiskOfBiasAssessment]) -> plt.Figure:
    """
    Create a summary bar chart of overall risk-of-bias judgments
    """
    judgment_counts = {"Low": 0, "Some concerns": 0, "High": 0, "Critical": 0}

    for assessment in rob_assessments:
        judgment = assessment.overall_judgment
        judgment_counts[judgment] = judgment_counts.get(judgment, 0) + 1

    fig, ax = plt.subplots(figsize=(10, 6))

    judgments = list(judgment_counts.keys())
    counts = [judgment_counts[j] for j in judgments]
    colors = ['#2ecc71', '#f39c12', '#e74c3c', '#8e44ad']

    bars = ax.bar(judgments, counts, color=colors[:len(judgments)], alpha=0.8, edgecolor='black')

    # Add count labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(count)}',
                ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax.set_ylabel('Number of Studies', fontsize=12, fontweight='bold')
    ax.set_xlabel('Overall Risk-of-Bias Judgment', fontsize=12, fontweight='bold')
    ax.set_title('Risk-of-Bias Summary\n(Distribution of Overall Judgments)',
                 fontsize=14, fontweight='bold', pad=20)
    ax.set_ylim(0, max(counts) * 1.2 if counts else 1)

    plt.tight_layout()
    return fig
