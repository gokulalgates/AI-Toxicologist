"""
Run validation using the NIHMS paper as gold standard

This script:
1. Extracts expert assessments from the NIHMS paper (Rusyn et al. 2021)
2. Runs AI system on the same chemicals
3. Compares AI vs gold standard
"""

import json
from typing import Dict, List

from app import analyze_chemical
from config import get_config
from validation import (
    GoldStandardRecord,
    calculate_kc_extraction_metrics,
)


def create_gold_standard_from_paper() -> List[Dict]:
    """
    Create gold standard from the NIHMS paper
    
    The paper explicitly states: "Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)"
    """
    # Based on the paper: Acetaminophen exhibits KCs 1-8 and 12
    acetaminophen_kcs = {
        "KC1": "SUPPORTED",  # Bioactivation to NAPQI
        "KC2": "SUPPORTED",  # Cell death (apoptosis/necrosis)
        "KC3": "SUPPORTED",  # Affects regeneration
        "KC4": "SUPPORTED",  # Disrupts transport
        "KC5": "SUPPORTED",  # Oxidative stress
        "KC6": "SUPPORTED",  # Immune response (neutrophils)
        "KC7": "SUPPORTED",  # Mitochondrial dysfunction
        "KC8": "SUPPORTED",  # JNK activation
        "KC9": "NOT_MENTIONED",  # Not explicitly mentioned
        "KC10": "NOT_MENTIONED",  # Not explicitly mentioned
        "KC11": "NOT_MENTIONED",  # Not explicitly mentioned
        "KC12": "SUPPORTED",  # Metabolism disruption (steatosis mentioned)
    }

    gold_standard = [
        {
            "pmid": "nihms-1779672",
            "chemical_name": "Acetaminophen",
            "is_relevant": True,
            "kc_assessments": acetaminophen_kcs,
            "rob_overall": "Low",
            "rob_domains": {
                "Selection Bias": "Low",
                "Performance Bias": "Low",
                "Detection Bias": "Low",
                "Reporting Bias": "Low"
            },
            "certainty_assessments": {
                kc: "Moderate" if status == "SUPPORTED" else "Very Low"
                for kc, status in acetaminophen_kcs.items()
            },
            "reviewer_id": "expert_consensus_rusyn_et_al_2021",
            "review_date": "2021-12-01",
            "notes": "Expert consensus from Rusyn et al. Hepatology 2021. Paper explicitly states: 'Acetaminophen exhibits many KCs of hepatotoxicants (KCs 1–8 and 12)'"
        }
    ]

    return gold_standard


def run_ai_analysis(chemical_name: str, model_names: List[str] = None) -> Dict:
    """Run AI analysis and extract results in format for comparison"""
    print(f"\n{'='*80}")
    print(f"Running AI analysis for: {chemical_name}")
    print(f"{'='*80}\n")

    # Check full-text retrieval configuration
    config = get_config()
    if not config.search.enable_fulltext_retrieval:
        print("   ℹ️  Full-text retrieval is disabled in config.")
        print("   💡 Analysis will use abstracts only (sufficient for KC extraction).")
        print("   💡 To enable full-text retrieval, set config.search.enable_fulltext_retrieval = True\n")

    try:
        # Run analysis - this will save results to results/{chemical_name}/study_records.jsonl
        # Note: Full-text retrieval respects config.search.enable_fulltext_retrieval
        results = analyze_chemical(
            chemical_name=chemical_name,
            model_names=model_names or ["llama3.2", "mixtral"],
            enable_rob=True,
            enable_certainty=True
        )

        # Check if results were saved
        import os
        results_file = f"results/{chemical_name.replace(' ', '_')}/study_records.jsonl"
        if os.path.exists(results_file):
            print("✅ AI analysis complete and results saved")
            return {"status": "success", "chemical": chemical_name}
        else:
            print("⚠️  Analysis completed but results file not found")
            return {"status": "warning", "chemical": chemical_name, "message": "Results file not created"}

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return {"status": "interrupted", "chemical": chemical_name}
    except Exception as e:
        print(f"❌ Error running AI analysis: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def convert_ai_results_to_comparison_format(chemical_name: str, results_dir: str = "results") -> List[Dict]:
    """
    Convert AI results to format needed for comparison
    
    This would load the actual results from the analysis output files
    """
    import os

    # Find the most recent results for this chemical (case-insensitive)
    chem_dir_base = chemical_name.replace(" ", "_")
    chem_dir = os.path.join(results_dir, chem_dir_base)

    # Try case-insensitive search if exact match not found
    if not os.path.exists(chem_dir) and os.path.exists(results_dir):
        # List all directories and find case-insensitive match
        for dir_name in os.listdir(results_dir):
            if dir_name.lower() == chem_dir_base.lower():
                chem_dir = os.path.join(results_dir, dir_name)
                print(f"Found results directory (case-insensitive): {chem_dir}")
                break

    if not os.path.exists(chem_dir):
        print(f"Warning: Results directory not found: {chem_dir}")
        return []

    # Load study records if available
    study_records_file = os.path.join(chem_dir, "study_records.jsonl")
    ai_results = []

    if os.path.exists(study_records_file):
        with open(study_records_file) as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        record = json.loads(line)
                        # Convert to comparison format
                        result = {
                            "pmid": record.get("metadata", {}).get("pmid", "unknown"),
                            "is_relevant": True,  # Already passed relevance screening
                            "kc_assessments": {}
                        }

                        # Extract KC statuses
                        kc_analysis = record.get("kc_analysis", {})
                        if not kc_analysis:
                            print(f"   ⚠️  Warning: Record {line_num} has empty kc_analysis")
                            continue

                        found_statuses = 0
                        for i in range(1, 13):
                            kc_key = f"kc{i}_status"
                            kc_name = f"KC{i}"
                            status = kc_analysis.get(kc_key, "NOT_MENTIONED")
                            result["kc_assessments"][kc_name] = status
                            if status != "NOT_MENTIONED":
                                found_statuses += 1

                        # Debug: Show first record's statuses
                        if line_num == 1:
                            print(f"   📋 Sample record (PMID {result['pmid']}): Found {found_statuses} non-NOT_MENTIONED KCs")
                            if found_statuses == 0:
                                print("   ⚠️  Warning: First record has all NOT_MENTIONED - this may indicate a data issue")
                                print("   💡 This could mean results were saved before the consolidation fix.")
                                print("   💡 Try re-running the analysis with the latest code.")

                        ai_results.append(result)
                    except json.JSONDecodeError as e:
                        print(f"   ⚠️  Warning: Could not parse JSON on line {line_num}: {e}")
                        continue

    return ai_results


def main():
    """Main validation workflow"""
    print("="*80)
    print("VALIDATION: AI System vs Expert Gold Standard (NIHMS Paper)")
    print("="*80)

    # Check configuration
    config = get_config()
    print("\n⚙️  Configuration:")
    print(f"   • Full-text retrieval: {'Enabled' if config.search.enable_fulltext_retrieval else 'Disabled'}")
    print(f"   • Skip on error: {'Yes' if config.search.skip_fulltext_on_error else 'No'}")
    if not config.search.enable_fulltext_retrieval:
        print("   💡 Note: Full-text retrieval is disabled. Analysis will use abstracts only.")
        print("   💡 This is fine for KC extraction, but RoB assessment may be limited.\n")

    # Step 1: Create gold standard from paper
    print("\n📚 Step 1: Extracting gold standard from NIHMS paper...")
    gold_standard = create_gold_standard_from_paper()

    # Save gold standard
    with open("gold_standard_nihms.json", 'w') as f:
        json.dump(gold_standard, f, indent=2)
    print("✅ Gold standard saved: gold_standard_nihms.json")
    print(f"   Chemicals: {[r['chemical_name'] for r in gold_standard]}")

    # Step 2: Run AI analysis (or load existing results)
    print("\n🤖 Step 2: Running AI analysis...")
    chemical_name = "Acetaminophen"

    # Check if results already exist (case-insensitive)
    import os
    results_dir_base = chemical_name.replace(' ', '_')
    results_dir = f"results/{results_dir_base}"

    # Try case-insensitive search
    if not os.path.exists(f"{results_dir}/study_records.jsonl") and os.path.exists("results"):
        for dir_name in os.listdir("results"):
            if dir_name.lower() == results_dir_base.lower():
                results_dir = f"results/{dir_name}"
                break

    results_exist = os.path.exists(f"{results_dir}/study_records.jsonl")

    # Check if existing results are valid (have at least some SUPPORTED KCs)
    if results_exist:
        # Quick check: are all results "NOT_MENTIONED"?
        try:
            with open(f"{results_dir}/study_records.jsonl") as f:
                first_line = f.readline()
                if first_line.strip():
                    record = json.loads(first_line)
                    kc_analysis = record.get("kc_analysis", {})
                    # Check if all statuses are NOT_MENTIONED
                    all_not_mentioned = all(
                        kc_analysis.get(f"kc{i}_status", "NOT_MENTIONED") == "NOT_MENTIONED"
                        for i in range(1, 13)
                    )
                    if all_not_mentioned:
                        print("   ⚠️  Existing results appear invalid (all KCs are NOT_MENTIONED).")
                        print("   💡 This likely means results were generated before the LangChain fix.")
                        print("   🔄 Re-running analysis with fixed code...")
                        results_exist = False  # Force re-run
        except Exception as e:
            print(f"   ⚠️  Could not validate existing results: {e}")
            print("   🔄 Re-running analysis...")
            results_exist = False

    if not results_exist:
        print("   ⚠️  No existing results found.")
        print("   🔄 Running new AI analysis now...")
        print("   ⏱️  This will take 30-60 minutes. Please be patient...")
        print("   💡 Tip: You can run this in background using:")
        print("      nohup python run_analysis_bg.py > acetaminophen_analysis.log 2>&1 &")
        print("")

        # Run analysis
        try:
            ai_result = run_ai_analysis(chemical_name, model_names=["llama3.2", "mixtral"])
            if ai_result["status"] == "error":
                print(f"   ❌ Analysis failed: {ai_result.get('error', 'Unknown error')}")
                print("   Please check the error above and try again.")
                return
            print("   ✅ AI analysis complete!")
        except KeyboardInterrupt:
            print("\n   ⚠️  Analysis interrupted by user.")
            print("   Partial results may be available. You can re-run this script to continue.")
            return
        except Exception as e:
            print(f"   ❌ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            return
    else:
        print("   ✅ Using existing results...")

    # Step 3: Load AI results
    print("\n📊 Step 3: Loading AI results...")
    ai_results = convert_ai_results_to_comparison_format(chemical_name)

    if not ai_results:
        print("   ⚠️  No AI results found. Please run analysis first:")
        print(f"   python app.py  # Then analyze {chemical_name}")
        return

    print(f"   Found {len(ai_results)} AI-assessed studies")

    # Step 4: Compare
    print("\n🔍 Step 4: Comparing AI vs Gold Standard...")

    # For this validation, we're comparing:
    # - Gold standard: Expert consensus from paper (1 record for Acetaminophen)
    # - AI results: Multiple studies analyzed by AI

    # We need to aggregate AI results across studies for comparison
    # Since gold standard is at the chemical level, we'll compare:
    # - Which KCs does AI identify as supported across studies?

    # Aggregate AI KC assessments
    ai_kc_counts = {f"KC{i}": {"SUPPORTED": 0, "ASSOCIATED": 0, "CAUSALLY_LINKED": 0, "NOT_MENTIONED": 0, "REFUTED": 0}
                    for i in range(1, 13)}

    for result in ai_results:
        for kc, status in result["kc_assessments"].items():
            if kc in ai_kc_counts:
                ai_kc_counts[kc][status] = ai_kc_counts[kc].get(status, 0) + 1

    # Debug: Show counts for first few KCs
    print("\n   📊 KC Status Counts (sample):")
    for kc in ["KC1", "KC2", "KC3"]:
        counts = ai_kc_counts[kc]
        total = sum(counts.values())
        if total > 0:
            print(f"      {kc}: SUPPORTED={counts['SUPPORTED']}, ASSOCIATED={counts['ASSOCIATED']}, "
                  f"CAUSALLY_LINKED={counts['CAUSALLY_LINKED']}, NOT_MENTIONED={counts['NOT_MENTIONED']} (total={total})")

    # Determine AI consensus (KC is supported if >50% of studies support it)
    ai_consensus = {}
    for kc, counts in ai_kc_counts.items():
        total = sum(counts.values())
        if total > 0:
            supported_pct = (counts["SUPPORTED"] + counts["ASSOCIATED"] + counts["CAUSALLY_LINKED"]) / total
            if supported_pct > 0.5:
                ai_consensus[kc] = "SUPPORTED"
            else:
                ai_consensus[kc] = "NOT_MENTIONED"
        else:
            ai_consensus[kc] = "NOT_MENTIONED"

    # Compare with gold standard
    gold_kcs = gold_standard[0]["kc_assessments"]

    print("\n" + "="*80)
    print("COMPARISON RESULTS")
    print("="*80)

    print("\nGold Standard (Expert Consensus):")
    for kc in sorted(gold_kcs.keys()):
        print(f"  {kc}: {gold_kcs[kc]}")

    print("\nAI Consensus (across studies):")
    for kc in sorted(ai_consensus.keys()):
        print(f"  {kc}: {ai_consensus[kc]}")

    # Calculate metrics
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)

    # Convert to format for metrics calculation
    gold_record = GoldStandardRecord(**gold_standard[0])

    # Create AI prediction dict
    ai_predictions = {"nihms-1779672": ai_consensus}

    # Calculate metrics for each KC
    metrics_by_kc = {}
    for kc in [f"KC{i}" for i in range(1, 13)]:
        metrics = calculate_kc_extraction_metrics(
            [gold_record],
            ai_predictions,
            kc
        )
        metrics_by_kc[kc] = {
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "accuracy": metrics.accuracy
        }

    # Print summary
    print("\nPer-KC Metrics:")
    for kc, metrics in sorted(metrics_by_kc.items()):
        print(f"  {kc}: Precision={metrics['precision']:.3f}, Recall={metrics['recall']:.3f}, "
              f"F1={metrics['f1_score']:.3f}, Accuracy={metrics['accuracy']:.3f}")

    # Overall summary
    avg_precision = sum(m["precision"] for m in metrics_by_kc.values()) / len(metrics_by_kc)
    avg_recall = sum(m["recall"] for m in metrics_by_kc.values()) / len(metrics_by_kc)
    avg_f1 = sum(m["f1_score"] for m in metrics_by_kc.values()) / len(metrics_by_kc)

    print("\nOverall Average:")
    print(f"  Precision: {avg_precision:.3f}")
    print(f"  Recall: {avg_recall:.3f}")
    print(f"  F1 Score: {avg_f1:.3f}")

    # Save comparison report
    report = {
        "gold_standard": gold_standard,
        "ai_consensus": ai_consensus,
        "metrics_by_kc": metrics_by_kc,
        "overall_metrics": {
            "avg_precision": avg_precision,
            "avg_recall": avg_recall,
            "avg_f1": avg_f1
        }
    }

    with open("validation_report_nihms.json", 'w') as f:
        json.dump(report, f, indent=2)

    print("\n✅ Validation report saved: validation_report_nihms.json")
    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
