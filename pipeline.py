import os
import time
import logging
from typing import List, Dict, Tuple, Optional, Any, Callable
import pandas as pd
from langchain_core.messages import SystemMessage, HumanMessage

# Import project modules
from search_enhanced import fetch_pubmed_enhanced
from evidence_models import StudyRecord
from provenance import create_provenance_record, save_provenance
from prisma import create_prisma_flow_diagram
from multi_reviewer import consolidate_kc_analyses
from config import get_config
from exceptions import SearchError, ChemicalStandardizationError, LLMError
from core_logic import (
    standardize_chemical_name, 
    check_relevance, 
    analyze_abstract_with_llm
)
from risk_of_bias import assess_rob_with_llm
from certainty_grading import assess_certainty_per_kc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HepatotoxicityPipeline:
    """
    Orchestrates the Hepatotoxicity Assessment Pipeline:
    1. Standardization (Librarian)
    2. Search (Librarian)
    3. Relevance Filtering (Gatekeeper)
    4. Analysis (Analyst)
    5. Reporting (Architect)
    """

    def __init__(self, config=None):
        self.config = config or get_config()
        self.results = {}
        self.state = {
            "step": "initialized",
            "progress": 0,
            "message": "Ready"
        }

    def update_progress(self, progress_callback: Optional[Callable], progress: float, message: str):
        """Update progress if a callback is provided."""
        self.state["progress"] = progress
        self.state["message"] = message
        if progress_callback:
            # Gradio progress expects (progress_float, message_str)
            progress_callback(progress, desc=message)
        logger.info(f"Progress: {progress:.2f} - {message}")

    def run_pipeline(
        self, 
        chemical_name: str, 
        models: List[str], 
        enable_rob: bool = False,
        enable_certainty: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Run the full analysis pipeline.
        """
        try:
            start_time = time.time()
            self.update_progress(progress_callback, 0.05, "Standardizing chemical name...")
            
            # Step 1: Standardize Chemical
            std_name, cid, synonyms = standardize_chemical_name(chemical_name)
            self.update_progress(progress_callback, 0.1, f"Identified: {std_name} (CID: {cid})")

            # Step 2: Search Literature
            self.update_progress(progress_callback, 0.15, "Fetching abstracts from PubMed...")
            abstracts = fetch_pubmed_enhanced(
                chemical_name=std_name, 
                synonyms=synonyms, 
                max_results=self.config.search.max_abstracts_initial
            )
            
            if not abstracts:
                raise SearchError(f"No abstracts found for {std_name}")

            self.update_progress(progress_callback, 0.25, f"Found {len(abstracts)} abstracts. Filtering for relevance...")

            # Step 3: Filter Relevance
            relevant_abstracts = []
            for i, abstract in enumerate(abstracts):
                if check_relevance(abstract.get('text', abstract.get('abstract', '')), abstract['title'], std_name):
                    relevant_abstracts.append(abstract)
                
                # Update progress periodically
                if i % 10 == 0:
                    prog = 0.25 + (0.15 * (i / len(abstracts)))
                    self.update_progress(progress_callback, prog, f"Filtered {i}/{len(abstracts)} abstracts")

            if not relevant_abstracts:
                raise SearchError("No relevant abstracts found after filtering.")

            # Limit analysis to configured max
            relevant_abstracts = relevant_abstracts[:self.config.search.max_abstracts_analyze]
            self.update_progress(progress_callback, 0.4, f"Analyzing {len(relevant_abstracts)} relevant abstracts...")

            # Step 4: Analyze Content (KC + RoB + Certainty)
            analyzed_records = []
            
            for i, abstract in enumerate(relevant_abstracts):
                # KC Analysis
                analysis_result, _ = analyze_abstract_with_llm(abstract['text'], abstract['title'])
                
                # RoB Analysis (Optional)
                rob_result = None
                if enable_rob:
                    rob_result = assess_rob_with_llm(abstract['text'], abstract['title'])

                # Create Record
                record = {
                    "abstract": abstract,
                    "analysis": analysis_result,
                    "rob": rob_result
                }
                analyzed_records.append(record)
                
                prog = 0.4 + (0.5 * (i / len(relevant_abstracts)))
                self.update_progress(progress_callback, prog, f"Analyzed {i+1}/{len(relevant_abstracts)}")

            # Step 5: Synthesis
            self.update_progress(progress_callback, 0.95, "Synthesizing results...")
            
            # Create Provenance
            provenance = create_provenance_record(
                chemical_name=std_name,
                model_name=models[0] if models else "default",
                step="pipeline_complete",
                details={"relevant_count": len(relevant_abstracts)}
            )

            # Generate Results Structure
            results = {
                "chemical_name": std_name,
                "cid": cid,
                "abstracts": relevant_abstracts,
                "analyzed_records": analyzed_records,
                "provenance": provenance,
                "timestamp": time.time()
            }
            
            self.results = results
            self.update_progress(progress_callback, 1.0, "Analysis Complete!")
            
            return results

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            self.update_progress(progress_callback, 0, f"Error: {str(e)}")
            raise e
