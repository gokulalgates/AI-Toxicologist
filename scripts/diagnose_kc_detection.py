"""
Diagnostic script to investigate why KCs are not being detected
"""

import json
import os


def check_study_records():
    """Check what's in the study records"""
    records_file = "results/acetaminophen/study_records.jsonl"

    if not os.path.exists(records_file):
        print(f"❌ File not found: {records_file}")
        return

    records = []
    with open(records_file) as f:
        for line in f:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    pass

    print(f"Total records: {len(records)}")
    print()

    # Check first few records
    print("="*80)
    print("SAMPLE RECORDS ANALYSIS")
    print("="*80)

    for i, record in enumerate(records[:3]):
        print(f"\nRecord {i+1}:")
        print(f"  Title: {record.get('metadata', {}).get('title', 'N/A')[:80]}")
        print(f"  PMID: {record.get('metadata', {}).get('pmid', 'N/A')}")

        kc_analysis = record.get('kc_analysis', {})
        print(f"  KC Analysis keys: {list(kc_analysis.keys())[:10]}")

        # Check KC statuses
        kc1_status = kc_analysis.get('kc1_status', 'MISSING')
        kc2_status = kc_analysis.get('kc2_status', 'MISSING')
        kc5_status = kc_analysis.get('kc5_status', 'MISSING')
        print(f"  KC1 status: {kc1_status}")
        print(f"  KC2 status: {kc2_status}")
        print(f"  KC5 status: {kc5_status}")

        # Check if has multi-reviewer consensus
        if 'multi_reviewer_consensus' in record:
            consensus = record['multi_reviewer_consensus']
            print("  Has multi-reviewer consensus: Yes")
            if 'KC1' in consensus:
                kc1_consensus = consensus['KC1']
                print(f"  KC1 consensus: {kc1_consensus}")
        else:
            print("  Has multi-reviewer consensus: No")

        # Check reasoning
        reasoning = kc_analysis.get('reasoning', 'N/A')
        print(f"  Reasoning length: {len(str(reasoning))} chars")
        print(f"  Reasoning preview: {str(reasoning)[:150]}")

        # Check evidence quotes
        evidence_quotes = kc_analysis.get('evidence_quotes', {})
        print(f"  Evidence quotes: {len(evidence_quotes)} KCs have quotes")
        if evidence_quotes:
            for kc, quotes in list(evidence_quotes.items())[:2]:
                print(f"    {kc}: {len(quotes)} quotes")

    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)

    # Count statuses
    status_counts = {f"KC{i}": {"SUPPORTED": 0, "ASSOCIATED": 0, "CAUSALLY_LINKED": 0, "NOT_MENTIONED": 0}
                     for i in range(1, 13)}

    for record in records:
        kc_analysis = record.get('kc_analysis', {})
        for i in range(1, 13):
            status = kc_analysis.get(f'kc{i}_status', 'NOT_MENTIONED')
            status_counts[f"KC{i}"][status] = status_counts[f"KC{i}"].get(status, 0) + 1

    print("\nKC Status Distribution:")
    for kc in ["KC1", "KC2", "KC5", "KC7", "KC8", "KC12"]:
        counts = status_counts[kc]
        total = sum(counts.values())
        print(f"  {kc}:")
        print(f"    SUPPORTED: {counts['SUPPORTED']}/{total} ({counts['SUPPORTED']/total*100:.1f}%)")
        print(f"    ASSOCIATED: {counts['ASSOCIATED']}/{total} ({counts['ASSOCIATED']/total*100:.1f}%)")
        print(f"    CAUSALLY_LINKED: {counts['CAUSALLY_LINKED']}/{total} ({counts['CAUSALLY_LINKED']/total*100:.1f}%)")
        print(f"    NOT_MENTIONED: {counts['NOT_MENTIONED']}/{total} ({counts['NOT_MENTIONED']/total*100:.1f}%)")

    # Check if models are actually analyzing
    print("\n" + "="*80)
    print("MODEL ANALYSIS CHECK")
    print("="*80)

    records_with_consensus = [r for r in records if 'multi_reviewer_consensus' in r]
    print(f"Records with multi-reviewer consensus: {len(records_with_consensus)}/{len(records)}")

    if records_with_consensus:
        first = records_with_consensus[0]
        consensus = first['multi_reviewer_consensus']
        reviewer_analyses = first.get('provenance', {}).get('models', [])
        print(f"Models used: {reviewer_analyses}")

        # Check what individual models said
        if 'reviewer_analyses' in first:
            print("\nIndividual model assessments (if available in record):")
            # This might not be in the saved record, but check anyway

if __name__ == "__main__":
    check_study_records()
