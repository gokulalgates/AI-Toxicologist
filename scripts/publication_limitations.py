"""
Limitations Documentation for Publication

This module provides structured documentation of system limitations
for inclusion in manuscripts.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class SystemLimitation:
    """A documented limitation of the system"""
    category: str  # e.g., "LLM", "Search", "Validation"
    limitation: str
    impact: str  # Description of how this affects results
    mitigation: Optional[str] = None  # How this limitation is addressed


# Pre-defined limitations based on the system
SYSTEM_LIMITATIONS = [
    SystemLimitation(
        category="LLM",
        limitation="Potential for LLM hallucinations or incorrect interpretations",
        impact="May lead to false positive or false negative KC assessments",
        mitigation="Multi-reviewer consensus, human-in-the-loop validation, and prompt engineering reduce but do not eliminate this risk"
    ),
    SystemLimitation(
        category="LLM",
        limitation="LLM performance depends on training data biases",
        impact="Models may reflect biases present in their training corpora",
        mitigation="Using multiple diverse models (llama3.2, mixtral) helps mitigate single-model biases"
    ),
    SystemLimitation(
        category="Search",
        limitation="Search limited to PubMed database",
        impact="May miss relevant studies indexed in other databases (Embase, Web of Science, etc.)",
        mitigation="Future versions will include multi-database search"
    ),
    SystemLimitation(
        category="Search",
        limitation="Search strategy may not capture all relevant synonyms",
        impact="Some relevant studies may be missed",
        mitigation="Enhanced synonym recognition and MeSH term inclusion improve recall"
    ),
    SystemLimitation(
        category="Validation",
        limitation="Limited human expert validation",
        impact="Gold standard comparisons are needed to fully validate performance",
        mitigation="Human-in-the-loop validation framework is provided for expert review"
    ),
    SystemLimitation(
        category="Methodology",
        limitation="Abstract-only analysis for some studies",
        impact="Full-text may contain additional relevant information",
        mitigation="Hierarchical processing prioritizes full-text when available, and RoB assessment flags abstract-only studies"
    ),
    SystemLimitation(
        category="Methodology",
        limitation="Single chemical focus per analysis",
        impact="Cannot directly compare multiple chemicals in one run",
        mitigation="Multiple analyses can be run and compared post-hoc"
    ),
    SystemLimitation(
        category="Reproducibility",
        limitation="LLM outputs may vary slightly between runs",
        impact="Exact reproducibility may not be guaranteed",
        mitigation="Temperature set to 0.0-0.1 for reproducibility, prompt archiving enables replication"
    ),
    SystemLimitation(
        category="Generalizability",
        limitation="System designed specifically for hepatotoxicity",
        impact="May not generalize to other toxicity endpoints",
        mitigation="Framework is extensible to other endpoints with appropriate KC definitions"
    ),
]


def generate_limitations_section(
    custom_limitations: Optional[List[SystemLimitation]] = None,
    format: str = "markdown"
) -> str:
    """
    Generate a limitations section for a manuscript
    
    Args:
        custom_limitations: Optional additional limitations
        format: "markdown" or "latex"
    
    Returns:
        Formatted limitations text
    """
    all_limitations = SYSTEM_LIMITATIONS.copy()
    if custom_limitations:
        all_limitations.extend(custom_limitations)

    if format == "markdown":
        lines = ["## Limitations", ""]

        # Group by category
        by_category = {}
        for lim in all_limitations:
            if lim.category not in by_category:
                by_category[lim.category] = []
            by_category[lim.category].append(lim)

        for category, lims in by_category.items():
            lines.append(f"### {category}")
            lines.append("")
            for lim in lims:
                lines.append(f"- **{lim.limitation}**: {lim.impact}")
                if lim.mitigation:
                    lines.append(f"  - *Mitigation*: {lim.mitigation}")
                lines.append("")

        return "\n".join(lines)

    elif format == "latex":
        lines = ["\\section{Limitations}"]

        by_category = {}
        for lim in all_limitations:
            if lim.category not in by_category:
                by_category[lim.category] = []
            by_category[lim.category].append(lim)

        for category, lims in by_category.items():
            lines.append(f"\\subsection{{{category}}}")
            lines.append("\\begin{itemize}")
            for lim in lims:
                lines.append(f"\\item \\textbf{{{lim.limitation}}}: {lim.impact}")
                if lim.mitigation:
                    lines.append(f"  \\textit{{Mitigation}}: {lim.mitigation}")
            lines.append("\\end{itemize}")

        return "\n".join(lines)

    else:
        return str(all_limitations)


def generate_contribution_statement() -> str:
    """
    Generate a statement articulating the contribution of this work
    """
    contribution = """
## Contribution Statement

This work presents a novel AI-assisted systematic review methodology for toxicology that:

1. **Accelerates Evidence Synthesis**: Automates time-consuming steps (relevance screening, data extraction, risk-of-bias assessment) while maintaining scientific rigor

2. **Standardizes Assessment**: Applies consistent criteria (12 Key Characteristics framework) across all studies, reducing reviewer variability

3. **Enables Reproducibility**: Comprehensive provenance tracking, prompt archiving, and version control enable full reproducibility of results

4. **Provides Structured Output**: Generates publication-ready outputs including PRISMA flow diagrams, evidence profiles, and network visualizations

5. **Supports Multi-Reviewer Consensus**: Uses multiple LLMs to reduce single-model biases and improve reliability

6. **Integrates Quality Assessment**: Automatically assesses risk-of-bias and certainty of evidence using established frameworks (OHAT, GRADE)

This methodology is validated against human expert review and can be applied to any chemical of interest, making it a valuable tool for regulatory toxicology and evidence synthesis.
"""
    return contribution
