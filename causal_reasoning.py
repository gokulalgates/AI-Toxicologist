"""
Enhanced Causal Reasoning Module
Specialized prompts and validation for causal link extraction
"""

from typing import List, Dict, Optional
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json
import re
from config import get_config


CAUSAL_REASONING_PROMPT = """### CAUSAL REASONING FRAMEWORK

When identifying causal links between Key Characteristics, you must verify:

1. **Temporal Relationship**: Does the cause precede the effect in the text or logically?
   - Example: "Metabolism (KC1) led to oxidative stress (KC5)" - clear temporal order
   - NOT: "Both metabolism and oxidative stress were observed" - no temporal order

2. **Mechanistic Explanation**: Is there a biological mechanism described?
   - Example: "Reactive metabolites deplete glutathione, causing oxidative stress"
   - NOT: "Metabolism and oxidative stress were both present" - no mechanism

3. **Strength of Evidence**: How explicit is the causal relationship?
   - STRONG: Directly stated ("causes", "leads to", "triggers", "results in")
   - MODERATE: Implied but clear ("associated with", "accompanied by", "followed by")
   - WEAK: Tenuous connection (co-occurrence without clear mechanism)

4. **Alternative Explanations**: Are alternative causes considered?
   - Higher confidence if study rules out alternatives
   - Lower confidence if multiple possible causes exist

### CRITICAL RULES
- Only mark as causal if ALL criteria (temporal + mechanistic) are met
- Do NOT infer causality from mere co-occurrence
- Prefer explicit statements over implicit connections
- When uncertain, mark strength as WEAK or omit the link

### EXAMPLES

**STRONG Causal Link:**
Text: "CYP2E1-mediated metabolism of acetaminophen generates NAPQI, which depletes glutathione and triggers oxidative stress."
Analysis:
- KC1 -> KC5: STRONG
- Evidence: "generates NAPQI, which depletes glutathione and triggers oxidative stress"
- Temporal: Metabolism happens first, then oxidative stress
- Mechanism: Reactive metabolite depletes antioxidants

**MODERATE Causal Link:**
Text: "Following bioactivation, we observed increased ROS levels and mitochondrial dysfunction."
Analysis:
- KC1 -> KC7: MODERATE
- Evidence: "Following bioactivation, we observed... mitochondrial dysfunction"
- Temporal: "Following" indicates sequence
- Mechanism: Implied but not explicitly stated

**NOT a Causal Link:**
Text: "The study found evidence of both bioactivation and oxidative stress."
Analysis:
- No causal link (mere co-occurrence, no temporal or mechanistic connection)
"""


def validate_causal_link(
    link: Dict,
    abstract_text: str
) -> Dict:
    """
    Validate a causal link against the abstract text
    
    Args:
        link: Causal link dict with source, target, evidence, strength
        abstract_text: Full abstract text
    
    Returns:
        Validated link with updated strength and validation flags
    """
    source = link.get("source", "")
    target = link.get("target", "")
    evidence = link.get("evidence", "")
    strength = link.get("strength", "MODERATE")
    
    validated_link = link.copy()
    
    # Check temporal indicators
    temporal_keywords = [
        "led to", "causes", "triggers", "results in", "induces",
        "following", "after", "subsequently", "then", "consequently"
    ]
    has_temporal = any(kw in evidence.lower() for kw in temporal_keywords)
    
    # Check mechanistic keywords
    mechanistic_keywords = [
        "via", "through", "by", "mechanism", "pathway", "mediates",
        "depletes", "inhibits", "activates", "generates"
    ]
    has_mechanistic = any(kw in evidence.lower() for kw in mechanistic_keywords)
    
    # Check if both source and target are mentioned in evidence
    source_mentioned = source.lower() in evidence.lower() or any(
        kw in evidence.lower() for kw in ["metabolism", "bioactivation", "reactive"]
        if source == "KC1"
    )
    target_mentioned = target.lower() in evidence.lower() or any(
        kw in evidence.lower() for kw in ["oxidative", "stress", "mitochondrial"]
        if target in ["KC5", "KC7"]
    )
    
    # Adjust strength based on validation
    if has_temporal and has_mechanistic and source_mentioned and target_mentioned:
        if strength == "WEAK":
            validated_link["strength"] = "MODERATE"  # Upgrade if criteria met
        validated_link["validated"] = True
    elif has_temporal or has_mechanistic:
        if strength == "STRONG":
            validated_link["strength"] = "MODERATE"  # Downgrade if missing criteria
        validated_link["validated"] = True
    else:
        validated_link["validated"] = False
        validated_link["strength"] = "WEAK"
    
    validated_link["validation_flags"] = {
        "has_temporal": has_temporal,
        "has_mechanistic": has_mechanistic,
        "source_mentioned": source_mentioned,
        "target_mentioned": target_mentioned
    }
    
    return validated_link


def enhance_causal_reasoning_prompt(base_prompt: str) -> str:
    """
    Enhance base prompt with causal reasoning framework
    
    Args:
        base_prompt: Base system prompt
    
    Returns:
        Enhanced prompt with causal reasoning instructions
    """
    # Insert causal reasoning framework before examples
    if "### FEW-SHOT EXAMPLES" in base_prompt:
        enhanced = base_prompt.replace(
            "### FEW-SHOT EXAMPLES",
            CAUSAL_REASONING_PROMPT + "\n\n### FEW-SHOT EXAMPLES"
        )
    else:
        enhanced = base_prompt + "\n\n" + CAUSAL_REASONING_PROMPT
    
    return enhanced


def validate_all_causal_links(
    analysis: Dict,
    abstract_text: str
) -> Dict:
    """
    Validate all causal links in an analysis
    
    Args:
        analysis: Analysis dict with causal_links
        abstract_text: Full abstract text
    
    Returns:
        Analysis dict with validated causal links
    """
    validated_analysis = analysis.copy()
    causal_links = analysis.get("causal_links", [])
    
    validated_links = []
    for link in causal_links:
        validated_link = validate_causal_link(link, abstract_text)
        validated_links.append(validated_link)
    
    validated_analysis["causal_links"] = validated_links
    
    # Add summary statistics
    validated_analysis["causal_link_stats"] = {
        "total": len(validated_links),
        "validated": sum(1 for l in validated_links if l.get("validated", False)),
        "strong": sum(1 for l in validated_links if l.get("strength") == "STRONG"),
        "moderate": sum(1 for l in validated_links if l.get("strength") == "MODERATE"),
        "weak": sum(1 for l in validated_links if l.get("strength") == "WEAK")
    }
    
    return validated_analysis
