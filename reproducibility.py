"""
Reproducibility and Version Tracking for Systematic Review Research

This module provides comprehensive tracking of:
- LLM model versions and configurations
- Prompt archiving with versioning
- Dependency versioning
- Experiment configuration snapshots
"""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_ollama_model_info(model_name: str) -> Dict[str, Any]:
    """
    Get detailed information about an Ollama model
    
    Returns model size, architecture, and other metadata if available
    """
    try:
        # Try to get model info from Ollama
        result = subprocess.run(
            ["ollama", "show", model_name, "--modelfile"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            modelfile = result.stdout
            # Extract key information
            info = {
                "model_name": model_name,
                "modelfile": modelfile,
                "source": "ollama"
            }

            # Try to get model size
            try:
                size_result = subprocess.run(
                    ["ollama", "list"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if size_result.returncode == 0:
                    for line in size_result.stdout.split('\n'):
                        if model_name in line:
                            parts = line.split()
                            if len(parts) >= 2:
                                info["size"] = parts[1]  # Usually shows size like "3.8GB"
            except Exception:
                pass

            return info
    except Exception:
        pass

    # Fallback: return basic info
    return {
        "model_name": model_name,
        "source": "ollama",
        "note": "Could not retrieve detailed model info"
    }


def get_ollama_version() -> Optional[str]:
    """Get Ollama version"""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def get_python_package_versions() -> Dict[str, str]:
    """
    Get versions of all key dependencies
    
    Returns dict mapping package name to version
    """
    key_packages = [
        "langchain",
        "langchain-community",
        "pydantic",
        "pandas",
        "numpy",
        "matplotlib",
        "networkx",
        "pubchempy",
        "biopython",
        "gradio",
        "ollama",
    ]

    versions = {}
    for package in key_packages:
        try:
            # Try different import names
            import_name = package.replace("-", "_")
            if import_name == "biopython":
                import_name = "Bio"

            version = importlib.metadata.version(package)
            versions[package] = version
        except Exception:
            versions[package] = "unknown"

    return versions


def archive_prompt(
    prompt_text: str,
    prompt_type: str,
    prompt_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Archive a prompt with full versioning information
    
    Args:
        prompt_text: The prompt text
        prompt_type: Type of prompt (e.g., "kc_analysis", "relevance_check", "rob_assessment")
        prompt_name: Optional name for the prompt
        metadata: Additional metadata
    
    Returns:
        Archive record with hash, timestamp, and full text
    """
    timestamp = datetime.now().isoformat()
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

    archive_record = {
        "prompt_name": prompt_name or f"{prompt_type}_{timestamp}",
        "prompt_type": prompt_type,
        "timestamp": timestamp,
        "hash": prompt_hash,
        "hash_short": prompt_hash[:16],  # Short hash for easy reference
        "prompt_text": prompt_text,
        "metadata": metadata or {},
        "system_info": {
            "python_version": sys.version,
            "platform": platform.platform(),
        }
    }

    return archive_record


def save_prompt_archive(
    archive_record: Dict[str, Any],
    archive_dir: str = "prompt_archives"
) -> str:
    """
    Save prompt archive to file
    
    Returns path to saved file
    """
    Path(archive_dir).mkdir(parents=True, exist_ok=True)

    # Create filename from hash and timestamp
    timestamp_short = archive_record["timestamp"].replace(":", "-").split(".")[0]
    filename = f"{archive_record['prompt_type']}_{archive_record['hash_short']}_{timestamp_short}.json"
    filepath = Path(archive_dir) / filename

    with open(filepath, 'w') as f:
        json.dump(archive_record, f, indent=2)

    return str(filepath)


def create_experiment_snapshot(
    chemical_name: str,
    model_names: List[str],
    config_dict: Dict[str, Any],
    prompt_hashes: Optional[Dict[str, str]] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a complete snapshot of an experiment for reproducibility
    
    This includes:
    - All model versions and configurations
    - All prompt hashes
    - System information
    - Dependency versions
    - Configuration parameters
    """
    timestamp = datetime.now().isoformat()

    # Get model information
    model_info = {}
    for model_name in model_names:
        model_info[model_name] = get_ollama_model_info(model_name)

    # Get dependency versions
    package_versions = get_python_package_versions()

    # Get Ollama version
    ollama_version = get_ollama_version()

    snapshot = {
        "experiment_id": f"{chemical_name}_{timestamp.replace(':', '-').split('.')[0]}",
        "chemical_name": chemical_name,
        "timestamp": timestamp,
        "models": model_info,
        "ollama_version": ollama_version,
        "dependencies": package_versions,
        "system": {
            "python_version": sys.version,
            "platform": platform.platform(),
            "architecture": platform.architecture(),
            "processor": platform.processor(),
        },
        "configuration": config_dict,
        "prompt_hashes": prompt_hashes or {},
        "metadata": additional_metadata or {},
    }

    return snapshot


def save_experiment_snapshot(
    snapshot: Dict[str, Any],
    output_dir: str = "experiment_snapshots"
) -> str:
    """
    Save experiment snapshot to file
    
    Returns path to saved file
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    filename = f"{snapshot['experiment_id']}.json"
    filepath = Path(output_dir) / filename

    with open(filepath, 'w') as f:
        json.dump(snapshot, f, indent=2)

    return str(filepath)


def load_experiment_snapshot(filepath: str) -> Dict[str, Any]:
    """Load an experiment snapshot from file"""
    with open(filepath) as f:
        return json.load(f)


def verify_reproducibility(
    snapshot_file: str,
    current_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Verify that current environment matches a previous experiment snapshot
    
    Returns dict with verification results
    """
    snapshot = load_experiment_snapshot(snapshot_file)

    verification = {
        "snapshot_id": snapshot.get("experiment_id"),
        "snapshot_timestamp": snapshot.get("timestamp"),
        "checks": {},
        "warnings": [],
        "errors": []
    }

    # Check Python version
    current_python = sys.version.split()[0]
    snapshot_python = snapshot.get("system", {}).get("python_version", "").split()[0]
    verification["checks"]["python_version"] = {
        "match": current_python == snapshot_python,
        "snapshot": snapshot_python,
        "current": current_python
    }

    # Check dependency versions
    current_versions = get_python_package_versions()
    snapshot_versions = snapshot.get("dependencies", {})

    version_matches = {}
    for package, snapshot_version in snapshot_versions.items():
        current_version = current_versions.get(package, "unknown")
        match = current_version == snapshot_version
        version_matches[package] = {
            "match": match,
            "snapshot": snapshot_version,
            "current": current_version
        }
        if not match:
            verification["warnings"].append(
                f"Package {package} version mismatch: {snapshot_version} vs {current_version}"
            )

    verification["checks"]["dependencies"] = version_matches

    # Check Ollama version
    current_ollama = get_ollama_version()
    snapshot_ollama = snapshot.get("ollama_version")
    verification["checks"]["ollama_version"] = {
        "match": current_ollama == snapshot_ollama,
        "snapshot": snapshot_ollama,
        "current": current_ollama
    }

    # Check models
    snapshot_models = list(snapshot.get("models", {}).keys())
    verification["checks"]["models"] = {
        "snapshot_models": snapshot_models,
        "note": "Model availability should be verified manually"
    }

    # Check configuration if provided
    if current_config:
        snapshot_config = snapshot.get("configuration", {})
        config_match = current_config == snapshot_config
        verification["checks"]["configuration"] = {
            "match": config_match,
            "snapshot": snapshot_config,
            "current": current_config
        }
        if not config_match:
            verification["warnings"].append("Configuration parameters differ from snapshot")

    return verification
