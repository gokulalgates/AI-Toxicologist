"""
Compare AI analysis results with gold standard from NIHMS paper
"""

import json
import os
from typing import Dict, List

# Gold Standard from Rusyn et al. 2021 (NIHMS-1779672)
GOLD_STANDARD_ACETAMINOPHEN = {
    "KC1": "SUPPORTED",  # Bioactivation to NAPQI
    "KC2": "SUPPORTED",  # Cell death (apoptosis/necrosis)
    "KC3": "SUPPORTED",  # Affects regeneration
    "KC4": "SUPPORTED",  # Disrupts transport
    "KC5": "SUPPORTED",  # Oxidative stress
    "KC6": "SUPPORTED",  # Immune response (neutrophils)
    "KC7": "SUPPORTED",  # Mitochondrial dysfunction
    "KC8": "SUPPORTED",  # JNK activation
    "KC9": "NOT_MENTIONED",
    "KC10": "NOT_MENTIONED",
    "KC11": "NOT_MENTIONED",
    "KC12": "SUPPORTED",  # Metabolism disruption (steatosis mentioned)
}

def load_ai_results(results_dir: str = "results/acetaminophen") -> List[Dict]:
    """Load AI analysis results from study_records.jsonl"""
    study_records_file = os.path.join(results_dir, "study_records.jsonl")

    if not os.path.exists(study_records_file):
        print(f"❌ Results file not found: {study_records_file}")
        return []

    records = []
    with open(study_records_file) as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    print(f"⚠️  Warning: Could not parse line {line_num}: {e}")
                    continue

    return records

def aggregate_ai_kc_assessments(records: List[Dict]) -> Dict[str, Dict[str, int]]:
    """Aggregate KC assessments across all studies"""
    kc_counts = {f"KC{i}": {
        "SUPPORTED": 0,
        "ASSOCIATED": 0,
        "CAUSALLY_LINKED": 0,
        "REFUTED": 0,
        "NOT_MENTIONED": 0
    } for i in range(1, 13)}

    for record in records:
        kc_analysis = record.get("kc_analysis", {})
        for i in range(1, 13):
            kc_key = f"kc{i}_status"
            status = kc_analysis.get(kc_key, "NOT_MENTIONED")
            kc_name = f"KC{i}"
            if kc_name in kc_counts:
                kc_counts[kc_name][status] = kc_counts[kc_name].get(status, 0) + 1

    return kc_counts

def determine_ai_consensus(kc_counts: Dict[str, Dict[str, int]]) -> Dict[str, str]:
    """Determine AI consensus (KC is supported if >50% of studies support it)"""
    ai_consensus = {}

    for kc, counts in kc_counts.items():
        total = sum(counts.values())
        if total > 0:
            supported_pct = (counts["SUPPORTED"] + counts["ASSOCIATED"] + counts["CAUSALLY_LINKED"]) / total
            if supported_pct > 0.5:
                ai_consensus[kc] = "SUPPORTED"
            elif counts["REFUTED"] > total * 0.5:
                ai_consensus[kc] = "REFUTED"
            else:
                ai_consensus[kc] = "NOT_MENTIONED"
        else:
            ai_consensus[kc] = "NOT_MENTIONED"

    return ai_consensus

def calculate_metrics(gold_standard: Dict[str, str], ai_consensus: Dict[str, str]) -> Dict:
    """Calculate precision, recall, F1, accuracy per KC"""
    metrics = {}

    for kc in [f"KC{i}" for i in range(1, 13)]:
        gold_status = gold_standard.get(kc, "NOT_MENTIONED")
        ai_status = ai_consensus.get(kc, "NOT_MENTIONED")

        # Convert to binary (SUPPORTED = 1, others = 0)
        gold_binary = 1 if gold_status == "SUPPORTED" else 0
        ai_binary = 1 if ai_status == "SUPPORTED" else 0

        # Calculate TP, FP, FN, TN
        tp = 1 if (gold_binary == 1 and ai_binary == 1) else 0
        fp = 1 if (gold_binary == 0 and ai_binary == 1) else 0
        fn = 1 if (gold_binary == 1 and ai_binary == 0) else 0
        tn = 1 if (gold_binary == 0 and ai_binary == 0) else 0

        # Calculate metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0.0

        metrics[kc] = {
            "gold_standard": gold_status,
            "ai_consensus": ai_status,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "accuracy": accuracy
        }

    return metrics

def print_comparison_report(gold_standard: Dict[str, str], ai_consensus: Dict[str, str],
                           kc_counts: Dict[str, Dict[str, int]], metrics: Dict):
    """Print detailed comparison report"""
    print("="*80)
    print("COMPARISON: AI RESULTS vs GOLD STANDARD (Rusyn et al. 2021)")
    print("="*80)
    print()

    print("GOLD STANDARD (Expert Consensus from NIHMS Paper):")
    print("-" * 80)
    for kc in sorted(gold_standard.keys()):
        status = gold_standard[kc]
        icon = "✅" if status == "SUPPORTED" else "⚪"
        print(f"  {icon} {kc}: {status}")
    print()

    print("AI CONSENSUS (Aggregated across studies):")
    print("-" * 80)
    for kc in sorted(ai_consensus.keys()):
        status = ai_consensus[kc]
        icon = "✅" if status == "SUPPORTED" else "⚪"
        print(f"  {icon} {kc}: {status}")
    print()

    print("DETAILED AI RESULTS (Status counts across studies):")
    print("-" * 80)
    for kc in sorted(kc_counts.keys()):
        counts = kc_counts[kc]
        total = sum(counts.values())
        print(f"  {kc}:")
        print(f"    SUPPORTED: {counts['SUPPORTED']}/{total} ({counts['SUPPORTED']/total*100:.1f}%)")
        print(f"    ASSOCIATED: {counts['ASSOCIATED']}/{total} ({counts['ASSOCIATED']/total*100:.1f}%)")
        print(f"    CAUSALLY_LINKED: {counts['CAUSALLY_LINKED']}/{total} ({counts['CAUSALLY_LINKED']/total*100:.1f}%)")
        print(f"    REFUTED: {counts['REFUTED']}/{total} ({counts['REFUTED']/total*100:.1f}%)")
        print(f"    NOT_MENTIONED: {counts['NOT_MENTIONED']}/{total} ({counts['NOT_MENTIONED']/total*100:.1f}%)")
    print()

    print("PER-KC PERFORMANCE METRICS:")
    print("-" * 80)
    print(f"{'KC':<6} {'Gold':<15} {'AI':<15} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Accuracy':<12}")
    print("-" * 80)

    for kc in sorted(metrics.keys()):
        m = metrics[kc]
        print(f"{kc:<6} {m['gold_standard']:<15} {m['ai_consensus']:<15} "
              f"{m['precision']:<12.3f} {m['recall']:<12.3f} {m['f1_score']:<12.3f} {m['accuracy']:<12.3f}")

    print()
    print("OVERALL PERFORMANCE:")
    print("-" * 80)
    avg_precision = sum(m['precision'] for m in metrics.values()) / len(metrics)
    avg_recall = sum(m['recall'] for m in metrics.values()) / len(metrics)
    avg_f1 = sum(m['f1_score'] for m in metrics.values()) / len(metrics)
    avg_accuracy = sum(m['accuracy'] for m in metrics.values()) / len(metrics)

    print(f"  Average Precision: {avg_precision:.3f}")
    print(f"  Average Recall: {avg_recall:.3f}")
    print(f"  Average F1 Score: {avg_f1:.3f}")
    print(f"  Average Accuracy: {avg_accuracy:.3f}")
    print()

    # Identify issues
    print("ISSUES IDENTIFIED:")
    print("-" * 80)
    false_negatives = [kc for kc in sorted(metrics.keys())
                      if metrics[kc]['gold_standard'] == "SUPPORTED"
                      and metrics[kc]['ai_consensus'] != "SUPPORTED"]
    false_positives = [kc for kc in sorted(metrics.keys())
                      if metrics[kc]['gold_standard'] != "SUPPORTED"
                      and metrics[kc]['ai_consensus'] == "SUPPORTED"]

    if false_negatives:
        print(f"  ❌ False Negatives (Missed KCs): {', '.join(false_negatives)}")
        print("     These KCs should be SUPPORTED but AI marked as NOT_MENTIONED")
    else:
        print("  ✅ No False Negatives")

    if false_positives:
        print(f"  ⚠️  False Positives (Over-predicted): {', '.join(false_positives)}")
        print("     These KCs are marked SUPPORTED by AI but not in gold standard")
    else:
        print("  ✅ No False Positives")

    print()
    print("="*80)

def main():
    """Main comparison function"""
    print("Loading AI results...")
    records = load_ai_results()

    if not records:
        print("❌ No AI results found. Please run analysis first.")
        return

    print(f"✅ Loaded {len(records)} study records")
    print()

    # Aggregate KC assessments
    kc_counts = aggregate_ai_kc_assessments(records)

    # Determine consensus
    ai_consensus = determine_ai_consensus(kc_counts)

    # Calculate metrics
    metrics = calculate_metrics(GOLD_STANDARD_ACETAMINOPHEN, ai_consensus)

    # Print report
    print_comparison_report(
        GOLD_STANDARD_ACETAMINOPHEN,
        ai_consensus,
        kc_counts,
        metrics
    )

    # Save report
    report = {
        "gold_standard": GOLD_STANDARD_ACETAMINOPHEN,
        "ai_consensus": ai_consensus,
        "kc_counts": {kc: dict(counts) for kc, counts in kc_counts.items()},
        "metrics": {kc: dict(m) for kc, m in metrics.items()},
        "overall_metrics": {
            "avg_precision": sum(m['precision'] for m in metrics.values()) / len(metrics),
            "avg_recall": sum(m['recall'] for m in metrics.values()) / len(metrics),
            "avg_f1": sum(m['f1_score'] for m in metrics.values()) / len(metrics),
            "avg_accuracy": sum(m['accuracy'] for m in metrics.values()) / len(metrics)
        }
    }

    with open("comparison_report_acetaminophen.json", 'w') as f:
        json.dump(report, f, indent=2)

    print("✅ Comparison report saved to: comparison_report_acetaminophen.json")

if __name__ == "__main__":
    main()
