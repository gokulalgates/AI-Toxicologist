"""
ASReview Integration for Active Learning in Systematic Review Screening
Uses ASReview library to accelerate abstract screening with active learning
"""

import logging
from typing import List, Dict, Optional, Tuple
import os
import tempfile
import json

logger = logging.getLogger(__name__)

# Try to import ASReview
try:
    import asreview as asr
    ASREVIEW_AVAILABLE = True
except ImportError:
    ASREVIEW_AVAILABLE = False
    logger.warning("ASReview not available. Install with: pip install asreview")


class ASReviewScreener:
    """
    Wrapper for ASReview active learning screening
    """
    
    def __init__(self, project_name: str = "hepatotoxicity_review", 
                 model: str = "nb",  # Naive Bayes, or "svm", "rf", "nb"
                 feature_extraction: str = "tfidf"):  # "tfidf" or "doc2vec"
        """
        Initialize ASReview screener
        
        Args:
            project_name: Name for ASReview project
            model: Classification model ("nb", "svm", "rf", "logistic", "nn-2-layer")
            feature_extraction: Feature extraction method ("tfidf", "doc2vec")
        """
        if not ASREVIEW_AVAILABLE:
            raise ImportError("ASReview not available. Install with: pip install asreview")
        
        self.project_name = project_name
        self.model = model
        self.feature_extraction = feature_extraction
        self.project_path = None
        self.project = None
    
    def create_project(self, abstracts: List[Dict]) -> str:
        """
        Create ASReview project from abstracts
        
        Args:
            abstracts: List of dicts with 'title', 'abstract', 'pmid' keys
        
        Returns:
            Path to project directory
        """
        if not ASREVIEW_AVAILABLE:
            raise ImportError("ASReview not available")
        
        try:
            # Create temporary project directory
            temp_dir = tempfile.mkdtemp(prefix="asreview_")
            self.project_path = os.path.join(temp_dir, self.project_name)
            
            # Create project
            self.project = asr.Project.create_new(self.project_path)
            
            # Add records
            for abstract in abstracts:
                title = abstract.get('title', '')
                abstract_text = abstract.get('abstract', '')
                pmid = abstract.get('pmid', '')
                
                # Combine title and abstract
                full_text = f"{title}\n\n{abstract_text}"
                
                # Add record
                self.project.add_record(
                    text=full_text,
                    record_id=pmid,
                    title=title
                )
            
            logger.info(f"Created ASReview project with {len(abstracts)} records")
            return self.project_path
        
        except Exception as e:
            logger.error(f"Error creating ASReview project: {e}")
            raise
    
    def start_screening(self, initial_labels: Optional[List[Tuple[int, int]]] = None) -> Dict:
        """
        Start active learning screening
        
        Args:
            initial_labels: Optional list of (record_index, label) tuples for initial training
                          label: 1 = relevant, 0 = irrelevant
        
        Returns:
            Dictionary with screening results
        """
        if not self.project:
            raise ValueError("Project not created. Call create_project() first")
        
        try:
            # Label initial records if provided
            if initial_labels:
                for record_idx, label in initial_labels:
                    # Get record by index
                    records = list(self.project.records)
                    if record_idx < len(records):
                        record = records[record_idx]
                        self.project.label(record, label)
            
            # Start active learning simulation
            # In real usage, this would be interactive
            # For automation, we use ReviewSimulate
            results = {
                "screened": [],
                "relevant": [],
                "irrelevant": [],
                "remaining": []
            }
            
            # Get initial predictions
            with asr.ReviewSimulate(self.project, model=self.model, 
                                   feature_extraction=self.feature_extraction) as review:
                # Get first batch of predictions (sorted by relevance)
                for i, record in enumerate(review):
                    if i >= 10:  # Limit initial batch
                        break
                    
                    # In real usage, would present to user for labeling
                    # For now, return predictions
                    results["screened"].append({
                        "pmid": record.record_id,
                        "title": record.title,
                        "relevance_score": getattr(record, 'relevance_score', None),
                        "rank": i + 1
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error in ASReview screening: {e}")
            raise
    
    def get_next_record(self) -> Optional[Dict]:
        """
        Get the next record recommended by active learning
        
        Returns:
            Dictionary with record info, or None if no more records
        """
        if not self.project:
            return None
        
        try:
            with asr.ReviewSimulate(self.project, model=self.model,
                                   feature_extraction=self.feature_extraction) as review:
                for record in review:
                    return {
                        "pmid": record.record_id,
                        "title": record.title,
                        "abstract": getattr(record, 'abstract', ''),
                        "relevance_score": getattr(record, 'relevance_score', None)
                    }
        except Exception as e:
            logger.error(f"Error getting next record: {e}")
        
        return None
    
    def label_record(self, pmid: str, label: int) -> bool:
        """
        Label a record as relevant (1) or irrelevant (0)
        
        Args:
            pmid: PubMed ID
            label: 1 for relevant, 0 for irrelevant
        
        Returns:
            True if successful
        """
        if not self.project:
            return False
        
        try:
            # Find record by PMID
            for record in self.project.records:
                if record.record_id == pmid:
                    self.project.label(record, label)
                    logger.info(f"Labeled {pmid} as {'relevant' if label else 'irrelevant'}")
                    return True
        except Exception as e:
            logger.error(f"Error labeling record {pmid}: {e}")
        
        return False
    
    def get_statistics(self) -> Dict:
        """
        Get screening statistics
        
        Returns:
            Dictionary with stats
        """
        if not self.project:
            return {}
        
        try:
            total = len(list(self.project.records))
            labeled = len([r for r in self.project.records if r.label is not None])
            relevant = len([r for r in self.project.records if r.label == 1])
            irrelevant = len([r for r in self.project.records if r.label == 0])
            
            return {
                "total_records": total,
                "labeled": labeled,
                "relevant": relevant,
                "irrelevant": irrelevant,
                "remaining": total - labeled,
                "progress": labeled / total if total > 0 else 0.0
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def cleanup(self):
        """Clean up temporary project files"""
        if self.project_path and os.path.exists(self.project_path):
            import shutil
            try:
                shutil.rmtree(os.path.dirname(self.project_path))
                logger.info("Cleaned up ASReview project files")
            except Exception as e:
                logger.warning(f"Could not clean up project files: {e}")


def prioritize_abstracts_with_asreview(abstracts: List[Dict], 
                                       initial_relevant: Optional[List[int]] = None,
                                       initial_irrelevant: Optional[List[int]] = None,
                                       max_screening: int = 100) -> List[Dict]:
    """
    Prioritize abstracts using ASReview active learning
    
    Args:
        abstracts: List of abstract dicts with 'title', 'abstract', 'pmid'
        initial_relevant: Optional list of indices for initially labeled relevant abstracts
        initial_irrelevant: Optional list of indices for initially labeled irrelevant abstracts
        max_screening: Maximum number of abstracts to prioritize
    
    Returns:
        List of abstracts sorted by relevance (most relevant first)
    """
    if not ASREVIEW_AVAILABLE:
        logger.warning("ASReview not available, returning abstracts in original order")
        return abstracts
    
    try:
        screener = ASReviewScreener()
        screener.create_project(abstracts)
        
        # Label initial records
        initial_labels = []
        if initial_relevant:
            for idx in initial_relevant:
                initial_labels.append((idx, 1))
        if initial_irrelevant:
            for idx in initial_irrelevant:
                initial_labels.append((idx, 0))
        
        # Start screening
        results = screener.start_screening(initial_labels)
        
        # Get prioritized list
        prioritized = []
        screened_pmids = {r["pmid"] for r in results["screened"]}
        
        # Add screened records in priority order
        for result in results["screened"]:
            pmid = result["pmid"]
            # Find original abstract
            for abstract in abstracts:
                if abstract.get("pmid") == pmid:
                    abstract["asreview_rank"] = result["rank"]
                    abstract["relevance_score"] = result.get("relevance_score")
                    prioritized.append(abstract)
                    break
        
        # Add remaining abstracts
        for abstract in abstracts:
            if abstract.get("pmid") not in screened_pmids:
                prioritized.append(abstract)
        
        screener.cleanup()
        return prioritized[:max_screening]
    
    except Exception as e:
        logger.error(f"Error prioritizing with ASReview: {e}")
        return abstracts
