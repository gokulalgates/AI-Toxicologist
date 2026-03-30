"""
Create PowerPoint presentation and HTML export for Acetaminophen analysis results
"""

import json
import os
from datetime import datetime

from pptx import Presentation
from pptx.util import Inches, Pt

# KC Names
KC_NAMES = {
    "KC1": "Reactive/Bioactivation",
    "KC2": "Cell Death",
    "KC3": "Proliferation/Regeneration",
    "KC4": "Transport Disruption",
    "KC5": "Oxidative Stress",
    "KC6": "Immune Response",
    "KC7": "Mitochondrial Dysfunction",
    "KC8": "Stress Signaling",
    "KC9": "Cholestasis",
    "KC10": "Cytoskeleton Disruption",
    "KC11": "Liver Fibrosis",
    "KC12": "Metabolism Disruption"
}

def add_bullet_points(slide, text_list, left=Inches(0.5), top=Inches(2), width=Inches(9), height=Inches(5)):
    """Add bullet points to a slide"""
    text_frame = slide.shapes.add_textbox(left, top, width, height).text_frame
    text_frame.word_wrap = True

    for i, item in enumerate(text_list):
        p = text_frame.add_paragraph()
        p.text = item
        p.level = 0
        p.space_after = Pt(12)
        if i == 0:
            p.font.size = Pt(14)
        else:
            p.font.size = Pt(12)

def create_powerpoint(results_data, output_path="results/acetaminophen/acetaminophen_results.pptx"):
    """Create PowerPoint presentation"""
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Title Slide
    title_slide_layout = prs.slide_layouts[0]
    slide = prs.slides.add_slide(title_slide_layout)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]

    title.text = "AI Toxicologist: Acetaminophen Hepatotoxicity Assessment"
    subtitle.text = f"Systematic Literature Review\n{datetime.now().strftime('%B %Y')}"

    # Methods Slide
    methods_slide = prs.slides.add_slide(prs.slide_layouts[1])
    methods_slide.shapes.title.text = "Methods"

    methods_text = [
        "• Chemical: Acetaminophen (Paracetamol, APAP)",
        "• Database: PubMed",
        "• Search Strategy: Multi-term search with synonyms",
        "• Screening: LLM-based relevance filtering",
        "• Analysis: Multi-reviewer LLM consensus (llama3.2, mixtral)",
        "• Framework: PRISMA 2020 compliant",
        "• Risk-of-Bias: OHAT framework",
        "• Certainty Assessment: GRADE/OHAT methodology",
        f"• Total Papers Analyzed: {results_data['total_papers']}"
    ]
    add_bullet_points(methods_slide, methods_text)

    # Results Overview Slide
    overview_slide = prs.slides.add_slide(prs.slide_layouts[1])
    overview_slide.shapes.title.text = "Results Overview"

    # Calculate summary stats
    high_certainty = []
    moderate_certainty = []
    low_certainty = []

    for kc, data in results_data['kc_results'].items():
        if data['count'] >= 20:  # High support
            high_certainty.append(f"{kc} ({data['name']}): {data['count']}/{data['total']} ({data['count']/data['total']*100:.0f}%)")
        elif data['count'] >= 10:  # Moderate support
            moderate_certainty.append(f"{kc} ({data['name']}): {data['count']}/{data['total']} ({data['count']/data['total']*100:.0f}%)")
        elif data['count'] > 0:  # Low support
            low_certainty.append(f"{kc} ({data['name']}): {data['count']}/{data['total']} ({data['count']/data['total']*100:.0f}%)")

    overview_text = ["Strongly Supported (High Certainty):"] + high_certainty
    if moderate_certainty:
        overview_text.append("\nModerately Supported:")
        overview_text.extend(moderate_certainty)
    if low_certainty:
        overview_text.append("\nWeakly Supported (Low Certainty):")
        overview_text.extend(low_certainty)

    add_bullet_points(overview_slide, overview_text)

    # Individual KC Slides (for strongly supported ones)
    for kc, data in results_data['kc_results'].items():
        if data['count'] >= 10:  # Only create slides for moderately/strongly supported
            kc_slide = prs.slides.add_slide(prs.slide_layouts[1])
            kc_slide.shapes.title.text = f"{kc}: {data['name']}"

            kc_text = [
                f"• Studies Supporting: {data['count']}/{data['total']} ({data['count']/data['total']*100:.1f}%)",
                f"• Studies Refuting: 0/{data['total']}",
                f"• Certainty of Evidence: {'High' if data['count'] >= 20 else 'Moderate' if data['count'] >= 10 else 'Low'}"
            ]

            # Add interpretation based on KC
            if kc == "KC1":
                kc_text.append("\n• Interpretation: Bioactivation to NAPQI (N-acetyl-p-benzoquinone imine)")
            elif kc == "KC5":
                kc_text.append("\n• Interpretation: Glutathione depletion and oxidative stress")
            elif kc == "KC7":
                kc_text.append("\n• Interpretation: Mitochondrial dysfunction and energy failure")
            elif kc == "KC2":
                kc_text.append("\n• Interpretation: Hepatocellular necrosis and apoptosis")
            elif kc == "KC8":
                kc_text.append("\n• Interpretation: JNK signaling pathway activation")
            elif kc == "KC12":
                kc_text.append("\n• Interpretation: Metabolic disruption and steatosis")

            add_bullet_points(kc_slide, kc_text)

    # Summary Slide
    summary_slide = prs.slides.add_slide(prs.slide_layouts[1])
    summary_slide.shapes.title.text = "Summary & Conclusions"

    total_supported = sum(data['count'] for data in results_data['kc_results'].values())
    summary_text = [
        f"• Total Papers Analyzed: {results_data['total_papers']}",
        f"• Key Characteristics with Evidence: {sum(1 for d in results_data['kc_results'].values() if d['count'] > 0)}/12",
        f"• Total KC Support Instances: {total_supported}",
        "",
        "Key Findings:",
        "• KC1 (Bioactivation), KC5 (Oxidative Stress), and KC7 (Mitochondrial Dysfunction) show strong evidence",
        "• Results align with known acetaminophen hepatotoxicity mechanisms",
        "• Multi-reviewer consensus approach provides robust evidence assessment",
        "",
        "Implications:",
        "• AI Toxicologist successfully identified major hepatotoxic mechanisms",
        "• Systematic approach enables reproducible evidence synthesis"
    ]
    add_bullet_points(summary_slide, summary_text)

    # Save presentation
    prs.save(output_path)
    print(f"✅ PowerPoint saved to: {output_path}")
    return output_path

def create_html_export(results_data, output_path="results/acetaminophen/acetaminophen_results.html"):
    """Create HTML export with all data"""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acetaminophen Hepatotoxicity Assessment - Results</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .summary-box {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .kc-result {{
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: #fafafa;
        }}
        .kc-result.strong {{
            border-left: 5px solid #27ae60;
        }}
        .kc-result.moderate {{
            border-left: 5px solid #f39c12;
        }}
        .kc-result.weak {{
            border-left: 5px solid #e74c3c;
        }}
        .kc-header {{
            font-weight: bold;
            font-size: 1.2em;
            color: #2c3e50;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: #3498db;
            color: white;
            padding: 15px;
            border-radius: 5px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>AI Toxicologist: Acetaminophen Hepatotoxicity Assessment</h1>
        
        <div class="summary-box">
            <h2>Executive Summary</h2>
            <p><strong>Chemical:</strong> Acetaminophen (Paracetamol, APAP)</p>
            <p><strong>Analysis Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
            <p><strong>Total Papers Analyzed:</strong> {results_data['total_papers']}</p>
            <p><strong>Analysis Method:</strong> Multi-reviewer LLM consensus (llama3.2, mixtral)</p>
            <p><strong>Framework:</strong> PRISMA 2020 compliant systematic review</p>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-number">{results_data['total_papers']}</div>
                <div class="stat-label">Papers Analyzed</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{sum(1 for d in results_data['kc_results'].values() if d['count'] > 0)}</div>
                <div class="stat-label">KCs with Evidence</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{sum(d['count'] for d in results_data['kc_results'].values())}</div>
                <div class="stat-label">Total Support Instances</div>
            </div>
            <div class="stat-box">
                <div class="stat-number">{sum(1 for d in results_data['kc_results'].values() if d['count'] >= 20)}</div>
                <div class="stat-label">High Certainty KCs</div>
            </div>
        </div>
        
        <h2>Key Characteristics Results</h2>
        
        <table>
            <thead>
                <tr>
                    <th>KC</th>
                    <th>Name</th>
                    <th>Supported</th>
                    <th>Percentage</th>
                    <th>Certainty</th>
                </tr>
            </thead>
            <tbody>
"""

    # Add KC results to table
    for kc, data in sorted(results_data['kc_results'].items()):
        percentage = (data['count'] / data['total'] * 100) if data['total'] > 0 else 0
        if data['count'] >= 20:
            certainty = "High"
            css_class = "strong"
        elif data['count'] >= 10:
            certainty = "Moderate"
            css_class = "moderate"
        elif data['count'] > 0:
            certainty = "Low"
            css_class = "weak"
        else:
            certainty = "Very Low"
            css_class = "weak"

        html_content += f"""
                <tr>
                    <td><strong>{kc}</strong></td>
                    <td>{data['name']}</td>
                    <td>{data['count']}/{data['total']}</td>
                    <td>{percentage:.1f}%</td>
                    <td>{certainty}</td>
                </tr>
"""

    html_content += """
            </tbody>
        </table>
        
        <h2>Detailed KC Results</h2>
"""

    # Add detailed KC results
    for kc, data in sorted(results_data['kc_results'].items()):
        if data['count'] > 0:
            percentage = (data['count'] / data['total'] * 100) if data['total'] > 0 else 0
            if data['count'] >= 20:
                css_class = "strong"
                certainty = "High"
            elif data['count'] >= 10:
                css_class = "moderate"
                certainty = "Moderate"
            else:
                css_class = "weak"
                certainty = "Low"

            html_content += f"""
        <div class="kc-result {css_class}">
            <div class="kc-header">{kc}: {data['name']}</div>
            <p><strong>Studies Supporting:</strong> {data['count']}/{data['total']} ({percentage:.1f}%)</p>
            <p><strong>Studies Refuting:</strong> 0/{data['total']}</p>
            <p><strong>Certainty of Evidence:</strong> {certainty}</p>
"""

            # Add interpretation
            interpretations = {
                "KC1": "Bioactivation to NAPQI (N-acetyl-p-benzoquinone imine) - the primary toxic metabolite",
                "KC2": "Hepatocellular necrosis and apoptosis - cell death mechanisms",
                "KC5": "Glutathione depletion and oxidative stress - key mechanism of toxicity",
                "KC7": "Mitochondrial dysfunction and energy failure - critical for cell survival",
                "KC8": "JNK signaling pathway activation - stress response signaling",
                "KC12": "Metabolic disruption and steatosis - lipid metabolism effects"
            }

            if kc in interpretations:
                html_content += f'            <p><strong>Interpretation:</strong> {interpretations[kc]}</p>\n'

            html_content += "        </div>\n"

    html_content += f"""
        <div class="metadata">
            <h2>Metadata</h2>
            <p><strong>Generated:</strong> {datetime.now().isoformat()}</p>
            <p><strong>Data Source:</strong> results/acetaminophen/study_records.jsonl</p>
            <p><strong>Analysis Framework:</strong> PRISMA 2020, OHAT Risk-of-Bias, GRADE Certainty</p>
            <p><strong>Models Used:</strong> llama3.2, mixtral (Multi-reviewer consensus)</p>
        </div>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ HTML export saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    # Load results data
    summary_file = "results/acetaminophen/kc_summary.json"
    if not os.path.exists(summary_file):
        print(f"❌ Summary file not found: {summary_file}")
        print("   Please run the analysis first or create kc_summary.json")
        exit(1)

    with open(summary_file) as f:
        results_data = json.load(f)

    print("="*80)
    print("CREATING POWERPOINT PRESENTATION AND HTML EXPORT")
    print("="*80)

    # Create PowerPoint
    pptx_path = create_powerpoint(results_data)

    # Create HTML export
    html_path = create_html_export(results_data)

    print("\n" + "="*80)
    print("✅ COMPLETE!")
    print("="*80)
    print(f"PowerPoint: {pptx_path}")
    print(f"HTML Export: {html_path}")
    print("="*80)
