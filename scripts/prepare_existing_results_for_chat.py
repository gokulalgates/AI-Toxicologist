"""
Convert existing study_records.jsonl to abstracts_for_chat.json
so users can reload and chat with previous analyses
"""

import json
import os
from datetime import datetime


def convert_study_records_to_abstracts(chemical_name):
    """Convert study_records.jsonl to abstracts_for_chat.json"""
    results_dir = f"results/{chemical_name.replace(' ', '_')}"
    records_file = os.path.join(results_dir, "study_records.jsonl")
    abstracts_file = os.path.join(results_dir, "abstracts_for_chat.json")

    if not os.path.exists(records_file):
        print(f"❌ Records file not found: {records_file}")
        return False

    abstracts = []
    with open(records_file, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    record = json.loads(line)
                    metadata = record.get('metadata', {})

                    # Extract abstract data
                    abstract_data = {
                        "pmid": metadata.get('pmid', 'unknown'),
                        "title": metadata.get('title', ''),
                        "abstract": metadata.get('abstract', ''),
                        "authors": metadata.get('authors', ''),
                        "journal": metadata.get('journal', ''),
                        "year": metadata.get('year', ''),
                        "fulltext": record.get('fulltext', '')  # If available
                    }

                    # Only add if we have at least title or abstract
                    if abstract_data.get('title') or abstract_data.get('abstract'):
                        abstracts.append(abstract_data)
                except Exception as e:
                    print(f"Warning: Could not parse record: {e}")
                    continue

    if len(abstracts) == 0:
        print(f"❌ No abstracts found in {records_file}")
        return False

    # Save abstracts for chat
    chat_data = {
        "chemical_name": chemical_name,
        "abstracts": abstracts,
        "saved_at": datetime.now().isoformat(),
        "num_abstracts": len(abstracts),
        "converted_from": "study_records.jsonl"
    }

    with open(abstracts_file, 'w', encoding='utf-8') as f:
        json.dump(chat_data, f, indent=2, ensure_ascii=False)

    print(f"✅ Converted {len(abstracts)} abstracts for {chemical_name}")
    print(f"   Saved to: {abstracts_file}")
    return True

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Convert specific chemical
        chemical_name = sys.argv[1]
        convert_study_records_to_abstracts(chemical_name)
    else:
        # Convert all available chemicals
        results_base = "results"
        if not os.path.exists(results_base):
            print(f"❌ Results directory not found: {results_base}")
            exit(1)

        print("="*80)
        print("CONVERTING EXISTING RESULTS FOR CHAT")
        print("="*80)

        converted = 0
        for chemical_dir in os.listdir(results_base):
            chemical_path = os.path.join(results_base, chemical_dir)
            if os.path.isdir(chemical_path):
                records_file = os.path.join(chemical_path, "study_records.jsonl")
                if os.path.exists(records_file):
                    chemical_name = chemical_dir.replace('_', ' ')
                    if convert_study_records_to_abstracts(chemical_name):
                        converted += 1

        print("\n" + "="*80)
        print(f"✅ Converted {converted} analysis results for chat")
        print("="*80)
        print("\nYou can now reload these analyses in the web interface!")
