"""
Provenance tracking and audit trail for reproducibility
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path


def hash_prompt(prompt_text: str) -> str:
    """Generate SHA256 hash of prompt for reproducibility"""
    return hashlib.sha256(prompt_text.encode()).hexdigest()[:16]


def create_provenance_record(
    chemical_name: str,
    model_name: str,
    model_version: Optional[str] = None,
    prompt_hash: Optional[str] = None,
    temperature: float = 0.0,
    search_query: Optional[str] = None,
    pmids: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a provenance record for a review run
    """
    timestamp = datetime.now().isoformat()
    
    record = {
        "chemical_name": chemical_name,
        "timestamp": timestamp,
        "model": {
            "name": model_name,
            "version": model_version or "unknown",
            "temperature": temperature
        },
        "prompt": {
            "hash": prompt_hash or "unknown"
        },
        "search": {
            "query": search_query,
            "pmids_retrieved": len(pmids) if pmids else 0,
            "pmids": pmids[:10] if pmids else []  # Store first 10 for reference
        },
        "parameters": kwargs
    }
    
    return record


def save_provenance(
    provenance_record: Dict[str, Any],
    output_dir: str = "results",
    chemical_name: Optional[str] = None
) -> str:
    """
    Save provenance record to JSON file
    Returns path to saved file
    """
    # Create output directory
    if chemical_name:
        safe_name = "".join(c for c in chemical_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        chem_dir = os.path.join(output_dir, safe_name)
    else:
        chem_dir = output_dir
    
    os.makedirs(chem_dir, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = provenance_record.get("timestamp", datetime.now().isoformat())
    timestamp_short = timestamp.replace(":", "-").split(".")[0]
    filename = f"provenance_{timestamp_short}.json"
    filepath = os.path.join(chem_dir, filename)
    
    # Save
    with open(filepath, 'w') as f:
        json.dump(provenance_record, f, indent=2)
    
    return filepath


def save_study_record(
    study_record: Dict[str, Any],
    output_dir: str = "results",
    chemical_name: Optional[str] = None
) -> str:
    """
    Save individual study record (JSONL format for easy processing)
    """
    if chemical_name:
        safe_name = "".join(c for c in chemical_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        chem_dir = os.path.join(output_dir, safe_name)
    else:
        chem_dir = output_dir
    
    os.makedirs(chem_dir, exist_ok=True)
    
    # JSONL file (one JSON object per line)
    jsonl_file = os.path.join(chem_dir, "study_records.jsonl")
    
    with open(jsonl_file, 'a') as f:
        f.write(json.dumps(study_record) + '\n')
    
    return jsonl_file


def save_search_log(
    search_log: Dict[str, Any],
    output_dir: str = "results",
    chemical_name: Optional[str] = None
) -> str:
    """
    Save search strategy and results log
    """
    if chemical_name:
        safe_name = "".join(c for c in chemical_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        chem_dir = os.path.join(output_dir, safe_name)
    else:
        chem_dir = output_dir
    
    os.makedirs(chem_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"search_log_{timestamp}.json"
    filepath = os.path.join(chem_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(search_log, f, indent=2)
    
    return filepath


def load_provenance(filepath: str) -> Dict[str, Any]:
    """Load provenance record from file"""
    with open(filepath, 'r') as f:
        return json.load(f)
