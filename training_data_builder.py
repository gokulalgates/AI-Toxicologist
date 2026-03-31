"""
Training Data Builder for DSPy Prompt Optimization.

Builds and manages the training dataset used to optimize KC classification prompts.
Three data sources, in priority order:
  1. Manually curated examples in training_data.json
  2. Gold standard file (gold_standard_nihms.json) — fetches abstract from PubMed
  3. Past analysis results saved in results/ directory

Run directly to build/refresh the training dataset:
    python training_data_builder.py
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TRAINING_DATA_PATH = Path("training_data.json")
GOLD_STANDARD_PATH = Path("gold_standard_nihms.json")
RESULTS_DIR = Path("results")

# ---------------------------------------------------------------------------
# Curated bootstrap examples
# These are included by default so the optimizer has something to work with
# even before any analysis runs have been saved.
# ---------------------------------------------------------------------------

BOOTSTRAP_EXAMPLES = [
    {
        "pmid": "bootstrap_apap_1",
        "chemical_name": "Acetaminophen",
        "abstract": (
            "Acetaminophen (APAP) overdose is the most common cause of acute liver failure "
            "in the United States. APAP is metabolized by CYP2E1 and CYP3A4 to the reactive "
            "metabolite N-acetyl-p-benzoquinone imine (NAPQI), which depletes hepatic "
            "glutathione stores and covalently binds to cellular proteins. The resulting "
            "oxidative stress triggers mitochondrial dysfunction through the mitochondrial "
            "permeability transition and activates the c-Jun N-terminal kinase (JNK) "
            "signaling pathway. Ultimately, APAP causes massive centrilobular hepatocyte "
            "necrosis. Inflammatory cells, including neutrophils and macrophages (Kupffer "
            "cells), are recruited and amplify liver injury through cytokine release."
        ),
        "kc_assessments": {
            "KC1": "SUPPORTED",
            "KC2": "SUPPORTED",
            "KC3": "NOT_MENTIONED",
            "KC4": "NOT_MENTIONED",
            "KC5": "SUPPORTED",
            "KC6": "SUPPORTED",
            "KC7": "SUPPORTED",
            "KC8": "SUPPORTED",
            "KC9": "NOT_MENTIONED",
            "KC10": "NOT_MENTIONED",
            "KC11": "NOT_MENTIONED",
            "KC12": "NOT_MENTIONED",
        },
        "source": "bootstrap_curated",
    },
    {
        "pmid": "bootstrap_apap_2",
        "chemical_name": "Acetaminophen",
        "abstract": (
            "We investigated the role of lipid metabolism dysregulation in "
            "acetaminophen-induced liver injury. Mice treated with 300 mg/kg APAP developed "
            "hepatic steatosis as evidenced by increased lipid droplet accumulation and "
            "elevated serum triglycerides. Transcriptomic analysis revealed suppression of "
            "fatty acid beta-oxidation genes and upregulation of lipogenic pathways. "
            "Glutathione depletion was confirmed by HPLC analysis 2 hours post-dose. "
            "JNK phosphorylation peaked at 1 hour, preceding the onset of cell death at "
            "6 hours. No fibrosis was observed at 24 hours by Sirius Red staining."
        ),
        "kc_assessments": {
            "KC1": "SUPPORTED",
            "KC2": "SUPPORTED",
            "KC3": "NOT_MENTIONED",
            "KC4": "NOT_MENTIONED",
            "KC5": "SUPPORTED",
            "KC6": "NOT_MENTIONED",
            "KC7": "NOT_MENTIONED",
            "KC8": "SUPPORTED",
            "KC9": "NOT_MENTIONED",
            "KC10": "NOT_MENTIONED",
            "KC11": "REFUTED",
            "KC12": "SUPPORTED",
        },
        "source": "bootstrap_curated",
    },
    {
        "pmid": "bootstrap_ccl4_1",
        "chemical_name": "Carbon tetrachloride",
        "abstract": (
            "Carbon tetrachloride (CCl4) is a classical hepatotoxic agent used to model "
            "liver fibrosis. CYP2E1 metabolizes CCl4 to the trichloromethyl radical (CCl3·), "
            "a highly reactive species that initiates lipid peroxidation and oxidative stress. "
            "Chronic CCl4 administration activates hepatic stellate cells, leading to "
            "excessive collagen deposition and cirrhosis. Acute exposure causes zone 3 "
            "hepatocyte necrosis and elevates serum ALT/AST. Kupffer cell activation "
            "and TNF-α secretion contribute to the inflammatory response. "
            "Mitochondrial damage and ATP depletion were observed 4 hours post-exposure."
        ),
        "kc_assessments": {
            "KC1": "SUPPORTED",
            "KC2": "SUPPORTED",
            "KC3": "NOT_MENTIONED",
            "KC4": "NOT_MENTIONED",
            "KC5": "SUPPORTED",
            "KC6": "SUPPORTED",
            "KC7": "SUPPORTED",
            "KC8": "NOT_MENTIONED",
            "KC9": "NOT_MENTIONED",
            "KC10": "NOT_MENTIONED",
            "KC11": "SUPPORTED",
            "KC12": "NOT_MENTIONED",
        },
        "source": "bootstrap_curated",
    },
    {
        "pmid": "bootstrap_mtx_1",
        "chemical_name": "Methotrexate",
        "abstract": (
            "Long-term methotrexate therapy is associated with hepatotoxicity, primarily "
            "manifesting as hepatic fibrosis and cirrhosis. The mechanism involves inhibition "
            "of dihydrofolate reductase, disrupting folate metabolism and nucleotide "
            "synthesis. Repeated exposure activates hepatic stellate cells and promotes "
            "extracellular matrix deposition. Histological assessment of liver biopsies "
            "showed progressive fibrosis in 15% of patients on long-term therapy. "
            "No significant oxidative stress markers or mitochondrial abnormalities were "
            "detected in short-term in vitro studies at therapeutic concentrations."
        ),
        "kc_assessments": {
            "KC1": "NOT_MENTIONED",
            "KC2": "NOT_MENTIONED",
            "KC3": "NOT_MENTIONED",
            "KC4": "NOT_MENTIONED",
            "KC5": "REFUTED",
            "KC6": "NOT_MENTIONED",
            "KC7": "REFUTED",
            "KC8": "NOT_MENTIONED",
            "KC9": "NOT_MENTIONED",
            "KC10": "NOT_MENTIONED",
            "KC11": "SUPPORTED",
            "KC12": "SUPPORTED",
        },
        "source": "bootstrap_curated",
    },
    {
        "pmid": "bootstrap_troglitazone_1",
        "chemical_name": "Troglitazone",
        "abstract": (
            "Troglitazone, a thiazolidinedione withdrawn from the market due to idiosyncratic "
            "hepatotoxicity, undergoes hepatic bioactivation to reactive quinone and "
            "sulfate metabolites. These reactive intermediates form protein adducts and "
            "impair the bile salt export pump (BSEP), resulting in intrahepatic bile acid "
            "retention and cholestasis. Mitochondrial membrane potential collapse was "
            "observed at concentrations above 50 μM in isolated hepatocytes. The drug "
            "also activates the unfolded protein response and ER stress pathways. "
            "Immune-mediated mechanisms involving T-cell activation have been proposed "
            "to explain the idiosyncratic nature of the injury."
        ),
        "kc_assessments": {
            "KC1": "SUPPORTED",
            "KC2": "NOT_MENTIONED",
            "KC3": "NOT_MENTIONED",
            "KC4": "SUPPORTED",
            "KC5": "NOT_MENTIONED",
            "KC6": "SUPPORTED",
            "KC7": "SUPPORTED",
            "KC8": "SUPPORTED",
            "KC9": "SUPPORTED",
            "KC10": "NOT_MENTIONED",
            "KC11": "NOT_MENTIONED",
            "KC12": "NOT_MENTIONED",
        },
        "source": "bootstrap_curated",
    },
]


# ---------------------------------------------------------------------------
# DSPy Example builder
# ---------------------------------------------------------------------------

def _to_dspy_example(record: dict) -> Any:
    """Convert a training record dict to a DSPy Example."""
    from dspy_optimizer import _get_dspy
    dspy = _get_dspy()

    return dspy.Example(
        abstract=record["abstract"],
        chemical_name=record["chemical_name"],
        kc_assessments=record["kc_assessments"],
        # Pre-format kc_statuses JSON string for metric comparison
        kc_statuses=json.dumps(record["kc_assessments"]),
    ).with_inputs("abstract", "chemical_name", "kc_definitions")


# ---------------------------------------------------------------------------
# Data Sources
# ---------------------------------------------------------------------------

def _load_curated_file() -> list[dict]:
    """Load manually curated training_data.json if it exists."""
    if not TRAINING_DATA_PATH.exists():
        return []
    try:
        data = json.loads(TRAINING_DATA_PATH.read_text())
        valid = [r for r in data if _is_valid_record(r)]
        logger.info(f"Loaded {len(valid)} curated training examples from {TRAINING_DATA_PATH}")
        return valid
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to load {TRAINING_DATA_PATH}: {e}")
        return []


def _load_gold_standard() -> list[dict]:
    """
    Load gold standard records. Attempts to fetch missing abstract text
    from PubMed using Bio.Entrez.
    """
    if not GOLD_STANDARD_PATH.exists():
        return []
    try:
        records = json.loads(GOLD_STANDARD_PATH.read_text())
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Failed to load gold standard: {e}")
        return []

    valid = []
    for record in records:
        if not record.get("is_relevant", True):
            continue
        if not record.get("kc_assessments"):
            continue
        if "abstract" not in record or not record["abstract"]:
            abstract = _fetch_abstract_from_pubmed(record.get("pmid", ""))
            if abstract:
                record["abstract"] = abstract
        if record.get("abstract"):
            record["source"] = "gold_standard"
            valid.append(record)

    logger.info(f"Loaded {len(valid)} usable gold standard examples")
    return valid


def _fetch_abstract_from_pubmed(pmid: str) -> str:
    """Fetch abstract text from PubMed for a given PMID."""
    if not pmid or pmid.startswith("bootstrap") or pmid.startswith("nihms"):
        return ""
    try:
        from Bio import Entrez
        Entrez.email = "research@example.com"
        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="text")
        text = handle.read()
        handle.close()
        time.sleep(0.4)  # Respect NCBI rate limit
        if text and len(text) > 50:
            logger.info(f"Fetched abstract for PMID {pmid}")
            return text.strip()
    except Exception as e:
        logger.warning(f"Could not fetch abstract for PMID {pmid}: {e}")
    return ""


def _load_from_results() -> list[dict]:
    """
    Load training examples from previously saved analysis results.
    Looks for result JSON files in results/ directory.
    """
    if not RESULTS_DIR.exists():
        return []

    records = []
    for result_file in RESULTS_DIR.rglob("*.json"):
        try:
            data = json.loads(result_file.read_text())
            # Handle both list and single-record files
            entries = data if isinstance(data, list) else [data]
            for entry in entries:
                if _is_valid_record(entry):
                    entry["source"] = f"results/{result_file.name}"
                    records.append(entry)
        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    logger.info(f"Loaded {len(records)} examples from results/ directory")
    return records


def _is_valid_record(record: dict) -> bool:
    """Check if a record has the required fields to be a training example."""
    return (
        isinstance(record, dict)
        and record.get("abstract")
        and record.get("chemical_name")
        and isinstance(record.get("kc_assessments"), dict)
        and len(record["kc_assessments"]) >= 12
    )


def _deduplicate(records: list[dict]) -> list[dict]:
    """Remove duplicate records by (pmid, chemical_name) pair."""
    seen = set()
    unique = []
    for r in records:
        key = (r.get("pmid", ""), r.get("chemical_name", "").lower())
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_training_dataset(save: bool = True) -> list[dict]:
    """
    Build the full training dataset by combining all sources.
    Priority: curated file > gold standard > results > bootstrap examples.

    Args:
        save: If True, save the merged dataset to training_data.json.

    Returns:
        List of valid training record dicts.
    """
    # Load from all sources
    curated = _load_curated_file()
    gold = _load_gold_standard()
    from_results = _load_from_results()

    # Bootstrap examples fill in if we have fewer than 5 real examples
    all_real = _deduplicate(curated + gold + from_results)
    if len(all_real) < 5:
        logger.info(f"Using {len(BOOTSTRAP_EXAMPLES)} bootstrap examples to supplement dataset")
        combined = _deduplicate(all_real + BOOTSTRAP_EXAMPLES)
    else:
        combined = all_real

    print(f"\n📚 Training Dataset Summary")
    print(f"   Curated:    {len(curated)}")
    print(f"   Gold std:   {len(gold)}")
    print(f"   Results:    {len(from_results)}")
    print(f"   Bootstrap:  {len(BOOTSTRAP_EXAMPLES)} (used if total < 5)")
    print(f"   Total unique: {len(combined)}")

    if save and combined:
        TRAINING_DATA_PATH.write_text(json.dumps(combined, indent=2))
        print(f"\n✅ Training data saved to {TRAINING_DATA_PATH}")

    return combined


def load_training_examples() -> list[Any]:
    """
    Load training examples as DSPy Example objects.
    Builds the dataset if training_data.json doesn't exist yet.
    """
    records = _load_curated_file()
    if not records:
        records = build_training_dataset(save=True)

    examples = []
    for record in records:
        try:
            examples.append(_to_dspy_example(record))
        except Exception as e:
            logger.warning(f"Skipping invalid record: {e}")

    return examples


def add_example_from_run(
    abstract: str,
    chemical_name: str,
    kc_assessments: dict[str, str],
    pmid: str = "",
) -> None:
    """
    Add a new training example from a live analysis run.
    Called automatically when the user confirms KC results are correct.

    Args:
        abstract: Abstract text.
        chemical_name: Chemical name.
        kc_assessments: Dict of {KC: status} validated by the user.
        pmid: PubMed ID if available.
    """
    existing = _load_curated_file()

    # Don't add duplicates
    for rec in existing:
        if rec.get("pmid") == pmid and rec.get("chemical_name") == chemical_name:
            logger.info(f"Example {pmid} already in training data, skipping")
            return

    new_record = {
        "pmid": pmid or f"user_{len(existing)}",
        "chemical_name": chemical_name,
        "abstract": abstract,
        "kc_assessments": kc_assessments,
        "source": "user_confirmed",
    }

    existing.append(new_record)
    TRAINING_DATA_PATH.write_text(json.dumps(existing, indent=2))
    logger.info(f"Added new training example for {chemical_name} ({pmid})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dataset = build_training_dataset(save=True)
    print(f"\nReady. {len(dataset)} examples available for optimization.")
    print("Run: python dspy_optimizer.py --model llama3.2 --optimizer bootstrap")
