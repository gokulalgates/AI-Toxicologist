# Reproducibility Guide

This guide explains how to ensure reproducibility of results using the built-in reproducibility tracking system.

## Overview

The reproducibility system tracks:
- **LLM Model Versions**: Exact model names and configurations
- **Prompt Versions**: SHA256 hashes of all prompts used
- **Dependency Versions**: Python package versions
- **System Information**: Platform, Python version, etc.
- **Configuration**: All analysis parameters

## Automatic Tracking

### Experiment Snapshots

Every analysis automatically creates an experiment snapshot in `experiment_snapshots/`:

```python
from reproducibility import create_experiment_snapshot, save_experiment_snapshot

snapshot = create_experiment_snapshot(
    chemical_name="Acetaminophen",
    model_names=["llama3.2", "mixtral"],
    config_dict={...},
    additional_metadata={...}
)
save_experiment_snapshot(snapshot)
```

The snapshot includes:
- Model information (name, source, size)
- Ollama version
- Python package versions
- System information
- Configuration parameters
- Prompt hashes

### Prompt Archiving

All prompts are automatically archived in `prompt_archives/`:

- Each prompt gets a SHA256 hash
- Full prompt text is saved
- Metadata includes model, chemical, temperature, etc.

## Verifying Reproducibility

### Check Environment Match

```python
from reproducibility import verify_reproducibility, load_experiment_snapshot

# Load a previous snapshot
snapshot = load_experiment_snapshot("experiment_snapshots/acetaminophen_2025-01-15T10-30-00.json")

# Verify current environment matches
verification = verify_reproducibility(
    "experiment_snapshots/acetaminophen_2025-01-15T10-30-00.json",
    current_config={...}
)

# Check results
if verification["checks"]["python_version"]["match"]:
    print("✓ Python version matches")
else:
    print(f"⚠ Python version mismatch: {verification['checks']['python_version']}")

if all(v["match"] for v in verification["checks"]["dependencies"].values()):
    print("✓ All dependencies match")
else:
    print("⚠ Some dependencies differ:")
    for pkg, info in verification["checks"]["dependencies"].items():
        if not info["match"]:
            print(f"  - {pkg}: {info['snapshot']} vs {info['current']}")
```

## Reproducing Results

### Step 1: Install Exact Dependencies

```bash
# Create frozen requirements
pip freeze > requirements_frozen.txt

# Install exact versions
pip install -r requirements_frozen.txt
```

### Step 2: Install Same Ollama Models

```bash
# Check which models were used (from snapshot)
cat experiment_snapshots/acetaminophen_2025-01-15T10-30-00.json | grep model_name

# Install models
ollama pull llama3.2
ollama pull mixtral
```

### Step 3: Use Same Configuration

Load the configuration from the snapshot:

```python
import json
from config import set_config, AppConfig

with open("experiment_snapshots/acetaminophen_2025-01-15T10-30-00.json") as f:
    snapshot = json.load(f)

# Recreate configuration
config = AppConfig()
config_dict = snapshot["configuration"]
# Apply config_dict to config object
set_config(config)
```

### Step 4: Use Same Prompts

Prompts are archived with their hashes. To verify you're using the same prompt:

```python
from reproducibility import hash_prompt
from prompt_templates import get_prompt_for_abstract

# Get prompt
prompt = get_prompt_for_abstract(...)

# Calculate hash
prompt_hash = hash_prompt(prompt)

# Compare with archived hash
archived_hash = "abc123..."  # From prompt_archives/
assert prompt_hash[:16] == archived_hash[:16], "Prompt hash mismatch!"
```

## Sharing for Publication

### Package for GitHub

1. **Include**:
   - All Python scripts
   - `requirements.txt` (and `requirements_frozen.txt`)
   - `README.md`
   - `PUBLICATION_READINESS.md`
   - Example `experiment_snapshots/` (at least one)
   - Example `prompt_archives/` (at least one)

2. **Exclude** (use `.gitignore`):
   - Large result files
   - Model files
   - Temporary files

### Package Data for Zenodo/Figshare

1. **Include**:
   - `provenance_*.json` files
   - `search_log_*.json` files
   - `study_records.jsonl` files
   - `experiment_snapshots/` directory
   - `prompt_archives/` directory
   - Gold standard datasets (if available)

2. **Metadata**:
   - DOI (assigned by Zenodo/Figshare)
   - Description
   - License (CC-BY recommended)

## Best Practices

1. **Always Archive Prompts**: Prompts are automatically archived, but verify they're saved
2. **Document Model Versions**: Note any model updates that might affect results
3. **Pin Dependencies**: Use `requirements_frozen.txt` for exact reproducibility
4. **Save Snapshots**: Experiment snapshots are created automatically
5. **Verify Before Publishing**: Run `verify_reproducibility()` before finalizing results

## Troubleshooting

### "Model not found" error

If a model from a snapshot isn't available:

```bash
# Check available models
ollama list

# Install missing model
ollama pull <model_name>
```

### "Dependency version mismatch" warning

This is usually okay if it's a patch version. Check if it affects results:

```python
# Run a small test with both versions
# Compare outputs
```

### "Prompt hash mismatch"

This means the prompt has changed. Check:
1. Was `prompt_mode` changed?
2. Were prompt templates modified?
3. Is the same `chemical_name` being used?

## Example Workflow

```python
# 1. Run analysis (automatically creates snapshot)
from app import analyze_chemical
results = analyze_chemical("Acetaminophen", model_names=["llama3.2", "mixtral"])

# 2. Verify snapshot was created
import os
snapshots = [f for f in os.listdir("experiment_snapshots") if "acetaminophen" in f]
print(f"Created snapshot: {snapshots[-1]}")

# 3. Later, verify reproducibility
from reproducibility import verify_reproducibility
verification = verify_reproducibility(snapshots[-1])
print(verification)

# 4. Share snapshot and prompt archives for publication
```

## Citation

When publishing, cite:
- The code repository (GitHub)
- The data repository (Zenodo/Figshare DOI)
- The protocol registration (PROSPERO/OSF ID)
- Specific experiment snapshots used

Example:
```
Code: https://github.com/yourusername/ai-toxicologist
Data: https://doi.org/10.5281/zenodo.xxxxx
Protocol: PROSPERO CRD42025xxxxx
Experiment Snapshot: experiment_snapshots/acetaminophen_2025-01-15T10-30-00.json
```
