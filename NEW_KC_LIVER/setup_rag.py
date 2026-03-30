#!/usr/bin/env python3
"""
Setup script to initialize RAG system with PubMed abstracts.
Run this before using the main agent to download and index abstracts.
"""

import os
from pubmed_downloader import PubMedDownloader
from rag_system import RAGSystem


def main():
    """Setup RAG system by downloading abstracts and generating embeddings."""
    print("=" * 70)
    print("RAG System Setup for Hepatotoxicity Agent")
    print("=" * 70)
    print()
    
    # Get email for NCBI
    email = input("Enter your email for NCBI Entrez API (required): ").strip()
    if not email:
        print("Error: Email is required for NCBI API.")
        return
    
    # Get number of abstracts
    max_results_input = input("Max abstracts to download (default 1000, recommended 500-2000): ").strip()
    max_results = int(max_results_input) if max_results_input.isdigit() else 1000
    
    print(f"\nStep 1: Downloading {max_results} abstracts from PubMed...")
    downloader = PubMedDownloader(email=email)
    abstracts = downloader.search_hepatotoxicity_abstracts(max_results=max_results)
    
    if not abstracts:
        print("Error: No abstracts downloaded. Please check your network connection and try again.")
        return
    
    # Save abstracts
    abstracts_file = "pubmed_abstracts.json"
    downloader.save_abstracts(abstracts, abstracts_file)
    
    print(f"\nStep 2: Initializing RAG system...")
    rag = RAGSystem(top_k=5)
    rag.load_abstracts(abstracts_file)
    
    print(f"\nStep 3: Generating embeddings (this may take several minutes)...")
    print("Note: Make sure you have pulled the embedding model:")
    print("  ollama pull nomic-embed-text")
    print()
    
    rag.generate_embeddings()
    
    embeddings_file = "embeddings.npy"
    rag.save_embeddings(embeddings_file)
    
    print("\n" + "=" * 70)
    print("Setup complete! RAG system is ready to use.")
    print(f"  - Abstracts: {abstracts_file} ({len(abstracts)} abstracts)")
    print(f"  - Embeddings: {embeddings_file}")
    print("=" * 70)


if __name__ == "__main__":
    main()
