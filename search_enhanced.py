"""
Enhanced PubMed search with MeSH terms, CAS numbers, and multi-database support
"""

from __future__ import annotations

import time
from typing import Dict, List

import pubchempy as pcp
from Bio import Entrez


def get_chemical_synonyms_enhanced(chemical_name: str) -> Dict[str, List[str]]:
    """
    Get comprehensive synonyms including CAS numbers, MeSH terms, and common names
    Returns: dict with 'names', 'cas_numbers', 'cids', 'mesh_terms'
    """
    synonyms = {
        'names': [chemical_name],
        'cas_numbers': [],
        'cids': [],
        'mesh_terms': []
    }

    try:
        compounds = pcp.get_compounds(chemical_name, 'name')
        if compounds:
            compound = compounds[0]

            # Get CID
            if compound.cid:
                synonyms['cids'].append(str(compound.cid))

            # Get common names (filtered)
            if compound.synonyms:
                common_names = [s for s in compound.synonyms[:30]
                              if len(s) < 80 and
                              not s.startswith('4-[') and
                              not s.startswith('(') and
                              not s.replace('.', '').replace('-', '').isdigit()]
                synonyms['names'].extend(common_names[:10])

            # Get CAS numbers if available
            if hasattr(compound, 'synonyms'):
                for syn in compound.synonyms:
                    # CAS numbers are typically in format: 123-45-6 or 12345-67-8
                    if '-' in syn and len(syn.split('-')) == 3:
                        parts = syn.split('-')
                        if all(p.isdigit() for p in parts):
                            synonyms['cas_numbers'].append(syn)
                            break  # Usually only one CAS number

            # Try to get MeSH term for the chemical itself
            # Query PubMed to find MeSH terms associated with this chemical
            try:
                Entrez.email = "ai.toxicologist@example.com"
                # Search for the chemical and get MeSH terms from a representative paper
                search_handle = Entrez.esearch(db="pubmed", term=f'"{compound.cid}"[UID] OR "{chemical_name}"[Title/Abstract]', retmax=5)
                search_results = Entrez.read(search_handle)
                search_handle.close()

                if search_results["IdList"]:
                    # Get details for first result to extract MeSH terms
                    fetch_handle = Entrez.efetch(db="pubmed", id=search_results["IdList"][0], rettype="medline", retmode="text")
                    medline_text = fetch_handle.read()
                    fetch_handle.close()

                    # Extract MeSH terms (format: MH  - Term)
                    import re
                    mesh_pattern = r'MH\s+-\s+(.+?)(?:\n|$)'
                    mesh_matches = re.findall(mesh_pattern, medline_text.decode('utf-8', errors='ignore'))
                    # Filter for chemical-specific MeSH terms (not general terms like "Humans", "Animals")
                    chemical_mesh = [m.strip() for m in mesh_matches
                                    if m.strip() and m.strip() not in ["Humans", "Animals", "Male", "Female", "Adult", "Rats", "Mice"]]
                    if chemical_mesh:
                        synonyms['mesh_terms'] = chemical_mesh[:3]  # Take up to 3 MeSH terms
            except Exception:
                # MeSH lookup is optional, continue without it
                pass

    except Exception as e:
        print(f"Error getting enhanced synonyms: {e}")

    return synonyms


def build_mesh_aware_query(chemical_synonyms: Dict[str, List[str]],
                          max_terms: int = 15) -> str:
    """
    Build a MeSH-aware PubMed query with synonyms, CAS numbers, and MeSH terms
    """
    Entrez.email = "ai.toxicologist@example.com"

    # Build name query (Title/Abstract)
    name_terms = chemical_synonyms['names'][:max_terms]
    name_query = " OR ".join([f'"{name}"[Title/Abstract]' for name in name_terms])

    # Add CAS number queries
    cas_queries = []
    for cas in chemical_synonyms['cas_numbers'][:3]:
        cas_queries.append(f'"{cas}"[All Fields]')

    # Add CID queries
    cid_queries = []
    for cid in chemical_synonyms['cids'][:2]:
        cid_queries.append(f'"{cid}"[All Fields]')

    # Add MeSH term queries for the chemical itself (IMPROVEMENT #1)
    mesh_queries = []
    for mesh_term in chemical_synonyms['mesh_terms'][:3]:  # Use up to 3 MeSH terms
        # Use MeSH Major Topic if available, otherwise regular MeSH
        mesh_queries.append(f'"{mesh_term}"[MeSH Terms]')
        mesh_queries.append(f'"{mesh_term}"[MeSH Major Topic]')

    # Combine all chemical identifiers
    chemical_query_parts = [name_query]
    if cas_queries:
        chemical_query_parts.append(" OR ".join(cas_queries))
    if cid_queries:
        chemical_query_parts.append(" OR ".join(cid_queries))
    if mesh_queries:
        chemical_query_parts.append("(" + " OR ".join(mesh_queries) + ")")

    chemical_query = "(" + " OR ".join(chemical_query_parts) + ")"

    # Liver/hepatotoxicity terms with MeSH
    liver_terms = [
        'liver[Title/Abstract]',
        'hepatotoxicity[Title/Abstract]',
        'hepatotoxic[Title/Abstract]',
        'DILI[Title/Abstract]',
        'drug-induced liver injury[Title/Abstract]',
        'Liver/chemically induced[MeSH Terms]',
        'Chemical and Drug Induced Liver Injury[MeSH Terms]',
        'Cholestasis/chemically induced[MeSH Terms]',
        'Liver Diseases/chemically induced[MeSH Terms]'
    ]

    liver_query = "(" + " OR ".join(liver_terms) + ")"

    # Combine
    full_query = f"{chemical_query} AND {liver_query}"

    return full_query


def fetch_pubmed_enhanced(chemical_name: str, max_results: int = 50) -> Dict:
    """
    Enhanced PubMed search with MeSH awareness and comprehensive synonym handling
    Returns: dict with 'pmids', 'query_used', 'search_log'
    """
    Entrez.email = "ai.toxicologist@example.com"

    # Get enhanced synonyms
    synonyms = get_chemical_synonyms_enhanced(chemical_name)

    # Build query
    query = build_mesh_aware_query(synonyms)

    print(f"Enhanced PubMed query: {query[:200]}...")

    try:
        # Search PubMed
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, usehistory="y")
        record = Entrez.read(handle)
        handle.close()

        pmids = record["IdList"]
        total_found = int(record["Count"])

        search_log = {
            "query": query,
            "total_found": total_found,
            "retrieved": len(pmids),
            "synonyms_used": {
                "names": synonyms['names'][:10],
                "cas_numbers": synonyms['cas_numbers'],
                "cids": synonyms['cids']
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        return {
            "pmids": pmids,
            "query_used": query,
            "search_log": search_log,
            "synonyms": synonyms
        }

    except Exception as e:
        print(f"Error in enhanced PubMed search: {e}")
        return {
            "pmids": [],
            "query_used": query,
            "search_log": {"error": str(e)},
            "synonyms": synonyms
        }


def deduplicate_pmids(pmid_lists: List[List[str]]) -> List[str]:
    """
    Deduplicate PMIDs from multiple databases
    """
    seen = set()
    deduplicated = []

    for pmid_list in pmid_lists:
        for pmid in pmid_list:
            if pmid not in seen:
                seen.add(pmid)
                deduplicated.append(pmid)

    return deduplicated
