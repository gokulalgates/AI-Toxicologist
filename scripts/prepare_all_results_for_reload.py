"""
Prepare existing analysis results for full reload (all outputs, not just chat)
"""

import json
import os
from datetime import datetime

import pandas as pd


def prepare_results_for_reload(chemical_name):
    """Create analysis_results.json from existing files"""
    results_dir = f"results/{chemical_name.replace(' ', '_')}"

    if not os.path.exists(results_dir):
        print(f"❌ Results directory not found: {results_dir}")
        return False

    # Check for required files
    records_file = os.path.join(results_dir, "study_records.jsonl")
    plots_dir = os.path.join(results_dir, "plots")

    if not os.path.exists(records_file):
        print(f"❌ study_records.jsonl not found: {records_file}")
        return False

    # Load study records to get summary info
    abstracts = []
    rob_data = []
    with open(records_file, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    metadata = record.get('metadata', {})

                    abstract_data = {
                        "pmid": metadata.get('pmid', 'unknown'),
                        "title": metadata.get('title', ''),
                        "abstract": metadata.get('abstract', ''),
                        "authors": metadata.get('authors', ''),
                        "journal": metadata.get('journal', ''),
                        "year": metadata.get('year', ''),
                        "fulltext": record.get('fulltext', '')
                    }

                    if abstract_data.get('title') or abstract_data.get('abstract'):
                        abstracts.append(abstract_data)

                    # Extract RoB data
                    rob = record.get('risk_of_bias', {})
                    if rob:
                        rob_data.append({
                            "Study #": len(rob_data) + 1,
                            "PMID": metadata.get('pmid', 'unknown'),
                            "Title": metadata.get('title', '')[:80] + "..." if len(metadata.get('title', '')) > 80 else metadata.get('title', ''),
                            "Overall Judgment": rob.get('overall_judgment', 'Unknown'),
                            "Full-text": "Yes" if record.get('fulltext') else "No"
                        })
                except Exception:
                    continue

    # Find plot files (use relative paths from results_dir)
    saved_plots = {}
    if os.path.exists(plots_dir):
        plot_files = sorted(os.listdir(plots_dir), reverse=True)
        for filename in plot_files:
            if filename.endswith('.png'):
                # Use relative path from results_dir (e.g., "plots/filename.png")
                relative_path = os.path.join("plots", filename).replace("\\", "/")  # Normalize path separators
                filename_lower = filename.lower()
                if 'heatmap' in filename_lower and 'evidence' in filename_lower and 'heatmap' not in saved_plots:
                    saved_plots['heatmap'] = {'png': relative_path}
                elif ('network' in filename_lower or 'causal' in filename_lower) and 'network' not in saved_plots:
                    saved_plots['network'] = {'png': relative_path}
                elif 'prisma' in filename_lower and 'prisma' not in saved_plots:
                    saved_plots['prisma'] = {'png': relative_path}
                elif 'rob' in filename_lower and 'heatmap' in filename_lower and 'rob_heatmap' not in saved_plots:
                    saved_plots['rob_heatmap'] = {'png': relative_path}
                elif 'rob' in filename_lower and 'summary' in filename_lower and 'rob_summary' not in saved_plots:
                    saved_plots['rob_summary'] = {'png': relative_path}

    # Generate summary text (basic)
    num_abstracts = len(abstracts)
    summary_text = f"""Chemical Analysis Summary
{'='*60}
Input Name: {chemical_name}
Total Papers Analyzed: {num_abstracts}

Results saved to: {results_dir}/
"""

    # Save abstracts for chat (if not already saved)
    abstracts_file = os.path.join(results_dir, "abstracts_for_chat.json")
    if not os.path.exists(abstracts_file):
        with open(abstracts_file, 'w', encoding='utf-8') as f:
            json.dump({
                "chemical_name": chemical_name,
                "abstracts": abstracts,
                "saved_at": datetime.now().isoformat(),
                "num_abstracts": len(abstracts)
            }, f, indent=2, ensure_ascii=False)
        print("✅ Created abstracts_for_chat.json")

    # Save RoB table if available
    rob_table_file = None
    if rob_data:
        rob_table_file = os.path.join(results_dir, "rob_table.json")
        try:
            rob_df = pd.DataFrame(rob_data)
            rob_df.to_json(rob_table_file, orient='records', indent=2)
            print(f"✅ Created rob_table.json with {len(rob_data)} records")
        except Exception as e:
            print(f"⚠️  Could not create rob_table.json: {e}")

    # Try to load a more complete summary from study records if available
    # Look for the most recent provenance file to get better summary
    try:
        provenance_files = [f for f in os.listdir(results_dir) if f.startswith('provenance_') and f.endswith('.json')]
        if provenance_files:
            # Use most recent
            latest_prov = sorted(provenance_files, reverse=True)[0]
            prov_path = os.path.join(results_dir, latest_prov)
            with open(prov_path) as f:
                prov_data = json.load(f)
                # Try to extract summary if available
                if 'summary' in prov_data:
                    summary_text = prov_data['summary']
    except:
        pass  # Keep basic summary if can't load

    # Save analysis results
    results_file = os.path.join(results_dir, "analysis_results.json")
    results_data = {
        "chemical_name": chemical_name,
        "saved_at": datetime.now().isoformat(),
        "num_abstracts": num_abstracts,
        "summary_text": summary_text,
        "evidence_profiles": "",  # Would need to regenerate
        "saved_plots": saved_plots,
        "rob_table_file": "rob_table.json" if rob_table_file and os.path.exists(rob_table_file) else None
    }

    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Created analysis_results.json for {chemical_name}")
    print(f"   - {num_abstracts} abstracts")
    print(f"   - {len(saved_plots)} plot files found")
    print(f"   - {'RoB table' if rob_table_file else 'No RoB table'}")

    return True

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        chemical_name = sys.argv[1]
        prepare_results_for_reload(chemical_name)
    else:
        # Prepare all available chemicals
        results_base = "results"
        if not os.path.exists(results_base):
            print(f"❌ Results directory not found: {results_base}")
            exit(1)

        print("="*80)
        print("PREPARING ALL RESULTS FOR RELOAD")
        print("="*80)

        prepared = 0
        for chemical_dir in os.listdir(results_base):
            chemical_path = os.path.join(results_base, chemical_dir)
            if os.path.isdir(chemical_path):
                records_file = os.path.join(chemical_path, "study_records.jsonl")
                if os.path.exists(records_file):
                    chemical_name = chemical_dir.replace('_', ' ')
                    if prepare_results_for_reload(chemical_name):
                        prepared += 1
                    print()

        print("="*80)
        print(f"✅ Prepared {prepared} analysis results for reload")
        print("="*80)
        print("\nYou can now load these analyses in the web interface!")
