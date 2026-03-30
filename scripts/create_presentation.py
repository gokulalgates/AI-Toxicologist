import pptx


def create_presentation():
    """Creates the PowerPoint presentation."""

    prs = pptx.Presentation()

    # Slide 1: Title Slide
    slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "The AI Toxicologist: A Framework for Automated Hepatotoxicity Assessment"
    subtitle.text = "Leveraging Large Language Models for Systematic Literature Review\n\nUC Berkeley"

    # Slide 2: Introduction
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Introduction: The Challenge of Hepatotoxicity Assessment"
    content.text_frame.text = "Assessing chemical-induced liver injury is a complex and time-consuming process.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Systematic reviews are the gold standard but require significant manual effort.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "The 'Key Characteristics of Human Hepatotoxicants' (Rusyn et al., 2021) provide a structured framework for this assessment."

    # Slide 3: The 12 Key Characteristics
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "The 12 Key Characteristics of Human Hepatotoxicants"
    content.text_frame.text = (
        "KC1: Is reactive and/or is metabolized to reactive moieties\n"
        "KC2: Causes death of liver cells\n"
        "KC3: Affects liver cell proliferation and/or tissue regeneration\n"
        "KC4: Disrupts transport function\n"
        "KC5: Induces oxidative stress\n"
        "KC6: Triggers immune-mediated responses\n"
        "KC7: Causes mitochondrial dysfunction\n"
        "KC8: Activates stress signaling pathways\n"
        "KC9: Causes cholestasis\n"
        "KC10: Disrupts cellular cytoskeleton\n"
        "KC11: Causes liver fibrosis\n"
        "KC12: Disrupts liver metabolism"
    )

    # Slide 4: The "AI Toxicologist"
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "The 'AI Toxicologist': An Automated Solution"
    content.text_frame.text = "An automated tool that performs a systematic literature review to assess chemical hepatotoxicity.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Capabilities:\n"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Automated literature search and retrieval from PubMed"
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "AI-powered analysis of abstracts against the 12 KCs"
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "Generation of evidence matrices and causal pathway networks"
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "PRISMA-compliant systematic review process"
    p.level = 2

    # Slide 5: Application Workflow
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Application Workflow: From Chemical to Conclusion"
    content.text_frame.text = (
        "1. The Librarian: Standardizes chemical name and searches PubMed.\n"
        "2. The Gatekeeper: Filters abstracts for relevance to liver toxicity.\n"
        "3. The Analyst: Analyzes abstracts for KCs and causal links.\n"
        "4. The Scrutinizer: Assesses risk of bias and certainty of evidence.\n"
        "5. The Architect: Synthesizes evidence and generates visualizations."
    )

    # Slide 6: The Librarian
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Step 1: The Librarian - Finding the Right Literature"
    content.text_frame.text = "Standardizes chemical names using PubChem to resolve synonyms.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Performs an enhanced search on PubMed, using MeSH terms and synonyms to maximize recall and precision."

    # Slide 7: The Gatekeeper
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Step 2: The Gatekeeper - Ensuring Relevance"
    content.text_frame.text = "Filters abstracts for relevance to liver toxicity using a targeted LLM prompt.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Prompt used:\n"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "'Determine if the following abstract describes ADVERSE EFFECTS, TOXICITY, or SAFETY HAZARDS of the chemical '{chemical_name}' specifically in the LIVER.'"
    p.level = 2

    # Slide 8: The Analyst
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Step 3: The Analyst - Core Mechanistic Analysis"
    content.text_frame.text = "The core of the application: uses an LLM to analyze abstracts against the 12 KCs.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Employs a variable prompt strategy based on abstract complexity:\n"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Simple Prompt: For short abstracts"
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "Standard Prompt: For regular abstracts"
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "Detailed Prompt: For long abstracts or full text"
    p.level = 2

    # Slide 9: The "Standard" Prompt
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "The 'Standard' Prompt: A Deep Dive"
    content.text_frame.text = "Key components of the standard prompt:\n"
    p = content.text_frame.add_paragraph()
    p.text = "Role: 'You are an Expert Toxicologist and Systematic Reviewer.'"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "KC Definitions: Provides the LLM with the definitions of the 12 KCs."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Instructions: A step-by-step process for the LLM to follow (Scan, Evaluate, Quote, Link, Decide)."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Few-Shot Examples: Concrete examples to guide the LLM's analysis."
    p.level = 1

    # Slide 10: Enhancing the Prompt
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Enhancing the Prompt: Synonym Recognition"
    content.text_frame.text = "The 'enhanced' prompt provides a list of synonyms for each KC to improve detection.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Example for KC1 (Reactive/Bioactivation):\n'Look for: 'metabolized', 'bioactivation', 'reactive metabolite', 'NAPQI', 'CYP450', etc.'"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "\nExample for KC5 (Oxidative Stress):\n'Look for: 'oxidative stress', 'ROS', 'glutathione depletion', 'lipid peroxidation', etc.'"
    p.level = 1

    # Slide 11: Case Study
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Case Study: The Acetaminophen-Specific Prompt"
    content.text_frame.text = "Injects prior knowledge into the prompt for well-studied chemicals.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Provides the LLM with known mechanisms for Acetaminophen:\n'Known Mechanisms:\n- KC1: Metabolized by CYP2E1/CYP3A4 to NAPQI\n- KC5: NAPQI depletes glutathione, causing oxidative stress\n- KC8: Activates stress signaling (JNK, p38 MAPK)'"
    p.level = 1

    # Slide 12: The "Liberal" Prompt
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "The 'Liberal' Prompt: Casting a Wider Net"
    content.text_frame.text = "A more permissive prompt used when standard prompts may be too strict.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Instructs the LLM to 'Be LIBERAL in detecting mechanisms' and to mark a KC as SUPPORTED if a mechanism is even indirectly implied."
    p.level = 1

    # Slide 13: Causal Reasoning
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Causal Reasoning: Moving Beyond Co-occurrence"
    content.text_frame.text = "Identifies causal relationships between KCs using a two-pronged approach:\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "1. Prompt Engineering: Provides the LLM with a rigorous framework for identifying causal links (Temporal Relationship, Mechanistic Explanation)."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "2. Post-processing Validation: Programmatically validates the LLM's output by checking for specific keywords."
    p.level = 1

    # Slide 14: The Scrutinizer
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Step 4: The Scrutinizer - Assessing Study Quality"
    content.text_frame.text = "Assesses the Risk of Bias (RoB) for each study using the OHAT framework.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "This is a key feature for ensuring the scientific rigor of the analysis."
    p.level = 1

    # Slide 15: The Risk-of-Bias Prompt
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "The Risk-of-Bias Prompt"
    content.text_frame.text = "The RoB prompt instructs the LLM to:\n"
    p = content.text_frame.add_paragraph()
    p.text = "Act as a 'systematic review expert'."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Assess each OHAT domain ('Low', 'Some concerns', 'High', etc.)."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Provide a rationale and supporting quote for each judgment."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Critically, use 'Insufficient information' when details are missing."
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Extract the study type and species."
    p.level = 1

    # Slide 16: The Architect
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Step 5: The Architect - Synthesizing the Evidence"
    content.text_frame.text = "The application generates several visualizations to synthesize the evidence:\n"
    p = content.text_frame.add_paragraph()
    p.text = "Evidence Matrix Heatmap"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Causal Pathway Network"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "PRISMA Flow Diagram"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Risk-of-Bias Heatmap"
    p.level = 1

    # Slide 17: Advanced Features
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Advanced Features for Systematic Reviews"
    content.text_frame.text = (
        "Multi-Reviewer Mode: Uses multiple LLMs for consensus and higher reliability.\n"
        "Certainty Grading: GRADE/OHAT-style certainty ratings for each KC.\n"
        "Full-Text Retrieval: Can retrieve and analyze full-text articles.\n"
        "Reproducibility: Tracks provenance and creates experiment snapshots."
    )

    # Slide 18: Conclusion
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    content = slide.placeholders[1]
    title.text = "Conclusion & Future Directions"
    content.text_frame.text = "The AI Toxicologist is a powerful tool for automating systematic reviews of chemical hepatotoxicity.\n\n"
    p = content.text_frame.add_paragraph()
    p.text = "Future Directions:\n"
    p.level = 1
    p = content.text_frame.add_paragraph()
    p.text = "Expand to other toxicological endpoints."
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "Integrate more knowledge bases and data sources."
    p.level = 2
    p = content.text_frame.add_paragraph()
    p.text = "Improve the user interface for more interactive analysis."
    p.level = 2

    # Slide 19: Q&A
    slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(slide_layout)
    title = slide.shapes.title
    title.text = "Thank You\n\nQuestions?"

    prs.save("AI_Toxicologist_Presentation.pptx")

if __name__ == "__main__":
    create_presentation()
