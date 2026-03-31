"""
DSPy-based Prompt Optimization for KC Classification — Phase 1 RL Integration.

Uses DSPy to automatically optimize the prompts used for KC classification
by treating prompt engineering as an optimization problem scored against a
gold standard. Optimized prompts are saved to disk and loaded at app startup,
replacing the hand-tuned prompts transparently.

Usage:
    # Run optimization (takes ~10-30 min depending on model and dataset size)
    python dspy_optimizer.py --model llama3.2 --optimizer bootstrap

    # Check current optimized prompt score
    python dspy_optimizer.py --evaluate
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Where optimized programs are saved
OPTIMIZED_DIR = Path("optimized_prompts")
OPTIMIZED_PROGRAM_PATH = OPTIMIZED_DIR / "kc_classifier_optimized.json"
OPTIMIZATION_LOG_PATH = OPTIMIZED_DIR / "optimization_history.json"

# Valid KC statuses
VALID_STATUSES = {"SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED", "REFUTED", "NOT_MENTIONED"}
POSITIVE_STATUSES = {"SUPPORTED", "ASSOCIATED", "CAUSALLY_LINKED"}

KC_DEFINITIONS = {
    "KC1": "Is reactive and/or is metabolized (bioactivated) to reactive moieties.",
    "KC2": "Causes death (apoptosis and/or necrosis) of liver cells.",
    "KC3": "Affects liver cell proliferation and/or tissue regeneration.",
    "KC4": "Disrupts transport function.",
    "KC5": "Induces oxidative stress (imbalance between ROS and antioxidants).",
    "KC6": "Triggers immune-mediated responses in liver.",
    "KC7": "Causes mitochondrial dysfunction.",
    "KC8": "Activates stress signaling pathways.",
    "KC9": "Causes cholestasis.",
    "KC10": "Disrupts cellular cytoskeleton.",
    "KC11": "Causes liver fibrosis.",
    "KC12": "Disrupts liver metabolism, including of lipids and proteins.",
}

KC_DEFINITIONS_TEXT = "\n".join(
    f"{kc}: {definition}" for kc, definition in KC_DEFINITIONS.items()
)


# ---------------------------------------------------------------------------
# DSPy Signature and Module
# ---------------------------------------------------------------------------

def _get_dspy():
    """Lazy import DSPy to avoid hard dependency at module load time."""
    try:
        import dspy
        return dspy
    except ImportError as e:
        raise ImportError(
            "DSPy is required for prompt optimization. "
            "Install it with: pip install dspy-ai"
        ) from e


def build_kc_signature(dspy_module):
    """Build the DSPy Signature class for KC classification."""

    class KCClassificationSignature(dspy_module.Signature):
        """Analyze a scientific abstract to determine which Key Characteristics (KCs)
        of Hepatotoxicity are exhibited by the specified chemical.

        Rules:
        - Only attribute a KC to the chemical if the abstract explicitly discusses
          it in relation to THAT chemical, not a comparator or control compound.
        - Output a valid JSON object mapping each KC (KC1–KC12) to one of:
          SUPPORTED, ASSOCIATED, CAUSALLY_LINKED, REFUTED, or NOT_MENTIONED.
        """

        abstract: str = dspy_module.InputField(
            desc="Scientific abstract text to analyze"
        )
        chemical_name: str = dspy_module.InputField(
            desc="Name of the chemical being assessed for hepatotoxicity"
        )
        kc_definitions: str = dspy_module.InputField(
            desc="Definitions of all 12 Key Characteristics of Hepatotoxicity"
        )

        reasoning: str = dspy_module.OutputField(
            desc="Step-by-step chain-of-thought reasoning for each KC decision, "
                 "referencing specific text from the abstract"
        )
        kc_statuses: str = dspy_module.OutputField(
            desc=(
                'JSON object mapping KC names to their status. '
                'Example: {"KC1": "SUPPORTED", "KC2": "NOT_MENTIONED", '
                '"KC3": "NOT_MENTIONED", "KC4": "NOT_MENTIONED", '
                '"KC5": "SUPPORTED", "KC6": "NOT_MENTIONED", '
                '"KC7": "SUPPORTED", "KC8": "NOT_MENTIONED", '
                '"KC9": "NOT_MENTIONED", "KC10": "NOT_MENTIONED", '
                '"KC11": "NOT_MENTIONED", "KC12": "NOT_MENTIONED"}'
            )
        )

    return KCClassificationSignature


def build_kc_module(dspy_module):
    """Build the DSPy Module for KC classification."""
    KCClassificationSignature = build_kc_signature(dspy_module)

    class KCClassifier(dspy_module.Module):
        """KC classifier using Chain-of-Thought reasoning."""

        def __init__(self):
            super().__init__()
            self.classify = dspy_module.ChainOfThought(KCClassificationSignature)

        def forward(
            self,
            abstract: str,
            chemical_name: str,
            kc_definitions: str = KC_DEFINITIONS_TEXT,
        ):
            return self.classify(
                abstract=abstract,
                chemical_name=chemical_name,
                kc_definitions=kc_definitions,
            )

    return KCClassifier


# ---------------------------------------------------------------------------
# Metric Function
# ---------------------------------------------------------------------------

def parse_kc_statuses(raw: str) -> dict[str, str]:
    """Parse KC statuses from LLM output string into a clean dict."""
    # Try direct JSON parse
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return {k.upper(): v.upper().strip() for k, v in data.items()}
    except (json.JSONDecodeError, AttributeError):
        pass

    # Try to extract JSON blob from surrounding text
    match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, dict):
                return {k.upper(): v.upper().strip() for k, v in data.items()}
        except json.JSONDecodeError:
            pass

    # Try key:value pattern as last resort
    result = {}
    for kc_num in range(1, 13):
        kc = f"KC{kc_num}"
        pattern = rf"{kc}[\"']?\s*[:\-]\s*[\"']?(\w+)"
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            status = m.group(1).upper().strip()
            result[kc] = status if status in VALID_STATUSES else "NOT_MENTIONED"
        else:
            result[kc] = "NOT_MENTIONED"

    return result


def kc_accuracy_metric(
    gold_example: Any, prediction: Any, trace: Any = None
) -> float:
    """
    Score a KC prediction against the gold standard.

    Scoring per KC:
      - Exact match:                    1.0
      - Both positive (SUPPORTED/etc):  0.7 (right direction, wrong granularity)
      - Both negative (NOT_MENTIONED):  1.0
      - Otherwise:                      0.0

    Returns a float in [0, 1] representing average per-KC accuracy.
    """
    # Get gold standard KC assessments
    gold_kcs: dict[str, str] = {}
    if hasattr(gold_example, "kc_assessments"):
        gold_kcs = gold_example.kc_assessments
    elif hasattr(gold_example, "kc_statuses"):
        gold_kcs = parse_kc_statuses(gold_example.kc_statuses)

    if not gold_kcs:
        return 0.0

    # Parse prediction
    pred_raw = getattr(prediction, "kc_statuses", "{}")
    pred_kcs = parse_kc_statuses(str(pred_raw))

    score = 0.0
    for kc, gold_status in gold_kcs.items():
        gold_status = gold_status.upper().strip()
        pred_status = pred_kcs.get(kc, "NOT_MENTIONED")

        # Normalize pred to valid status
        if pred_status not in VALID_STATUSES:
            for vs in VALID_STATUSES:
                if vs in pred_status:
                    pred_status = vs
                    break
            else:
                pred_status = "NOT_MENTIONED"

        if gold_status == pred_status:
            score += 1.0
        elif gold_status in POSITIVE_STATUSES and pred_status in POSITIVE_STATUSES:
            score += 0.7  # Correct direction, wrong granularity
        # else: 0.0 — wrong prediction

    return score / len(gold_kcs)


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------

def configure_dspy(model_name: str, ollama_base: str = "http://localhost:11434"):
    """Configure DSPy with an Ollama model."""
    dspy = _get_dspy()
    lm = dspy.LM(
        f"ollama_chat/{model_name}",
        api_base=ollama_base,
        api_key="ollama",
        temperature=0.1,
        max_tokens=2048,
    )
    dspy.configure(lm=lm)
    logger.info(f"DSPy configured with model: {model_name}")
    return lm


def run_optimization(
    training_examples: list,
    model_name: str = "llama3.2",
    optimizer_type: str = "bootstrap",
    ollama_base: str = "http://localhost:11434",
    max_bootstrapped_demos: int = 3,
    max_labeled_demos: int = 4,
) -> tuple[Any, float]:
    """
    Run DSPy prompt optimization on KC classification.

    Args:
        training_examples: List of DSPy Example objects with abstract,
                           chemical_name, and kc_assessments fields.
        model_name: Ollama model to use.
        optimizer_type: "bootstrap" (fast, small data) or "mipro" (thorough).
        ollama_base: Ollama server URL.
        max_bootstrapped_demos: Max bootstrapped few-shot examples.
        max_labeled_demos: Max labeled few-shot examples.

    Returns:
        (optimized_program, best_score)
    """
    dspy = _get_dspy()
    configure_dspy(model_name, ollama_base)

    KCClassifier = build_kc_module(dspy)
    classifier = KCClassifier()

    # Split into train / dev
    split = max(1, int(len(training_examples) * 0.8))
    train_set = training_examples[:split]
    dev_set = training_examples[split:] or training_examples[:1]

    print(f"\n🔧 Starting DSPy optimization")
    print(f"   Optimizer:    {optimizer_type}")
    print(f"   Model:        {model_name}")
    print(f"   Train examples: {len(train_set)}")
    print(f"   Dev examples:   {len(dev_set)}")

    if optimizer_type == "mipro":
        optimizer = dspy.MIPROv2(
            metric=kc_accuracy_metric,
            auto="medium",
            num_threads=1,
            verbose=True,
        )
        optimized = optimizer.compile(
            classifier,
            trainset=train_set,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
        )
    else:
        # BootstrapFewShot — works well with small datasets
        optimizer = dspy.BootstrapFewShot(
            metric=kc_accuracy_metric,
            max_bootstrapped_demos=max_bootstrapped_demos,
            max_labeled_demos=max_labeled_demos,
            max_rounds=1,
        )
        optimized = optimizer.compile(classifier, trainset=train_set)

    # Evaluate on dev set
    best_score = _evaluate(optimized, dev_set)
    baseline_score = _evaluate(classifier, dev_set)

    print(f"\n📊 Optimization Results")
    print(f"   Baseline score:  {baseline_score:.3f}")
    print(f"   Optimized score: {best_score:.3f}")
    print(f"   Improvement:     {best_score - baseline_score:+.3f}")

    return optimized, best_score


def _evaluate(program: Any, examples: list) -> float:
    """Evaluate a DSPy program on a list of examples."""
    if not examples:
        return 0.0
    scores = []
    for ex in examples:
        try:
            pred = program(
                abstract=ex.abstract,
                chemical_name=ex.chemical_name,
                kc_definitions=KC_DEFINITIONS_TEXT,
            )
            score = kc_accuracy_metric(ex, pred)
            scores.append(score)
        except Exception as e:
            logger.warning(f"Evaluation failed for example: {e}")
            scores.append(0.0)
    return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

def save_optimized_program(program: Any, score: float, metadata: dict | None = None):
    """Save the optimized DSPy program to disk."""
    OPTIMIZED_DIR.mkdir(exist_ok=True)
    program.save(str(OPTIMIZED_PROGRAM_PATH))

    # Log the optimization run
    history = []
    if OPTIMIZATION_LOG_PATH.exists():
        try:
            history = json.loads(OPTIMIZATION_LOG_PATH.read_text())
        except json.JSONDecodeError:
            history = []

    from datetime import datetime
    history.append({
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "metadata": metadata or {},
    })
    OPTIMIZATION_LOG_PATH.write_text(json.dumps(history, indent=2))
    print(f"\n✅ Optimized program saved to {OPTIMIZED_PROGRAM_PATH}")


def load_optimized_program(model_name: str, ollama_base: str = "http://localhost:11434") -> Optional[Any]:
    """
    Load the saved optimized program if it exists.
    Returns None if not available (falls back to standard prompts).
    """
    if not OPTIMIZED_PROGRAM_PATH.exists():
        return None
    try:
        dspy = _get_dspy()
        configure_dspy(model_name, ollama_base)
        KCClassifier = build_kc_module(dspy)
        program = KCClassifier()
        program.load(str(OPTIMIZED_PROGRAM_PATH))
        logger.info(f"Loaded optimized DSPy program from {OPTIMIZED_PROGRAM_PATH}")
        return program
    except Exception as e:
        logger.warning(f"Failed to load optimized program: {e}")
        return None


def predict_with_optimized(
    program: Any,
    abstract: str,
    chemical_name: str,
) -> dict[str, str] | None:
    """
    Run KC classification with the optimized DSPy program.
    Returns a dict of {KC: status} or None on failure.
    """
    try:
        result = program(
            abstract=abstract,
            chemical_name=chemical_name,
            kc_definitions=KC_DEFINITIONS_TEXT,
        )
        return parse_kc_statuses(result.kc_statuses)
    except Exception as e:
        logger.warning(f"Optimized prediction failed: {e}")
        return None


def is_optimized_program_available() -> bool:
    """Quick check — does an optimized program exist on disk?"""
    return OPTIMIZED_PROGRAM_PATH.exists()


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="DSPy prompt optimizer for KC classification"
    )
    parser.add_argument("--model", default="llama3.2", help="Ollama model name")
    parser.add_argument(
        "--optimizer",
        choices=["bootstrap", "mipro"],
        default="bootstrap",
        help="Optimizer type (bootstrap=fast, mipro=thorough)",
    )
    parser.add_argument(
        "--ollama-base",
        default="http://localhost:11434",
        help="Ollama server base URL",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Evaluate current optimized program without re-optimizing",
    )
    args = parser.parse_args()

    # Load training data
    from training_data_builder import load_training_examples
    examples = load_training_examples()

    if not examples:
        print("❌ No training examples found. Run training_data_builder.py first.")
        return

    print(f"📚 Loaded {len(examples)} training examples")

    if args.evaluate:
        program = load_optimized_program(args.model, args.ollama_base)
        if program is None:
            print("❌ No optimized program found. Run without --evaluate to optimize first.")
            return
        score = _evaluate(program, examples)
        print(f"📊 Current optimized program score: {score:.3f}")
        return

    # Run optimization
    optimized, score = run_optimization(
        training_examples=examples,
        model_name=args.model,
        optimizer_type=args.optimizer,
        ollama_base=args.ollama_base,
    )

    save_optimized_program(
        optimized,
        score,
        metadata={"model": args.model, "optimizer": args.optimizer, "n_examples": len(examples)},
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
