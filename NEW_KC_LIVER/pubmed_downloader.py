#!/usr/bin/env python3
"""
PubMed abstract downloader for hepatotoxicity-related research.
Uses Entrez Direct (E-utilities) command-line tools for reliable downloads.
"""

import time
import subprocess
from typing import List, Dict
import json
import os
import xml.etree.ElementTree as ET


class PubMedDownloader:
    """Download abstracts from PubMed related to hepatotoxicity and Key Characteristics.
    Uses Entrez Direct (E-utilities) command-line tools.
    """
    
    def __init__(self, email="your.email@example.com", api_key=None):
        """
        Initialize PubMed downloader.
        
        Args:
            email (str): Email for Entrez API (required by NCBI)
            api_key (str): Optional API key for higher rate limits
        """
        self.email = email
        self.api_key = api_key
        
        # Check if Entrez Direct tools are available
        self._check_entrez_tools()
    
    def _check_entrez_tools(self):
        """Check if Entrez Direct tools (esearch, efetch) are available."""
        try:
            result = subprocess.run(
                ["which", "esearch"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("Warning: Entrez Direct tools not found.")
                print("Install with: conda install -c bioconda entrez-direct")
                print("Or download from: https://www.ncbi.nlm.nih.gov/books/NBK179288/")
                raise RuntimeError("Entrez Direct tools (esearch, efetch) are required")
        except FileNotFoundError:
            print("Warning: 'which' command not found. Assuming Entrez Direct is available.")
    
    def _run_esearch(self, query: str, max_results: int = 200) -> List[str]:
        """
        Run esearch to get PubMed IDs using Entrez Direct.
        Uses esearch | efetch pipeline to get UIDs.
        
        Args:
            query (str): PubMed search query
            max_results (int): Maximum number of results
            
        Returns:
            list: List of PubMed IDs
        """
        # Entrez Direct: esearch outputs XML with WebEnv/QueryKey
        # Then pipe to efetch to get UIDs
        # Format: esearch -db pubmed -query "term" | efetch -format uid | head -N
        
        # Set email for NCBI
        env = os.environ.copy()
        env["ENTREZ_EMAIL"] = self.email
        if self.api_key:
            env["ENTREZ_API_KEY"] = self.api_key
        
        try:
            # Step 1: Run esearch to get WebEnv/QueryKey
            esearch_cmd = [
                "esearch",
                "-db", "pubmed",
                "-query", query
            ]
            
            esearch_result = subprocess.run(
                esearch_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            if esearch_result.returncode != 0:
                print(f"Error running esearch: {esearch_result.stderr}")
                return []
            
            # Parse XML to get WebEnv and QueryKey
            root = ET.fromstring(esearch_result.stdout)
            webenv_elem = root.find(".//WebEnv")
            query_key_elem = root.find(".//QueryKey")
            
            if webenv_elem is None or query_key_elem is None:
                print("Error: Could not get WebEnv/QueryKey from esearch")
                return []
            
            webenv = webenv_elem.text
            query_key = query_key_elem.text
            
            # Step 2: Use efetch with WebEnv/QueryKey to get UIDs (limited)
            efetch_cmd = [
                "efetch",
                "-db", "pubmed",
                "-query_key", query_key,
                "-WebEnv", webenv,
                "-retstart", "0",
                "-retmax", str(max_results),
                "-format", "uid"
            ]
            
            efetch_result = subprocess.run(
                efetch_cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=60
            )
            
            if efetch_result.returncode != 0:
                print(f"Error fetching UIDs: {efetch_result.stderr}")
                return []
            
            # Parse UIDs (one per line, whitespace-separated)
            pmids = []
            for line in efetch_result.stdout.strip().split('\n'):
                pmids.extend([uid.strip() for uid in line.split() if uid.strip()])
            
            return pmids[:max_results]
            
        except subprocess.TimeoutExpired:
            print("esearch timed out")
            return []
        except ET.ParseError as e:
            print(f"Error parsing esearch output: {str(e)}")
            return []
        except Exception as e:
            print(f"Error running esearch: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
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
        
        # Join PMIDs with commas
        pmid_string = ",".join(pmids)
        
        cmd = [
            "efetch",
            "-db", "pubmed",
            "-id", pmid_string,
            "-format", "xml"
        ]
        
        # Set email for NCBI
        env = os.environ.copy()
        env["ENTREZ_EMAIL"] = self.email
        if self.api_key:
            env["ENTREZ_API_KEY"] = self.api_key
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env,
                timeout=120
            )
            
            if result.returncode != 0:
                print(f"Error running efetch: {result.stderr}")
                return []
            
            # Parse XML output
            abstracts = self._parse_xml_records(result.stdout)
            return abstracts
            
        except subprocess.TimeoutExpired:
            print("efetch timed out")
            return []
        except Exception as e:
            print(f"Error running efetch: {str(e)}")
            return []
    
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
        
        # Search for PMIDs using Entrez Direct
        pmids = self._run_esearch(full_query, max_results=max_results)
        print(f"Found {len(pmids)} PubMed IDs")
        
        if not pmids:
            return []
        
        # Fetch abstracts in batches
        abstracts = self._fetch_abstracts_batch(pmids)
        
        return abstracts
    
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
    
    def _parse_xml_records(self, xml_content: str) -> List[Dict]:
        """
        Parse XML content from efetch into abstract dictionaries.
        
        Args:
            xml_content (str): XML content from efetch
            
        Returns:
            list: List of abstract dictionaries
        """
        abstracts = []
        
        try:
            root = ET.fromstring(xml_content)
            
            # Find all PubmedArticle elements
            for article_elem in root.findall(".//PubmedArticle"):
                abstract_data = self._parse_xml_article(article_elem)
                if abstract_data:
                    abstracts.append(abstract_data)
                    
        except ET.ParseError as e:
            print(f"Error parsing XML: {str(e)}")
        except Exception as e:
            print(f"Error parsing records: {str(e)}")
        
        return abstracts
    
    def _parse_xml_article(self, article_elem) -> Dict:
        """
        Parse a single PubmedArticle XML element.
        
        Args:
            article_elem: XML element for PubmedArticle
            
        Returns:
            dict: Parsed abstract data or None
        """
        try:
            # Extract PMID
            pmid_elem = article_elem.find(".//PMID")
            pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ""
            
            # Extract title
            title_elem = article_elem.find(".//ArticleTitle")
            title = title_elem.text if title_elem is not None and title_elem.text else ""
            
            # Extract abstract text
            abstract_text = ""
            abstract_elem = article_elem.find(".//Abstract")
            if abstract_elem is not None:
                abstract_parts = []
                for text_elem in abstract_elem.findall(".//AbstractText"):
                    label = text_elem.get("Label", "")
                    text = text_elem.text if text_elem.text else ""
                    if text:
                        if label:
                            abstract_parts.append(f"{label}: {text}")
                        else:
                            abstract_parts.append(text)
                abstract_text = " ".join(abstract_parts)
            
            # Extract authors
            authors = []
            author_list = article_elem.find(".//AuthorList")
            if author_list is not None:
                for author in author_list.findall(".//Author"):
                    last_name_elem = author.find("LastName")
                    first_name_elem = author.find("ForeName")
                    last_name = last_name_elem.text if last_name_elem is not None and last_name_elem.text else ""
                    first_name = first_name_elem.text if first_name_elem is not None and first_name_elem.text else ""
                    if last_name:
                        authors.append(f"{first_name} {last_name}".strip())
            
            # Extract journal
            journal = ""
            journal_elem = article_elem.find(".//Journal/Title")
            if journal_elem is not None and journal_elem.text:
                journal = journal_elem.text
            
            # Extract year
            year = ""
            year_elem = article_elem.find(".//PubDate/Year")
            if year_elem is not None and year_elem.text:
                year = year_elem.text
            
            # Extract keywords
            keywords = []
            keyword_list = article_elem.find(".//KeywordList")
            if keyword_list is not None:
                for keyword in keyword_list.findall(".//Keyword"):
                    if keyword.text:
                        keywords.append(keyword.text)
            
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
        
        with open(filepath, "r", encoding="utf-8") as f:
            abstracts = json.load(f)
        
        print(f"Loaded {len(abstracts)} abstracts from {filepath}")
        return abstracts


if __name__ == "__main__":
    # Example usage
    downloader = PubMedDownloader(email="your.email@example.com")
    abstracts = downloader.search_hepatotoxicity_abstracts(max_results=500)
    downloader.save_abstracts(abstracts, "pubmed_abstracts.json")
