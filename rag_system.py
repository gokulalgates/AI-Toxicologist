"""
Retrieval-Augmented Generation (RAG) System
Retrieves similar abstracts/examples to provide context for LLM analysis
"""

from typing import List, Dict, Optional, Tuple
import json
import os
from pathlib import Path
import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Try to import sentence transformers, fallback to simple similarity if not available
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not installed. RAG will use simple text similarity.")


class RAGSystem:
    """Retrieval-Augmented Generation system for finding similar abstracts"""
    
    # Class-level flag to track if model has been loaded (to prevent duplicate prints)
    _model_loaded = False
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize RAG system
        
        Args:
            embedding_model: Name of sentence transformer model to use
        """
        self.embedding_model = None
        self.embeddings_available = EMBEDDINGS_AVAILABLE
        
        if EMBEDDINGS_AVAILABLE:
            try:
                # Only print once per process, even if multiple instances are created
                if not RAGSystem._model_loaded:
                    self.embedding_model = SentenceTransformer(embedding_model)
                    logger.info(f"Loaded embedding model: {embedding_model}")
                    RAGSystem._model_loaded = True
                else:
                    # Reuse the same model instance if already loaded
                    # Note: SentenceTransformer models are thread-safe and can be reused
                    self.embedding_model = SentenceTransformer(embedding_model)
            except Exception as e:
                if not RAGSystem._model_loaded:
                    logger.warning(f"Could not load embedding model: {e}")
                self.embeddings_available = False
        
        # Cache for embeddings
        self.embedding_cache = {}
        
        # Example database (can be populated from previous analyses)
        self.example_database = self._load_example_database()
    
    def _load_example_database(self) -> Dict[str, List[Dict]]:
        """Load example database from previous analyses"""
        example_db = {f"KC{i}": [] for i in range(1, 13)}
        
        # Try to load from results directory
        results_dir = Path("results")
        if results_dir.exists():
            for chemical_dir in results_dir.iterdir():
                study_records_file = chemical_dir / "study_records.jsonl"
                if study_records_file.exists():
                    try:
                        with open(study_records_file, 'r') as f:
                            for line in f:
                                record = json.loads(line)
                                kc_analysis = record.get("kc_analysis", {})
                                
                                # Extract examples for each KC
                                for kc in [f"KC{i}" for i in range(1, 13)]:
                                    kc_num = kc.replace("KC", "").lower()
                                    status_key = f"kc{kc_num}_status"
                                    status = kc_analysis.get(status_key, "NOT_MENTIONED")
                                    
                                    if status == "SUPPORTED":
                                        example = {
                                            "abstract": record.get("metadata", {}).get("title", ""),
                                            "analysis": kc_analysis,
                                            "pmid": record.get("metadata", {}).get("pmid", ""),
                                            "kc": kc,
                                            "status": status
                                        }
                                        example_db[kc].append(example)
                    except Exception as e:
                        logger.warning(f"Could not load examples from {study_records_file}: {e}")
                        continue
        
        return example_db
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Simple text similarity using word overlap (fallback when embeddings unavailable)"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _get_embedding(self, text: str) -> Optional[np.ndarray]:
        """Get embedding for text"""
        if not self.embeddings_available or self.embedding_model is None:
            return None
        
        # Check cache
        text_hash = hash(text[:100])  # Use hash of first 100 chars as key
        if text_hash in self.embedding_cache:
            return self.embedding_cache[text_hash]
        
        try:
            embedding = self.embedding_model.encode(text, convert_to_numpy=True)
            self.embedding_cache[text_hash] = embedding
            return embedding
        except Exception as e:
            logger.warning(f"Could not generate embedding: {e}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def find_similar_abstracts(
        self,
        abstract: str,
        chemical_name: str,
        kc: Optional[str] = None,
        top_k: int = 3
    ) -> List[Dict]:
        """
        Find similar abstracts from example database
        
        Args:
            abstract: Abstract text to find similarities for
            chemical_name: Chemical name (for filtering)
            kc: Optional KC to focus on
            top_k: Number of similar abstracts to return
        
        Returns:
            List of similar abstract dicts with similarity scores
        """
        similar_abstracts = []
        
        # If KC specified, search within that KC's examples
        kcs_to_search = [kc] if kc else [f"KC{i}" for i in range(1, 13)]
        
        for kc_search in kcs_to_search:
            examples = self.example_database.get(kc_search, [])
            
            for example in examples:
                example_text = example.get("abstract", "")
                if not example_text:
                    continue
                
                # Calculate similarity
                if self.embeddings_available:
                    abstract_emb = self._get_embedding(abstract)
                    example_emb = self._get_embedding(example_text)
                    
                    if abstract_emb is not None and example_emb is not None:
                        similarity = self._cosine_similarity(abstract_emb, example_emb)
                    else:
                        similarity = self._simple_similarity(abstract, example_text)
                else:
                    similarity = self._simple_similarity(abstract, example_text)
                
                similar_abstracts.append({
                    **example,
                    "similarity": similarity,
                    "matched_kc": kc_search
                })
        
        # Sort by similarity and return top_k
        similar_abstracts.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_abstracts[:top_k]
    
    def build_rag_context(
        self,
        abstract: str,
        chemical_name: str,
        kcs: Optional[List[str]] = None,
        top_k_per_kc: int = 2
    ) -> str:
        """
        Build RAG context string from similar abstracts
        
        Args:
            abstract: Current abstract
            chemical_name: Chemical name
            kcs: List of KCs to focus on (None = all)
            top_k_per_kc: Number of examples per KC
        
        Returns:
            Formatted context string
        """
        if kcs is None:
            kcs = [f"KC{i}" for i in range(1, 13)]
        
        context_parts = []
        
        for kc in kcs:
            similar = self.find_similar_abstracts(abstract, chemical_name, kc, top_k=top_k_per_kc)
            
            if similar:
                context_parts.append(f"\n### Similar Examples for {kc}:")
                for i, sim in enumerate(similar, 1):
                    context_parts.append(
                        f"{i}. PMID {sim.get('pmid', 'N/A')}: "
                        f"{sim.get('abstract', '')[:200]}... "
                        f"(Similarity: {sim['similarity']:.2f})"
                    )
        
        return "\n".join(context_parts) if context_parts else ""


# Global RAG instance
_rag_system: Optional[RAGSystem] = None


def get_rag_system() -> RAGSystem:
    """Get global RAG system instance"""
    global _rag_system
    if _rag_system is None:
        _rag_system = RAGSystem()
    return _rag_system


def add_to_example_database(
    abstract: str,
    analysis: Dict,
    metadata: Dict,
    kc: Optional[str] = None
) -> None:
    """Add a new example to the database"""
    rag = get_rag_system()
    
    if kc:
        kcs = [kc]
    else:
        # Extract all supported KCs
        kcs = []
        for i in range(1, 13):
            kc_name = f"KC{i}"
            kc_num = kc_name.replace("KC", "").lower()
            status_key = f"kc{kc_num}_status"
            if analysis.get(status_key) == "SUPPORTED":
                kcs.append(kc_name)
    
    for kc_name in kcs:
        example = {
            "abstract": abstract[:500],  # Store first 500 chars
            "analysis": analysis,
            "pmid": metadata.get("pmid", ""),
            "kc": kc_name,
            "status": analysis.get(f"kc{kc_name.replace('KC', '').lower()}_status", "NOT_MENTIONED")
        }
        rag.example_database[kc_name].append(example)
        
        # Limit database size (keep most recent 100 per KC)
        if len(rag.example_database[kc_name]) > 100:
            rag.example_database[kc_name] = rag.example_database[kc_name][-100:]
