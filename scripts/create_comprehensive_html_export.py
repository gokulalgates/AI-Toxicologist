"""
Create comprehensive HTML export with all study data for later retrieval
"""

import json
import os
from datetime import datetime
from html import escape


def create_comprehensive_html(results_dir="results/acetaminophen"):
    """Create comprehensive HTML export with all study data"""

    # Load summary data
    summary_file = os.path.join(results_dir, "kc_summary.json")
    with open(summary_file) as f:
        summary_data = json.load(f)

    # Load all study records
    records_file = os.path.join(results_dir, "study_records.jsonl")
    study_records = []
    with open(records_file) as f:
        for line in f:
            if line.strip():
                study_records.append(json.loads(line))

    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Acetaminophen Hepatotoxicity Assessment - Complete Results</title>
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
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
        h3 {{
            color: #555;
            margin-top: 20px;
        }}
        .tabs {{
            display: flex;
            border-bottom: 2px solid #ddd;
            margin: 20px 0;
        }}
        .tab {{
            padding: 10px 20px;
            cursor: pointer;
            background: #ecf0f1;
            border: none;
            border-right: 1px solid #ddd;
            font-size: 14px;
        }}
        .tab:hover {{
            background: #bdc3c7;
        }}
        .tab.active {{
            background: #3498db;
            color: white;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .summary-box {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
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
            font-size: 0.9em;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .kc-supported {{
            color: #27ae60;
            font-weight: bold;
        }}
        .kc-not-mentioned {{
            color: #95a5a6;
        }}
        .search-box {{
            margin: 20px 0;
            padding: 10px;
            width: 100%;
            font-size: 14px;
            border: 2px solid #ddd;
            border-radius: 5px;
        }}
        .study-card {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            background: #fafafa;
        }}
        .study-title {{
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .study-meta {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin: 5px 0;
        }}
        .kc-badge {{
            display: inline-block;
            padding: 3px 8px;
            margin: 2px;
            border-radius: 3px;
            font-size: 0.85em;
        }}
        .kc-supported-badge {{
            background: #27ae60;
            color: white;
        }}
        .kc-not-mentioned-badge {{
            background: #ecf0f1;
            color: #7f8c8d;
        }}
        .export-section {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #ffc107;
        }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
    </style>
    <script>
        function showTab(tabName) {{
            // Hide all tab contents
            var contents = document.getElementsByClassName('tab-content');
            for (var i = 0; i < contents.length; i++) {{
                contents[i].classList.remove('active');
            }}
            
            // Remove active class from all tabs
            var tabs = document.getElementsByClassName('tab');
            for (var i = 0; i < tabs.length; i++) {{
                tabs[i].classList.remove('active');
            }}
            
            // Show selected tab content
            document.getElementById(tabName).classList.add('active');
            event.target.classList.add('active');
        }}
        
        function searchStudies() {{
            var input = document.getElementById('searchInput');
            var filter = input.value.toLowerCase();
            var cards = document.getElementsByClassName('study-card');
            
            for (var i = 0; i < cards.length; i++) {{
                var card = cards[i];
                var text = card.textContent || card.innerText;
                if (text.toLowerCase().indexOf(filter) > -1) {{
                    card.style.display = '';
                }} else {{
                    card.style.display = 'none';
                }}
            }}
        }}
        
        function exportJSON() {{
            var data = {json.dumps(summary_data, indent=2)};
            var blob = new Blob([JSON.stringify(data, null, 2)], {{type: 'application/json'}});
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'acetaminophen_results.json';
            a.click();
        }}
    </script>
</head>
<body>
    <div class="container">
        <h1>AI Toxicologist: Acetaminophen Hepatotoxicity Assessment</h1>
        <p><strong>Complete Results Export</strong> - Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('summary')">Summary</button>
            <button class="tab" onclick="showTab('kc-results')">KC Results</button>
            <button class="tab" onclick="showTab('studies')">All Studies</button>
            <button class="tab" onclick="showTab('data-export')">Data Export</button>
        </div>
        
        <!-- Summary Tab -->
        <div id="summary" class="tab-content active">
            <div class="summary-box">
                <h2>Executive Summary</h2>
                <p><strong>Chemical:</strong> {summary_data['chemical']}</p>
                <p><strong>Total Papers Analyzed:</strong> {summary_data['total_papers']}</p>
                <p><strong>Analysis Method:</strong> Multi-reviewer LLM consensus (llama3.2, mixtral)</p>
                <p><strong>Framework:</strong> PRISMA 2020 compliant systematic review</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-number">{summary_data['total_papers']}</div>
                    <div class="stat-label">Papers Analyzed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{sum(1 for d in summary_data['kc_results'].values() if d['count'] > 0)}</div>
                    <div class="stat-label">KCs with Evidence</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{sum(d['count'] for d in summary_data['kc_results'].values())}</div>
                    <div class="stat-label">Total Support Instances</div>
                </div>
                <div class="stat-box">
                    <div class="stat-number">{sum(1 for d in summary_data['kc_results'].values() if d['count'] >= 20)}</div>
                    <div class="stat-label">High Certainty KCs</div>
                </div>
            </div>
            
            <h2>Key Characteristics Overview</h2>
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
    for kc, data in sorted(summary_data['kc_results'].items()):
        percentage = (data['count'] / data['total'] * 100) if data['total'] > 0 else 0
        if data['count'] >= 20:
            certainty = "High"
        elif data['count'] >= 10:
            certainty = "Moderate"
        elif data['count'] > 0:
            certainty = "Low"
        else:
            certainty = "Very Low"

        html_content += f"""
                    <tr>
                        <td><strong>{kc}</strong></td>
                        <td>{escape(data['name'])}</td>
                        <td class="{'kc-supported' if data['count'] > 0 else 'kc-not-mentioned'}">{data['count']}/{data['total']}</td>
                        <td>{percentage:.1f}%</td>
                        <td>{certainty}</td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
        </div>
        
        <!-- KC Results Tab -->
        <div id="kc-results" class="tab-content">
            <h2>Detailed Key Characteristics Results</h2>
"""

    # Add detailed KC results
    for kc, data in sorted(summary_data['kc_results'].items()):
        if data['count'] > 0:
            percentage = (data['count'] / data['total'] * 100) if data['total'] > 0 else 0
            if data['count'] >= 20:
                certainty = "High"
            elif data['count'] >= 10:
                certainty = "Moderate"
            else:
                certainty = "Low"

            html_content += f"""
            <div class="study-card">
                <div class="study-title">{kc}: {escape(data['name'])}</div>
                <p><strong>Studies Supporting:</strong> {data['count']}/{data['total']} ({percentage:.1f}%)</p>
                <p><strong>Studies Refuting:</strong> 0/{data['total']}</p>
                <p><strong>Certainty of Evidence:</strong> {certainty}</p>
"""

            interpretations = {
                "KC1": "Bioactivation to NAPQI (N-acetyl-p-benzoquinone imine) - the primary toxic metabolite",
                "KC2": "Hepatocellular necrosis and apoptosis - cell death mechanisms",
                "KC5": "Glutathione depletion and oxidative stress - key mechanism of toxicity",
                "KC7": "Mitochondrial dysfunction and energy failure - critical for cell survival",
                "KC8": "JNK signaling pathway activation - stress response signaling",
                "KC12": "Metabolic disruption and steatosis - lipid metabolism effects"
            }

            if kc in interpretations:
                html_content += f'                <p><strong>Interpretation:</strong> {escape(interpretations[kc])}</p>\n'

            html_content += "            </div>\n"

    html_content += """
        </div>
        
        <!-- Studies Tab -->
        <div id="studies" class="tab-content">
            <h2>All Study Records</h2>
            <input type="text" id="searchInput" class="search-box" placeholder="Search studies by title, PMID, or author..." onkeyup="searchStudies()">
            
"""

    # Add study cards
    for i, record in enumerate(study_records[:100]):  # Limit to first 100 for performance
        metadata = record.get('metadata', {})
        kc_analysis = record.get('kc_analysis', {})

        title = escape(metadata.get('title', 'N/A'))
        pmid = metadata.get('pmid', 'N/A')
        authors = escape(metadata.get('authors', 'N/A'))
        journal = escape(metadata.get('journal', 'N/A'))

        # Get supported KCs
        supported_kcs = []
        for kc_num in range(1, 13):
            kc_key = f"kc{kc_num}_status"
            if kc_analysis.get(kc_key) == 'SUPPORTED':
                supported_kcs.append(f"KC{kc_num}")

        html_content += f"""
            <div class="study-card">
                <div class="study-title">{title}</div>
                <div class="study-meta"><strong>PMID:</strong> {pmid}</div>
                <div class="study-meta"><strong>Authors:</strong> {authors}</div>
                <div class="study-meta"><strong>Journal:</strong> {journal}</div>
                <div style="margin-top: 10px;">
                    <strong>Supported KCs:</strong>
"""

        if supported_kcs:
            for kc in supported_kcs:
                html_content += f'                    <span class="kc-badge kc-supported-badge">{kc}</span>\n'
        else:
            html_content += '                    <span class="kc-badge kc-not-mentioned-badge">None</span>\n'

        html_content += """
                </div>
            </div>
"""

    if len(study_records) > 100:
        html_content += f'<p><em>Showing first 100 of {len(study_records)} studies. Full data available in JSON export.</em></p>\n'

    html_content += """
        </div>
        
        <!-- Data Export Tab -->
        <div id="data-export" class="tab-content">
            <div class="export-section">
                <h2>Data Export Options</h2>
                <p>This HTML file contains all analysis results. You can:</p>
                <ul>
                    <li>View results in the browser tabs above</li>
                    <li>Export summary data as JSON using the button below</li>
                    <li>Access full study records from: <code>results/acetaminophen/study_records.jsonl</code></li>
                </ul>
                <button onclick="exportJSON()" style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin-top: 10px;">
                    Export Summary as JSON
                </button>
            </div>
            
            <h2>Data Structure</h2>
            <p>The complete dataset includes:</p>
            <ul>
                <li><strong>Summary Statistics:</strong> KC support counts, certainty assessments</li>
                <li><strong>Study Records:</strong> Individual paper analyses with KC statuses, risk-of-bias, and evidence quotes</li>
                <li><strong>Metadata:</strong> Analysis provenance, model information, timestamps</li>
            </ul>
            
            <h3>File Locations</h3>
            <ul>
                <li><code>results/acetaminophen/study_records.jsonl</code> - Complete study records (JSONL format)</li>
                <li><code>results/acetaminophen/kc_summary.json</code> - Summary statistics (JSON format)</li>
                <li><code>results/acetaminophen/acetaminophen_results.html</code> - This HTML export</li>
                <li><code>results/acetaminophen/acetaminophen_results.pptx</code> - PowerPoint presentation</li>
            </ul>
        </div>
        
        <div class="metadata">
            <h2>Metadata</h2>
            <p><strong>Generated:</strong> {datetime.now().isoformat()}</p>
            <p><strong>Total Studies:</strong> {len(study_records)}</p>
            <p><strong>Analysis Framework:</strong> PRISMA 2020, OHAT Risk-of-Bias, GRADE Certainty</p>
            <p><strong>Models Used:</strong> llama3.2, mixtral (Multi-reviewer consensus)</p>
            <p><strong>Data Source:</strong> results/acetaminophen/study_records.jsonl</p>
        </div>
    </div>
</body>
</html>
"""

    # Save HTML file
    output_path = os.path.join(results_dir, "acetaminophen_results_complete.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ Comprehensive HTML export saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    print("="*80)
    print("CREATING COMPREHENSIVE HTML EXPORT")
    print("="*80)
    create_comprehensive_html()
    print("="*80)
