#!/usr/bin/env python3
"""
RAG (Retrieval-Augmented Generation) system for hepatotoxicity agent.
Uses vector embeddings for semantic search over PubMed abstracts.
"""

import json
import os
import numpy as np
from typing import List, Dict, Tuple, Optional
import ollama
import subprocess


class RAGSystem:
    """Retrieval-Augmented Generation system using Ollama embeddings."""
    
    def __init__(self, embedding_model="nomic-embed-text", top_k=5):
        """
        Initialize RAG system.
        
        Args:
            embedding_model (str): Ollama embedding model name
            top_k (int): Number of top documents to retrieve
        """
        self.embedding_model = embedding_model
        self.top_k = top_k
        self.abstracts = []
        self.embeddings = None
        self.embedding_dim = None
        self.use_embeddings = True
        
        # Check and ensure embedding model is available
        self._ensure_embedding_model()
    
    def _ensure_embedding_model(self):
        """Check if embedding model exists, try to pull if not."""
        try:
            # Try to generate a test embedding to check if model exists
            test_response = ollama.embeddings(model=self.embedding_model, prompt="test")
            self.embedding_dim = len(test_response["embedding"])
            print(f"Embedding model '{self.embedding_model}' is available (dim={self.embedding_dim})")
        except Exception as e:
            print(f"Embedding model '{self.embedding_model}' not found. Attempting to pull...")
            try:
                # Try to pull the model
                result = subprocess.run(
                    ["ollama", "pull", self.embedding_model],
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )
                if result.returncode == 0:
                    print(f"Successfully pulled embedding model '{self.embedding_model}'")
                    # Test again
                    test_response = ollama.embeddings(model=self.embedding_model, prompt="test")
                    self.embedding_dim = len(test_response["embedding"])
                else:
                    print(f"Failed to pull model. Error: {result.stderr}")
                    print("Falling back to keyword-based search (no embeddings)")
                    self.use_embeddings = False
            except Exception as pull_error:
                print(f"Error pulling model: {str(pull_error)}")
                print("Falling back to keyword-based search (no embeddings)")
                self.use_embeddings = False
    
    def load_abstracts(self, filepath: str):
        """
        Load abstracts from JSON file.
        
        Args:
            filepath (str): Path to JSON file with abstracts
        """
        if not os.path.exists(filepath):
            print(f"Warning: File {filepath} not found. Run pubmed_downloader.py first.")
            return
        
        with open(filepath, "r", encoding="utf-8") as f:
            self.abstracts = json.load(f)
        
        print(f"Loaded {len(self.abstracts)} abstracts into RAG system")
    
    def add_abstracts(self, abstracts: List[Dict]):
        """
        Add abstracts to the RAG system.
        
        Args:
            abstracts (list): List of abstract dictionaries
        """
        self.abstracts.extend(abstracts)
        print(f"Added {len(abstracts)} abstracts. Total: {len(self.abstracts)}")
    
    def generate_embeddings(self, start_index=0):
        """
        Generate embeddings for abstracts.
        
        Args:
            start_index (int): Index to start from (for incremental updates)
        """
        if not self.use_embeddings:
            print("Embeddings disabled, using keyword-based search instead")
            return
        
        if not self.abstracts:
            print("No abstracts to embed")
            return
        
        # Initialize embeddings array if needed
        if self.embeddings is None:
            embeddings = []
        else:
            embeddings = self.embeddings.tolist()
        
        num_new = len(self.abstracts) - start_index
        if num_new <= 0:
            print("No new abstracts to embed")
            return
        
        print(f"Generating embeddings for {num_new} new abstracts...")
        
        for i in range(start_index, len(self.abstracts)):
            if (i + 1) % 10 == 0:
                print(f"Embedding progress: {i + 1 - start_index}/{num_new}")
            
            abstract = self.abstracts[i]
            # Use full text for embedding
            text = abstract.get("full_text", abstract.get("abstract", ""))
            
            try:
                # Generate embedding using Ollama
                response = ollama.embeddings(model=self.embedding_model, prompt=text)
                embedding = response["embedding"]
                
                if self.embedding_dim is None:
                    self.embedding_dim = len(embedding)
                
                embeddings.append(embedding)
                
            except Exception as e:
                print(f"Error generating embedding for abstract {i}: {str(e)}")
                # Use zero vector as fallback
                if self.embedding_dim:
                    embeddings.append([0.0] * self.embedding_dim)
                else:
                    # Try to get dimension from model
                    try:
                        test_response = ollama.embeddings(model=self.embedding_model, prompt="test")
                        self.embedding_dim = len(test_response["embedding"])
                        embeddings.append([0.0] * self.embedding_dim)
                    except:
                        print("Could not determine embedding dimension, disabling embeddings")
                        self.use_embeddings = False
                        return
        
        self.embeddings = np.array(embeddings)
        print(f"Generated embeddings with shape: {self.embeddings.shape}")
    
    def retrieve_relevant_abstracts(self, query: str) -> List[Dict]:
        """
        Retrieve most relevant abstracts for a query.
        Uses embeddings if available, otherwise falls back to keyword search.
        
        Args:
            query (str): User query
            
        Returns:
            list: List of relevant abstract dictionaries
        """
        if not self.abstracts:
            print("Warning: No abstracts available.")
            return []
        
        # Use keyword-based search if embeddings are not available
        if not self.use_embeddings or self.embeddings is None:
            return self._keyword_search(query)
        
        try:
            # Generate query embedding
            response = ollama.embeddings(model=self.embedding_model, prompt=query)
            query_embedding = np.array(response["embedding"])
            
            # Calculate cosine similarity
            # Normalize embeddings
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
            doc_norms = self.embeddings / (np.linalg.norm(self.embeddings, axis=1, keepdims=True) + 1e-8)
            
            # Compute similarities
            similarities = np.dot(doc_norms, query_norm)
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:self.top_k]
            
            # Return top abstracts with scores
            results = []
            for idx in top_indices:
                abstract = self.abstracts[idx].copy()
                abstract["similarity_score"] = float(similarities[idx])
                results.append(abstract)
            
            return results
            
        except Exception as e:
            print(f"Error retrieving abstracts with embeddings: {str(e)}")
            print("Falling back to keyword-based search")
            return self._keyword_search(query)
    
    def _keyword_search(self, query: str) -> List[Dict]:
        """
        Fallback keyword-based search when embeddings are not available.
        
        Args:
            query (str): User query
            
        Returns:
            list: List of relevant abstract dictionaries
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        scored_abstracts = []
        for i, abstract in enumerate(self.abstracts):
            score = 0.0
            full_text = abstract.get("full_text", "").lower()
            title = abstract.get("title", "").lower()
            abstract_text = abstract.get("abstract", "").lower()
            
            # Score based on word matches
            for word in query_words:
                if len(word) < 3:  # Skip very short words
                    continue
                # Title matches are worth more
                if word in title:
                    score += 3.0
                # Abstract matches
                if word in abstract_text:
                    score += 1.0
                # Full text matches
                if word in full_text:
                    score += 0.5
            
            if score > 0:
                abstract_copy = abstract.copy()
                abstract_copy["similarity_score"] = score
                scored_abstracts.append((score, abstract_copy))
        
        # Sort by score and return top-k
        scored_abstracts.sort(key=lambda x: x[0], reverse=True)
        results = [abstract for _, abstract in scored_abstracts[:self.top_k]]
        
        return results
    
    def format_context(self, abstracts: List[Dict]) -> str:
        """
        Format retrieved abstracts into context string.
        
        Args:
            abstracts (list): List of abstract dictionaries
            
        Returns:
            str: Formatted context string
        """
        if not abstracts:
            return ""
        
        context_parts = ["RELEVANT RESEARCH EVIDENCE FROM PUBMED:\n"]
        
        for i, abstract in enumerate(abstracts, 1):
            pmid = abstract.get("pmid", "N/A")
            title = abstract.get("title", "")
            abstract_text = abstract.get("abstract", "")
            year = abstract.get("year", "")
            journal = abstract.get("journal", "")
            score = abstract.get("similarity_score", 0.0)
            
            context_parts.append(f"[{i}] PMID: {pmid} | Year: {year} | Journal: {journal} | Relevance: {score:.3f}")
            context_parts.append(f"Title: {title}")
            context_parts.append(f"Abstract: {abstract_text[:500]}...")  # Truncate long abstracts
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def save_embeddings(self, filepath: str):
        """Save embeddings to file."""
        if self.embeddings is None:
            print("No embeddings to save")
            return
        
        np.save(filepath, self.embeddings)
        print(f"Saved embeddings to {filepath}")
    
    def load_embeddings(self, filepath: str):
        """Load embeddings from file."""
        if not os.path.exists(filepath):
            print(f"Embeddings file {filepath} not found")
            return
        
        self.embeddings = np.load(filepath)
        print(f"Loaded embeddings with shape: {self.embeddings.shape}")


if __name__ == "__main__":
    # Example usage
    rag = RAGSystem()
    rag.load_abstracts("pubmed_abstracts.json")
    rag.generate_embeddings()
    rag.save_embeddings("embeddings.npy")
