"""
Script to create a PowerPoint presentation for the AI Toxicologist application
Fixed version with proper bullet point formatting
"""

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt


def add_bullet_points(text_frame, items):
    """Helper function to add bullet points to a text frame"""
    text_frame.clear()
    p = text_frame.paragraphs[0]
    p.text = items[0]
    p.level = 0
    p.font.size = Pt(18)
    p.font.color.rgb = RGBColor(51, 51, 51)

    for item in items[1:]:
        p = text_frame.add_paragraph()
        p.text = item
        p.level = 0
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(51, 51, 51)

def create_presentation():
    """Create a comprehensive PowerPoint presentation"""

    # Create presentation object
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Define colors
    title_color = RGBColor(0, 51, 102)  # Dark blue
    accent_color = RGBColor(0, 102, 204)  # Blue
    text_color = RGBColor(51, 51, 51)  # Dark gray

    # Slide 1: Title Slide
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    title = slide.shapes.title
    subtitle = slide.placeholders[1]

    title.text = "AI Toxicologist"
    title.text_frame.paragraphs[0].font.size = Pt(54)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    subtitle.text = "Systematic Literature Review\nfor Hepatotoxicity Assessment\n\nBased on Key Characteristics of Human Hepatotoxicants\n(Rusyn et al., 2021)"
    subtitle.text_frame.paragraphs[0].font.size = Pt(20)
    subtitle.text_frame.paragraphs[0].font.color.rgb = text_color

    # Slide 2: Problem Statement
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "The Challenge"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Systematic literature reviews for chemical safety assessment are:",
        "Time-consuming (weeks to months)",
        "Labor-intensive (requires expert toxicologists)",
        "Expensive (high personnel costs)",
        "Prone to human error and bias",
        "",
        "Need for standardized, reproducible assessment methods",
        "",
        "Key Characteristics framework provides structured approach but requires extensive manual review"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 3: Solution Overview
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Our Solution"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "AI Toxicologist: Automated Systematic Review System",
        "",
        "PRISMA 2020-compliant systematic literature review",
        "AI-powered analysis using open-source LLMs (Ollama)",
        "Reproducible outputs with full provenance tracking",
        "Multi-reviewer consensus mode for enhanced reliability",
        "Risk-of-Bias and Certainty Grading (GRADE/OHAT)",
        "",
        "Key Innovation:",
        "Automated extraction and synthesis of mechanistic evidence from scientific literature using Key Characteristics framework"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 4: Key Features
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Key Features"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "PRISMA 2020 Compliance",
        "  Flow diagrams and standardized reporting",
        "",
        "Enhanced Search Capabilities",
        "  MeSH-aware PubMed queries",
        "  CAS/CID support",
        "  Chemical name standardization via PubChem",
        "",
        "Evidence Extraction",
        "  Sentence-level evidence quotes",
        "  Causal pathway identification",
        "  Mechanistic relationship mapping",
        "",
        "Quality Assessment",
        "  Risk-of-Bias (OHAT/ROBINS-I)",
        "  Certainty Grading (GRADE/OHAT)",
        "  Evidence profile cards",
        "",
        "Multi-Reviewer Mode",
        "  Consensus analysis across multiple models",
        "  Inter-model agreement statistics (Cohen's kappa)",
        "  Paper ranking by consensus strength"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 5: The 12 Key Characteristics
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "The 12 Key Characteristics"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "KC1: Reactive/Bioactivation",
        "KC2: Cell Death (apoptosis/necrosis)",
        "KC3: Proliferation/Regeneration",
        "KC4: Transport Disruption",
        "KC5: Oxidative Stress",
        "KC6: Immune Response",
        "KC7: Mitochondrial Dysfunction",
        "KC8: Stress Signaling",
        "KC9: Cholestasis",
        "KC10: Cytoskeleton Disruption",
        "KC11: Liver Fibrosis",
        "KC12: Metabolism Disruption",
        "",
        "Each KC represents a distinct biological mechanism indicative of hepatotoxicity potential"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 6: Workflow - Step 1
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Workflow: Step 1 - The Librarian"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Chemical Standardization",
        "  Resolve chemical name via PubChem",
        "  Get standardized IUPAC name",
        "  Retrieve PubChem CID",
        "  Collect synonyms and common names",
        "",
        "Enhanced PubMed Search",
        "  MeSH-aware query construction",
        "  Multiple search terms (up to configurable limit)",
        "  CAS/CID support",
        "  Initial retrieval (up to 500 abstracts)",
        "",
        "Results",
        "  Standardized chemical name",
        "  Search log with query details",
        "  Retrieved abstracts with metadata"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 7: Workflow - Step 2
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Workflow: Step 2 - The Gatekeeper"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Relevance Filtering",
        "  AI-powered semantic filtering",
        "  Focus: Liver toxicity specifically",
        "  Excludes: Efficacy studies, other organ toxicity",
        "  Configurable analysis limit (default: 500)",
        "",
        "Full-Text Retrieval (Optional)",
        "  Attempts retrieval from multiple sources",
        "  Improves Risk-of-Bias assessment quality",
        "  Falls back to abstracts if unavailable",
        "  Tracks coverage percentage",
        "",
        "Results",
        "  Relevant abstracts for analysis",
        "  Full-text availability status",
        "  PRISMA-compliant exclusion tracking"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 8: Workflow - Step 3
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Workflow: Step 3 - The Analyst"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "AI-Powered KC Analysis",
        "  Analyze each abstract against 12 KCs",
        "  Extract evidence quotes (sentence-level)",
        "  Identify causal pathways between KCs",
        "  Chain-of-thought reasoning",
        "",
        "Multi-Reviewer Mode (Optional)",
        "  Multiple LLM models as independent reviewers",
        "  Consensus analysis (majority voting)",
        "  Inter-model agreement statistics",
        "  Paper ranking by consensus strength",
        "",
        "Outputs",
        "  KC status per paper (SUPPORTED/ASSOCIATED/CAUSALLY_LINKED/REFUTED/NOT_MENTIONED)",
        "  Evidence quotes for each KC",
        "  Causal links between KCs",
        "  Reasoning for each assessment"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 9: Workflow - Step 4
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Workflow: Step 4 - Quality Assessment"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Risk-of-Bias Assessment",
        "  LLM-based OHAT/ROBINS-I assessment",
        "  Multiple bias domains evaluated",
        "  Overall judgment per study",
        "  Visual heatmaps and summaries",
        "",
        "Certainty Grading",
        "  GRADE/OHAT-style certainty ratings",
        "  Per-Key Characteristic assessment",
        "  Considers: RoB, consistency, directness, precision",
        "  Evidence profile cards generated",
        "",
        "Results",
        "  Risk-of-Bias judgments",
        "  Certainty ratings (High/Moderate/Low/Very Low)",
        "  Evidence profile summaries"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 10: Workflow - Step 5
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Workflow: Step 5 - The Architect"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Visualizations Generated",
        "",
        "1. Evidence Matrix Heatmap",
        "   Papers by Key Characteristics",
        "   Color-coded: Supported/Refuted/Not Mentioned",
        "   Quick visual overview of evidence",
        "",
        "2. Causal Pathway Network (DAG)",
        "   Directed graph showing mechanistic relationships",
        "   Edge weights equal frequency of causal links",
        "   Color-coded by pathway role",
        "",
        "3. PRISMA 2020 Flow Diagram",
        "   Standardized reporting format",
        "   Shows screening and exclusion process",
        "   Publication-ready diagram",
        "",
        "4. Risk-of-Bias Visualizations",
        "   Heatmap by KC and domain",
        "   Summary statistics"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 11: Technical Architecture
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Technical Architecture"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Frontend: Gradio (Python web framework)",
        "  Interactive web interface",
        "  Real-time progress tracking",
        "  Multi-model selection",
        "",
        "Backend: Python-based pipeline",
        "  Chemical standardization: PubChemPy",
        "  Literature search: BioPython (Entrez)",
        "  AI analysis: LangChain + Ollama (open-source LLMs)",
        "  Data processing: pandas, numpy",
        "  Visualization: matplotlib, seaborn, networkx",
        "",
        "Infrastructure:",
        "  GPU acceleration support (CUDA)",
        "  Parallel processing (multi-threading)",
        "  MPI support for distributed computing",
        "  Configurable limits and settings",
        "",
        "Data Storage:",
        "  Provenance tracking (JSON)",
        "  Study records (JSONL)",
        "  Search logs",
        "  Saved visualizations (PNG)"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 12: Key Outputs
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Key Outputs"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Analysis Summary",
        "  Chemical information",
        "  PRISMA summary",
        "  KC evidence counts",
        "  Multi-reviewer agreement stats (if enabled)",
        "  Risk-of-Bias summary",
        "  Processing time",
        "",
        "Visualizations",
        "  Evidence Matrix Heatmap",
        "  Causal Pathway Network",
        "  PRISMA Flow Diagram",
        "  Risk-of-Bias Heatmaps",
        "",
        "Evidence Profiles",
        "  Per-KC certainty ratings",
        "  Evidence summaries",
        "  Study characteristics",
        "",
        "Saved Files",
        "  All outputs saved to results/{chemical_name}/",
        "  Provenance records",
        "  Study records (JSONL)",
        "  High-resolution plots (300 DPI)"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 13: Use Cases
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Use Cases"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Research Applications",
        "  Rapid literature review for new chemicals",
        "  Hypothesis generation for mechanistic studies",
        "  Evidence synthesis for meta-analyses",
        "  Comparative analysis across chemicals",
        "",
        "Regulatory and Industry",
        "  Chemical safety assessment",
        "  Risk evaluation support",
        "  Regulatory submission preparation",
        "  Due diligence for chemical products",
        "",
        "Educational",
        "  Teaching systematic review methods",
        "  Demonstrating Key Characteristics framework",
        "  Training in evidence synthesis",
        "",
        "Exploratory Analysis",
        "  Identifying knowledge gaps",
        "  Discovering mechanistic pathways",
        "  Finding high-quality evidence sources"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 14: Advantages
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Key Advantages"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Speed and Efficiency",
        "  Hours instead of weeks",
        "  Automated processing",
        "  Parallel analysis support",
        "",
        "Standardization",
        "  Consistent methodology",
        "  PRISMA-compliant",
        "  Reproducible results",
        "",
        "Comprehensive",
        "  Multiple quality metrics",
        "  Full provenance tracking",
        "  Publication-ready outputs",
        "",
        "Open Source",
        "  No proprietary dependencies",
        "  Local processing (privacy)",
        "  Customizable and extensible",
        "",
        "Multi-Reviewer",
        "  Consensus analysis",
        "  Agreement statistics",
        "  Enhanced reliability"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 15: Configuration
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Configuration and Requirements"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "System Requirements:",
        "  Python 3.8+",
        "  Ollama (for LLM models)",
        "  GPU optional but recommended",
        "",
        "Configuration Options:",
        "  MAX_ABSTRACTS_INITIAL: Initial PubMed fetch (default: 500)",
        "  MAX_ABSTRACTS_ANALYZE: Analysis limit (default: 500)",
        "  MAX_SEARCH_TERMS: Synonym limit (default: 10)",
        "  LLM_TEMPERATURE: Model temperature (default: 0.0)",
        "  Enable/disable GPU acceleration",
        "  Enable/disable parallel processing",
        "",
        "Recommended Models:",
        "  llama3.1 / llama3.2 (balanced)",
        "  mixtral (high quality)",
        "  mistral (fast)",
        "  Multi-reviewer: Use 2-3 models for consensus"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 16: Future Enhancements
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Future Enhancements"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Planned Features",
        "",
        "Additional databases (EMBASE, Web of Science)",
        "Citation network analysis",
        "Temporal trend analysis",
        "Comparative chemical analysis",
        "Export to standard formats (RIS, EndNote)",
        "API for programmatic access",
        "Batch processing capabilities",
        "Enhanced full-text retrieval",
        "Integration with chemical databases",
        "Custom KC definitions support"
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 17: Conclusion
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    title = slide.shapes.title
    content = slide.placeholders[1]

    title.text = "Conclusion"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    items = [
        "Summary",
        "",
        "AI Toxicologist provides a comprehensive, automated solution for systematic literature review in hepatotoxicity assessment.",
        "",
        "Key Benefits:",
        "  Reproducible, structured outputs",
        "  PRISMA 2020 compliant",
        "  Open-source and extensible",
        "  Multi-reviewer consensus mode",
        "  Full provenance tracking",
        "",
        "Impact:",
        "  Accelerates evidence synthesis",
        "  Standardizes assessment methodology",
        "  Enhances reproducibility",
        "  Supports regulatory decision-making",
        "",
        "Ready for use in research, regulatory, and industry applications."
    ]
    add_bullet_points(content.text_frame, items)

    # Slide 18: Thank You
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    title = slide.shapes.title
    subtitle = slide.placeholders[1]

    title.text = "Thank You"
    title.text_frame.paragraphs[0].font.size = Pt(54)
    title.text_frame.paragraphs[0].font.bold = True
    title.text_frame.paragraphs[0].font.color.rgb = title_color

    subtitle.text = "Questions and Discussion\n\nContact:\nGitHub Repository\nDocumentation\nDemo Available"
    subtitle.text_frame.paragraphs[0].font.size = Pt(24)
    subtitle.text_frame.paragraphs[0].font.color.rgb = text_color

    # Save presentation
    filename = "AI_Toxicologist_Presentation_Fixed.pptx"
    prs.save(filename)
    print(f"✅ Presentation created successfully: {filename}")
    print(f"   Total slides: {len(prs.slides)}")

    return filename

if __name__ == "__main__":
    try:
        create_presentation()
    except ImportError:
        print("Error: python-pptx library not found.")
        print("Please install it with: pip install python-pptx")
    except Exception as e:
        print(f"Error creating presentation: {e}")
        import traceback
        traceback.print_exc()
