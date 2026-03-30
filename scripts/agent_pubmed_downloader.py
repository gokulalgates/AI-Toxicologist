"""
PubMed abstract downloader for hepatotoxicity-related research.
Uses BioPython Entrez (already in codebase) for reliable downloads.
"""

import json
import os
import time
from typing import Dict, List

from Bio import Entrez

from config import get_config


class AgentPubMedDownloader:
    """Download abstracts from PubMed related to hepatotoxicity and Key Characteristics.
    Uses BioPython Entrez API.
    """

    def __init__(self, email=None, api_key=None):
        """
        Initialize PubMed downloader.
        
        Args:
            email (str): Email for Entrez API (required by NCBI)
            api_key (str): Optional API key for higher rate limits
        """
        config = get_config()
        self.email = email or config.search.entrez_email
        self.api_key = api_key

        # Set email for NCBI
        Entrez.email = self.email
        if self.api_key:
            Entrez.api_key = self.api_key

    def search_chemical_abstracts(self, chemical_name: str, max_results=200):
        """
        Search PubMed for abstracts related to a specific chemical and hepatotoxicity.
        
        Args:
            chemical_name (str): Name of the chemical to search for
            max_results (int): Maximum number of abstracts to retrieve
            
        Returns:
            list: List of abstract dictionaries
        """
        # Build query: chemical name + hepatotoxicity terms
        # Use quotes for exact phrase matching and handle synonyms
        chemical_query = f'"{chemical_name}" OR {chemical_name}'

        # Hepatotoxicity and mechanism terms
        hepatotoxicity_terms = "(hepatotoxicity OR liver toxicity OR hepatotoxic OR liver injury)"
        mechanism_terms = "(mechanism OR pathway OR biomarker OR mechanism of action)"

        # Combine into final query
        full_query = f"({chemical_query}) AND {hepatotoxicity_terms} AND {mechanism_terms}"

        print(f"Searching PubMed for: {chemical_name}")
        print(f"Query: {full_query}")
        print(f"Max results: {max_results}")

        # Search for PMIDs
        pmids = self._run_esearch(full_query, max_results=max_results)
        print(f"Found {len(pmids)} PubMed IDs for {chemical_name}")

        if not pmids:
            return []

        # Fetch abstracts in batches
        abstracts = self._fetch_abstracts_batch(pmids)

        return abstracts

    def search_hepatotoxicity_abstracts(self, max_results=1000, query_terms=None):
        """
        Search PubMed for hepatotoxicity-related abstracts.
        
        Args:
            max_results (int): Maximum number of abstracts to retrieve
            query_terms (list): Additional search terms to combine
            
        Returns:
            list: List of abstract dictionaries
        """
        # Base query for hepatotoxicity and Key Characteristics
        base_query = "(hepatotoxicity OR liver toxicity OR hepatotoxic) AND (mechanism OR pathway OR biomarker)"

        # Add KC-specific terms
        kc_terms = [
            "reactive metabolite",
            "apoptosis",
            "necrosis",
            "cell proliferation",
            "transport",
            "oxidative stress",
            "immune response",
            "mitochondrial dysfunction",
            "cholestasis",
            "cytoskeleton",
            "fibrosis",
            "metabolism"
        ]

        if query_terms:
            kc_terms.extend(query_terms)

        # Combine queries
        full_query = f"{base_query} AND ({' OR '.join(kc_terms)})"

        print(f"Searching PubMed with query: {full_query}")
        print(f"Max results: {max_results}")

        # Search for PMIDs
        pmids = self._run_esearch(full_query, max_results=max_results)
        print(f"Found {len(pmids)} PubMed IDs")

        if not pmids:
            return []

        # Fetch abstracts in batches
        abstracts = self._fetch_abstracts_batch(pmids)

        return abstracts

    def _run_esearch(self, query: str, max_results: int = 200) -> List[str]:
        """
        Run esearch to get PubMed IDs using BioPython Entrez.
        
        Args:
            query (str): PubMed search query
            max_results (int): Maximum number of results
            
        Returns:
            list: List of PubMed IDs
        """
        try:
            # Search PubMed
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            handle.close()

            pmids = record.get("IdList", [])
            return pmids[:max_results]

        except Exception as e:
            print(f"Error running esearch: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _fetch_abstracts_batch(self, pmids: List[str], batch_size=100):
        """
        Fetch abstracts in batches to avoid rate limiting.
        
        Args:
            pmids (list): List of PubMed IDs
            batch_size (int): Number of abstracts per batch
            
        Returns:
            list: List of abstract dictionaries
        """
        abstracts = []

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i + batch_size]
            print(f"Fetching batch {i//batch_size + 1}/{(len(pmids)-1)//batch_size + 1}...")

            try:
                # Fetch abstracts using efetch
                batch_abstracts = self._run_efetch(batch)
                abstracts.extend(batch_abstracts)

                # Rate limiting - be nice to NCBI
                time.sleep(0.34)  # ~3 requests per second

            except Exception as e:
                print(f"Error fetching batch: {str(e)}")
                continue

        print(f"Successfully downloaded {len(abstracts)} abstracts")
        return abstracts

    def _run_efetch(self, pmids: List[str]) -> List[Dict]:
        """
        Run efetch to get full records for PubMed IDs.
        
        Args:
            pmids (list): List of PubMed IDs
            
        Returns:
            list: List of parsed abstract dictionaries
        """
        if not pmids:
            return []

        try:
            # Fetch records
            handle = Entrez.efetch(db="pubmed", id=pmids, rettype="xml", retmode="xml")
            records = Entrez.read(handle)
            handle.close()

            # Parse records
            abstracts = []
            for record in records.get("PubmedArticle", []):
                abstract_data = self._parse_record(record)
                if abstract_data:
                    abstracts.append(abstract_data)

            return abstracts

        except Exception as e:
            print(f"Error running efetch: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _parse_record(self, record) -> Dict:
        """
        Parse a single PubmedArticle record.
        
        Args:
            record: PubmedArticle record from Entrez
            
        Returns:
            dict: Parsed abstract data or None
        """
        try:
            # Extract PMID
            pmid = ""
            if "MedlineCitation" in record and "PMID" in record["MedlineCitation"]:
                pmid = str(record["MedlineCitation"]["PMID"])

            # Extract title
            title = ""
            if "MedlineCitation" in record and "Article" in record["MedlineCitation"]:
                article = record["MedlineCitation"]["Article"]
                if "ArticleTitle" in article:
                    title = article["ArticleTitle"]

            # Extract abstract text
            abstract_text = ""
            if "MedlineCitation" in record and "Article" in record["MedlineCitation"]:
                article = record["MedlineCitation"]["Article"]
                if "Abstract" in article and "AbstractText" in article["Abstract"]:
                    abstract_parts = []
                    for text_elem in article["Abstract"]["AbstractText"]:
                        if isinstance(text_elem, dict):
                            label = text_elem.get("Label", "")
                            text = text_elem.get("AbstractText", "")
                            if text:
                                if label:
                                    abstract_parts.append(f"{label}: {text}")
                                else:
                                    abstract_parts.append(text)
                        else:
                            abstract_parts.append(str(text_elem))
                    abstract_text = " ".join(abstract_parts)

            # Extract authors
            authors = []
            if "MedlineCitation" in record and "Article" in record["MedlineCitation"]:
                article = record["MedlineCitation"]["Article"]
                if "AuthorList" in article:
                    for author in article["AuthorList"]:
                        last_name = author.get("LastName", "")
                        first_name = author.get("ForeName", "")
                        if last_name:
                            authors.append(f"{first_name} {last_name}".strip())

            # Extract journal
            journal = ""
            if "MedlineCitation" in record and "Article" in record["MedlineCitation"]:
                article = record["MedlineCitation"]["Article"]
                if "Journal" in article and "Title" in article["Journal"]:
                    journal = article["Journal"]["Title"]

            # Extract year
            year = ""
            if "MedlineCitation" in record and "Article" in record["MedlineCitation"]:
                article = record["MedlineCitation"]["Article"]
                if "Journal" in article and "JournalIssue" in article["Journal"]:
                    journal_issue = article["Journal"]["JournalIssue"]
                    if "PubDate" in journal_issue and "Year" in journal_issue["PubDate"]:
                        year = str(journal_issue["PubDate"]["Year"])

            # Extract keywords
            keywords = []
            if "MedlineCitation" in record and "KeywordList" in record["MedlineCitation"]:
                for kw_list in record["MedlineCitation"]["KeywordList"]:
                    if isinstance(kw_list, list):
                        keywords.extend([str(kw) for kw in kw_list])
                    else:
                        keywords.append(str(kw_list))

            if not abstract_text and not title:
                return None

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract_text,
                "authors": authors,
                "journal": journal,
                "year": year,
                "keywords": keywords,
                "full_text": f"{title}\n\n{abstract_text}"
            }

        except Exception as e:
            # Silently skip problematic records
            print(f"Warning: Could not parse record: {str(e)}")
            return None

    def save_abstracts(self, abstracts: List[Dict], filepath: str):
        """
        Save abstracts to a JSON file.
        
        Args:
            abstracts (list): List of abstract dictionaries
            filepath (str): Path to save JSON file
        """
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(abstracts, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(abstracts)} abstracts to {filepath}")

    def load_abstracts(self, filepath: str) -> List[Dict]:
        """
        Load abstracts from a JSON file.
        
        Args:
            filepath (str): Path to JSON file
            
        Returns:
            list: List of abstract dictionaries
        """
        if not os.path.exists(filepath):
            return []

        with open(filepath, encoding="utf-8") as f:
            abstracts = json.load(f)

        print(f"Loaded {len(abstracts)} abstracts from {filepath}")
        return abstracts
