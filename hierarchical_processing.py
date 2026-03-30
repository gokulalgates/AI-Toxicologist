"""
Hierarchical Processing Module
Prioritizes key sections (methods, results, conclusions) over other text
"""

import re
from typing import Dict, Optional, Tuple


def extract_sections(fulltext: str) -> Dict[str, str]:
    """
    Extract key sections from full-text
    
    Args:
        fulltext: Full text of the paper
    
    Returns:
        Dict with sections: abstract, methods, results, conclusions
    """
    sections = {
        "abstract": "",
        "methods": "",
        "results": "",
        "conclusions": "",
        "other": ""
    }

    text_lower = fulltext.lower()

    # Extract abstract (usually first section)
    abstract_match = re.search(r'(?:abstract|summary)\s*:?\s*(.+?)(?=\n\s*(?:introduction|background|methods|keywords)|$)',
                               fulltext, re.IGNORECASE | re.DOTALL)
    if abstract_match:
        sections["abstract"] = abstract_match.group(1).strip()

    # Extract methods section
    methods_patterns = [
        r'(?:methods?|methodology|materials\s+and\s+methods?)\s*:?\s*(.+?)(?=\n\s*(?:results?|discussion|conclusion|references?)|$)',
        r'(?:experimental\s+procedures?|study\s+design)\s*:?\s*(.+?)(?=\n\s*(?:results?|discussion|conclusion)|$)',
    ]
    for pattern in methods_patterns:
        match = re.search(pattern, fulltext, re.IGNORECASE | re.DOTALL)
        if match:
            sections["methods"] = match.group(1).strip()
            break

    # Extract results section
    results_patterns = [
        r'(?:results?|findings?)\s*:?\s*(.+?)(?=\n\s*(?:discussion|conclusion|references?)|$)',
        r'(?:data|outcomes?)\s*:?\s*(.+?)(?=\n\s*(?:discussion|conclusion)|$)',
    ]
    for pattern in results_patterns:
        match = re.search(pattern, fulltext, re.IGNORECASE | re.DOTALL)
        if match:
            sections["results"] = match.group(1).strip()
            break

    # Extract conclusions section
    conclusions_patterns = [
        r'(?:conclusions?|concluding\s+remarks?)\s*:?\s*(.+?)(?=\n\s*(?:references?|acknowledgments?|$)|$)',
        r'(?:discussion\s+and\s+conclusions?)\s*:?\s*(.+?)(?=\n\s*(?:references?|$)|$)',
        r'(?:summary\s+and\s+conclusions?)\s*:?\s*(.+?)(?=\n\s*(?:references?|$)|$)',
    ]
    for pattern in conclusions_patterns:
        match = re.search(pattern, fulltext, re.IGNORECASE | re.DOTALL)
        if match:
            sections["conclusions"] = match.group(1).strip()
            break

    return sections


def prioritize_text_for_analysis(
    abstract: str,
    fulltext: Optional[str] = None,
    max_length: int = 10000
) -> Tuple[str, Dict[str, float]]:
    """
    Prioritize and combine text sections for analysis
    
    Priority order:
    1. Results section (highest priority)
    2. Conclusions section
    3. Abstract
    4. Methods section
    5. Other text
    
    Args:
        abstract: Abstract text
        fulltext: Optional full-text
        max_length: Maximum length of combined text
    
    Returns:
        Tuple of (prioritized_text, section_weights)
    """
    section_weights = {
        "results": 1.0,
        "conclusions": 0.9,
        "abstract": 0.8,
        "methods": 0.6,
        "other": 0.3
    }

    prioritized_parts = []

    if fulltext and len(fulltext) > len(abstract):
        # Extract sections from full-text
        sections = extract_sections(fulltext)

        # Add sections in priority order
        for section_name in ["results", "conclusions", "methods"]:
            section_text = sections.get(section_name, "")
            if section_text:
                # Truncate if needed, but prioritize keeping this section
                max_section_length = int(max_length * section_weights[section_name])
                if len(section_text) > max_section_length:
                    section_text = section_text[:max_section_length] + "..."
                prioritized_parts.append((section_text, section_weights[section_name]))

        # Add abstract if not already included
        if abstract and abstract not in sections.get("abstract", ""):
            max_abstract_length = int(max_length * section_weights["abstract"])
            abstract_text = abstract[:max_abstract_length] if len(abstract) > max_abstract_length else abstract
            prioritized_parts.append((abstract_text, section_weights["abstract"]))
    else:
        # Just use abstract
        prioritized_parts.append((abstract, section_weights["abstract"]))

    # Combine parts, respecting max_length
    combined_text = ""
    current_length = 0

    # Sort by weight (descending)
    prioritized_parts.sort(key=lambda x: x[1], reverse=True)

    for text, weight in prioritized_parts:
        remaining_length = max_length - current_length
        if remaining_length <= 0:
            break

        if len(text) <= remaining_length:
            combined_text += text + "\n\n"
            current_length += len(text) + 2
        else:
            # Truncate this section
            combined_text += text[:remaining_length] + "...\n\n"
            break

    return combined_text.strip(), section_weights


def build_hierarchical_prompt(
    abstract: str,
    fulltext: Optional[str] = None,
    emphasize_sections: bool = True
) -> str:
    """
    Build prompt with hierarchical emphasis on key sections
    
    Args:
        abstract: Abstract text
        fulltext: Optional full-text
        emphasize_sections: Whether to add section emphasis in prompt
    
    Returns:
        Formatted text with section emphasis
    """
    prioritized_text, section_weights = prioritize_text_for_analysis(abstract, fulltext)

    if not emphasize_sections or not fulltext:
        return prioritized_text

    # Add section labels for clarity
    sections = extract_sections(fulltext)
    formatted_parts = []

    if sections.get("results"):
        formatted_parts.append(f"### RESULTS SECTION (High Priority):\n{sections['results'][:2000]}")

    if sections.get("conclusions"):
        formatted_parts.append(f"### CONCLUSIONS SECTION (High Priority):\n{sections['conclusions'][:1500]}")

    if abstract:
        formatted_parts.append(f"### ABSTRACT:\n{abstract}")

    if sections.get("methods"):
        formatted_parts.append(f"### METHODS SECTION:\n{sections['methods'][:1000]}")

    return "\n\n".join(formatted_parts)
