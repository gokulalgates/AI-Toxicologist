# Presentation Script: AI Toxicologist for Scientific Audiences

## Slide 1: Title Slide
**Title**: "AI Toxicologist: Automated Systematic Review for Chemical Toxicity Assessment"

**Subtitle**: "Using Large Language Models to Identify Mechanisms of Liver Toxicity"

**Presenter**: [Your Name]
**Date**: [Date]
**Institution**: [Your Institution]

---

## Slide 2: The Problem
**Title**: "The Challenge: Too Much Literature, Too Little Time"

**Points**:
- Thousands of papers published each year on chemical toxicity
- Traditional systematic reviews take **weeks to months**
- Human reviewers may miss papers or be inconsistent
- Need for **fast, comprehensive, and consistent** evidence synthesis

**Visual**: Graph showing exponential growth of scientific publications

---

## Slide 3: Our Solution
**Title**: "AI Toxicologist: An Automated Systematic Review System"

**What it does**:
1. **Searches** PubMed automatically
2. **Reads** abstracts with AI
3. **Identifies** mechanisms of toxicity
4. **Assesses** study quality
5. **Synthesizes** evidence across studies
6. **Visualizes** results

**Key Benefit**: Reduces review time from **months to hours**

**Visual**: Flowchart showing the process

---

## Slide 4: The 12 Key Characteristics
**Title**: "What Mechanisms Does It Identify?"

**Explanation**: The system identifies 12 biological mechanisms (Key Characteristics) that can cause liver toxicity:

**Categories**:
- **Metabolic**: Bioactivation (KC1), Metabolism Disruption (KC12)
- **Cellular**: Cell Death (KC2), Mitochondrial Dysfunction (KC7)
- **Stress**: Oxidative Stress (KC5), Stress Signaling (KC8)
- **Structural**: Transport Disruption (KC4), Cholestasis (KC9), Cytoskeleton Disruption (KC10)
- **Repair**: Proliferation/Regeneration (KC3), Liver Fibrosis (KC11)
- **Immune**: Immune Response (KC6)

**Visual**: Diagram showing the 12 KCs organized by category

---

## Slide 5: How It Works - Overview
**Title**: "The Process: From Chemical Name to Evidence Summary"

**Steps** (with simple explanations):

1. **Chemical Standardization**
   - "We take a chemical name like 'acetaminophen'"
   - "Find all its synonyms: paracetamol, APAP, etc."
   - "This ensures we don't miss any papers"

2. **PubMed Search**
   - "Search for papers mentioning the chemical AND liver toxicity"
   - "Retrieve up to 100 abstracts"

3. **Relevance Filtering**
   - "AI reads each abstract"
   - "Keeps only papers actually studying liver toxicity"
   - "Filters down to 15-20 most relevant studies"

4. **Key Characteristics Analysis**
   - "AI reads each abstract"
   - "Identifies which of the 12 mechanisms are supported"
   - "Creates a structured dataset"

5. **Quality Assessment**
   - "Assesses study quality using OHAT framework"
   - "Identifies potential bias"

6. **Evidence Synthesis**
   - "Combines results from all studies"
   - "Calculates how many studies support each mechanism"
   - "Assesses certainty of evidence"

**Visual**: Simple flowchart

---

## Slide 6: How the AI Identifies Mechanisms
**Title**: "How Does the AI 'Read' Papers?"

**Simple Explanation**:
- **Large Language Models (LLMs)** are AI systems trained on millions of scientific papers
- They can understand text, extract information, and make judgments
- Think of them as **very fast, tireless research assistants**

**How it works**:
1. **Input**: Abstract text + definitions of each Key Characteristic
2. **Processing**: AI reads the text and looks for:
   - Keywords related to each mechanism
   - Descriptions of biological processes
   - Evidence statements
3. **Output**: Structured data (which KCs are supported, with reasoning)

**Example**:
```
Input: "Acetaminophen is metabolized to NAPQI, which causes oxidative stress..."
AI identifies:
- KC1 (Bioactivation): SUPPORTED ✓
- KC5 (Oxidative Stress): SUPPORTED ✓
```

**Visual**: Diagram showing input → processing → output

---

## Slide 7: Multi-Reviewer Mode
**Title**: "Increasing Reliability Through Consensus"

**Concept**: Like having multiple scientists review the same papers

**How it works**:
- **Multiple AI models** independently analyze the same studies
- Each model makes its own assessment
- Results are compared and consensus is calculated

**Benefits**:
- **Higher reliability**: If 3 models agree, we're more confident
- **Identifies disputes**: If models disagree, we know to be cautious
- **Agreement statistics**: Quantifies how much models agree (Cohen's κ)

**Example**:
```
Model 1: KC1 = SUPPORTED
Model 2: KC1 = SUPPORTED
Model 3: KC1 = SUPPORTED
→ Consensus: KC1 is SUPPORTED (100% agreement)
```

**Visual**: Diagram showing multiple models → consensus

---

## Slide 8: Study Quality Assessment
**Title**: "Not All Studies Are Created Equal"

**Framework**: OHAT (Office of Health Assessment and Translation)

**7 Domains Assessed**:
1. Selection Bias
2. Confounding
3. Performance Bias
4. Detection/Measurement Bias
5. Attrition Bias
6. Selective Reporting
7. Other Sources of Bias

**Judgment Levels**:
- 🟢 **Low**: High-quality study
- 🟠 **Some concerns**: Moderate quality
- 🔴 **High**: Significant bias concerns
- ⚫ **Critical**: Critical flaws

**Why it matters**: High-quality studies provide more reliable evidence

**Visual**: Diagram showing the 7 domains

---

## Slide 9: Visualizations - Evidence Matrix
**Title**: "Evidence Matrix Heatmap: Which Studies Support Which Mechanisms?"

**What it shows**:
- **Rows**: Each study (paper)
- **Columns**: Each Key Characteristic (KC1-KC12)
- **Colors**:
  - 🟢 Green = Mechanism is SUPPORTED
  - ⚪ White = Mechanism is NOT MENTIONED
  - 🔴 Red = Mechanism is REFUTED

**How to read**:
- **Dense green columns** = Strong evidence (many studies support)
- **Sparse columns** = Weak evidence (few studies mention)
- **Patterns** = Commonly co-occurring mechanisms

**Example**: "KC1 column is all green → all studies found evidence for bioactivation"

**Visual**: Screenshot of the heatmap

---

## Slide 10: Visualizations - Risk-of-Bias Summary
**Title**: "Study Quality: How Good Is the Evidence?"

**What it shows**: Bar chart of study quality distribution

**X-axis**: Judgment categories (Low, Some concerns, High, Critical)
**Y-axis**: Number of studies

**Interpretation**:
- **Tall green bar** = Many high-quality studies (good!)
- **Tall orange/red bars** = Many studies with bias concerns (be cautious!)

**Example**: 
- 8 studies = Low risk (53%)
- 6 studies = Some concerns (40%)
- 1 study = Insufficient information (7%)

**Takeaway**: Most studies are moderate-to-high quality

**Visual**: Screenshot of the bar chart

---

## Slide 11: Visualizations - Risk-of-Bias Heatmap
**Title**: "Quality of Evidence by Mechanism and Bias Domain"

**What it shows**: 
- **Rows**: Key Characteristics (only those supported)
- **Columns**: 7 OHAT bias domains
- **Colors**: Green = Low risk, Orange = Some concerns, Red = High risk

**How to read**:
- **Green cells** = High-quality evidence for this mechanism
- **Orange/Red cells** = Evidence with bias concerns
- **Patterns** = Consistent green = high-quality evidence

**Example**: "KC1 row is mostly green → bioactivation is supported by high-quality studies"

**Visual**: Screenshot of the heatmap

---

## Slide 12: Case Study - Acetaminophen
**Title**: "Example: Acetaminophen-Induced Liver Toxicity"

**Input**:
- Chemical: Acetaminophen (paracetamol)
- Studies analyzed: 15
- Model: llama3.2

**Key Findings**:

1. **KC1 (Bioactivation)**: 15/15 studies (100%) support
   - Mechanism: Acetaminophen → NAPQI (toxic metabolite)
   - Certainty: **High**

2. **KC5 (Oxidative Stress)**: 15/15 studies (100%) support
   - Mechanism: NAPQI depletes glutathione → oxidative damage
   - Certainty: **High**

3. **KC7 (Mitochondrial Dysfunction)**: 12/15 studies (80%) support
   - Mechanism: Mitochondrial damage → energy depletion
   - Certainty: **Moderate**

4. **KC2 (Cell Death)**: 6/15 studies (40%) support
   - Mechanism: Hepatocyte death
   - Certainty: **Low**

**Study Quality**:
- Low risk: 8/15 (53%)
- Some concerns: 6/15 (40%)

**Visual**: Summary table and pathway diagram

---

## Slide 13: Identified Pathway
**Title**: "Mechanistic Pathway: How Acetaminophen Causes Liver Damage"

**Pathway**:
```
Acetaminophen 
  ↓ (Bioactivation - KC1)
NAPQI (Reactive Metabolite)
  ↓ (Oxidative Stress - KC5)
Glutathione Depletion
  ↓ (Mitochondrial Dysfunction - KC7)
Mitochondrial Damage
  ↓ (Cell Death - KC2)
Hepatocyte Death
```

**Supporting Mechanisms**:
- Stress Signaling (KC8): 60% support
- Metabolism Disruption (KC12): 53% support

**Visual**: Pathway diagram with arrows

---

## Slide 14: Advantages
**Title**: "Why Use AI for Systematic Reviews?"

**Speed**:
- Traditional: **Weeks to months**
- AI Toxicologist: **Hours to days**
- **10-100x faster**

**Consistency**:
- Same criteria applied to all studies
- No human fatigue or bias
- Reproducible results

**Comprehensiveness**:
- Can analyze hundreds of studies
- Doesn't miss papers due to human error
- Systematic approach

**Transparency**:
- All decisions documented
- Can see which studies support which mechanisms
- PRISMA-compliant reporting

**Visual**: Comparison table

---

## Slide 15: Limitations
**Title**: "What Are the Limitations?"

**Abstract-Only Analysis**:
- Full-text contains more detail
- Some evidence may be missed
- **Solution**: Can retrieve full-text when available

**AI Model Limitations**:
- May misinterpret complex text
- May miss subtle evidence
- **Solution**: Multi-reviewer mode increases reliability

**Study Quality Assessment**:
- Based on text, not raw data
- Cannot verify methods directly
- **Solution**: Uses established frameworks (OHAT)

**Animal/In Vitro Studies**:
- Most studies not human clinical trials
- Certainty limited by study type
- **Solution**: Certainty grading accounts for study type

**Visual**: List with icons

---

## Slide 16: Use Cases
**Title**: "Who Can Use This System?"

**1. Regulatory Assessment**
- Identify mechanisms for chemical safety evaluation
- Support risk assessment decisions
- **Users**: EPA, FDA, regulatory agencies

**2. Research Prioritization**
- Identify knowledge gaps
- Guide future research directions
- **Users**: Researchers, funding agencies

**3. Literature Review**
- Quickly synthesize large bodies of literature
- Identify consensus vs. disputed findings
- **Users**: Graduate students, postdocs, researchers

**4. Teaching Tool**
- Demonstrate systematic review methodology
- Show evidence synthesis
- **Users**: Professors, students

**Visual**: Icons for each use case

---

## Slide 17: Interpreting Results
**Title**: "How to Interpret the Results"

**Strong Evidence (High Certainty)**:
- Many studies support (>80%)
- Studies are high quality
- Findings are consistent
- **Example**: KC1 for acetaminophen

**Moderate Evidence**:
- Some studies support (40-80%)
- Studies have moderate quality
- Findings are somewhat consistent
- **Example**: KC2 for acetaminophen

**Weak Evidence (Low Certainty)**:
- Few studies support (<40%)
- Studies have quality concerns
- Findings are inconsistent
- **Example**: KC6 for acetaminophen

**No Evidence**:
- Mechanism not mentioned
- Cannot assess
- **Example**: KC4 for acetaminophen

**Visual**: Examples from acetaminophen analysis

---

## Slide 18: Future Directions
**Title**: "What's Next?"

**Improvements**:
- Full-text retrieval and analysis
- More sophisticated causal pathway extraction
- Integration with experimental data
- Human-AI collaboration features

**Expansions**:
- Other organs (kidney, lung, etc.)
- Other endpoints (cancer, developmental toxicity)
- Real-time literature monitoring

**Research Questions**:
- How does AI compare to human reviewers?
- Can AI identify novel mechanisms?
- How to best combine AI and human expertise?

**Visual**: Roadmap diagram

---

## Slide 19: Conclusion
**Title**: "Summary"

**Key Points**:
1. AI Toxicologist automates systematic review of toxicity literature
2. Identifies mechanisms (12 Key Characteristics) from abstracts
3. Assesses study quality (risk-of-bias)
4. Synthesizes evidence across studies
5. Creates visualizations for easy interpretation

**Benefits**:
- Fast and comprehensive
- Consistent and transparent
- Reproducible

**Impact**:
- Supports evidence-based decision-making
- Accelerates research
- Improves consistency

**Visual**: Summary diagram

---

## Slide 20: Questions & Discussion
**Title**: "Thank You! Questions?"

**Contact Information**:
- Email: [Your Email]
- GitHub: [Repository Link]
- Website: [If Available]

**Resources**:
- Documentation: [Link]
- Code: [Link]
- Demo: [Link]

**Visual**: Contact information slide

---

## Appendix: Detailed Technical Explanations

### How Evidence Matrix is Calculated

**Step 1**: For each study, convert KC status to numbers
- SUPPORTED = 1 (green)
- ASSOCIATED = 0.7 (yellow)
- CAUSALLY_LINKED = 0.5 (yellow)
- NOT_MENTIONED = 0 (white)
- REFUTED = -1 (red)

**Step 2**: Create matrix (studies × KCs)

**Step 3**: Visualize with color-coded heatmap

### How Risk-of-Bias Summary is Calculated

**Step 1**: Assess each study for 7 OHAT domains

**Step 2**: Determine overall judgment (Low, Some concerns, High, Critical)

**Step 3**: Count studies by judgment category

**Step 4**: Create bar chart

### How Risk-of-Bias Heatmap is Calculated

**Step 1**: Filter to KCs supported by at least one study

**Step 2**: For each KC-Domain pair:
- Find all studies supporting that KC
- Get domain judgments from those studies
- Calculate average judgment (numeric: Low=0, Some concerns=1, High=2, Critical=3)

**Step 3**: Visualize as heatmap (KCs × Domains)

---

## Presentation Tips

1. **Start with the problem**: Why do we need this?
2. **Explain simply**: Avoid jargon, use analogies
3. **Show examples**: Use acetaminophen case study
4. **Visualize**: Show actual screenshots/plots
5. **Be honest**: Acknowledge limitations
6. **Engage**: Ask questions, encourage discussion

**Timing**: 
- 15-20 minutes for presentation
- 5-10 minutes for Q&A

**Audience Adaptation**:
- **General scientists**: Focus on use cases and benefits
- **Toxicologists**: Focus on mechanisms and evidence
- **Computer scientists**: Focus on AI/ML aspects
- **Regulators**: Focus on quality assessment and transparency
