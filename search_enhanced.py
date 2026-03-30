"""
Enhanced PubMed search with MeSH terms, CAS numbers, and multi-database support
Includes modular KC-specific queries and History Server batch retrieval
"""

from Bio import Entrez
from typing import List, Dict, Set, Optional, Tuple
import pubchempy as pcp
import time
import logging

logger = logging.getLogger(__name__)

# KC-specific search terms based on Rusyn et al. framework
KC_SEARCH_TERMS = {
    1: ["bioactivation", "reactive metabolite", "cytochrome P450", "CYP", "electrophile", 
        "covalent binding", "NAPQI", "quinone imine", "metabolic activation", "toxification"],
    2: ["apoptosis", "necrosis", "cell death", "cytotoxicity", "caspase", "TUNEL", 
        "hepatocellular necrosis", "hepatocyte death", "necroptosis", "pyroptosis"],
    3: ["proliferation", "regeneration", "cell cycle", "mitotic index", "Ki-67", "PCNA",
        "hepatocyte proliferation", "liver regeneration", "compensatory hyperplasia", "tissue repair"],
    4: ["transporter", "BSEP", "MDR3", "MRP", "efflux", "bile acid", "OATP", 
        "transport disruption", "bile salt export pump", "multidrug resistance"],
    5: ["oxidative stress", "ROS", "reactive oxygen species", "lipid peroxidation", 
        "glutathione", "GSH", "GSSG", "superoxide", "hydrogen peroxide", "oxidative damage"],
    6: ["immune", "inflammation", "cytokine", "Kupffer cell", "T-cell", "hypersensitivity",
        "immune-mediated", "TNF-alpha", "IL-6", "DRESS syndrome", "idiosyncratic"],
    7: ["mitochondrial", "ATP depletion", "respiration", "beta-oxidation", "MPTP",
        "mitochondrial permeability transition", "membrane potential", "uncoupling", 
        "respiratory chain", "mitochondrial dysfunction"],
    8: ["ER stress", "endoplasmic reticulum stress", "UPR", "unfolded protein response",
        "JNK", "MAPK", "stress signaling", "CHOP", "stress kinase", "kinase cascade"],
    9: ["cholestasis", "cholestatic", "bile acid", "bilirubin", "alkaline phosphatase",
        "bile duct injury", "bile flow", "hyperbilirubinemia"],
    10: ["cytoskeleton", "microtubule", "keratin", "actin", "ballooning degeneration",
         "Mallory-Denk bodies", "Mallory bodies", "cytoskeletal disruption"],
    11: ["fibrosis", "cirrhosis", "stellate cell", "collagen", "fibrogenesis",
         "ECM deposition", "extracellular matrix", "liver scarring"],
    12: ["steatosis", "fatty liver", "metabolic disruption", "lipid accumulation",
         "glycogen", "lipid metabolism", "phospholipidosis", "hyperammonemia"]
}


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
            except Exception as mesh_error:
                # MeSH lookup is optional, continue without it
                pass
            
    except Exception as e:
        logger.error(f"Error getting enhanced synonyms: {e}")
    
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
    
    logger.info(f"Enhanced PubMed query: {query[:200]}...")
    
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
        logger.error(f"Error in enhanced PubMed search: {e}")
        return {
            "pmids": [],
            "query_used": query,
            "search_log": {"error": str(e)},
            "synonyms": synonyms
        }


def build_chemical_query_part(chemical_synonyms: Dict[str, List[str]], max_terms: int = 15) -> str:
    """
    Build the chemical identification part of a query (without liver terms)
    Used for modular KC-specific queries
    """
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
    
    # Add MeSH term queries
    mesh_queries = []
    for mesh_term in chemical_synonyms['mesh_terms'][:3]:
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
    
    return "(" + " OR ".join(chemical_query_parts) + ")"


def build_kc_specific_query(chemical_synonyms: Dict[str, List[str]], kc_number: int, 
                           include_liver_terms: bool = True) -> str:
    """
    Build a PubMed query for a specific Key Characteristic
    
    Args:
        chemical_synonyms: Dictionary with chemical names, CAS, CIDs, MeSH terms
        kc_number: KC number (1-12)
        include_liver_terms: Whether to include liver/hepatotoxicity terms
    
    Returns:
        Complete PubMed query string
    """
    chemical_query = build_chemical_query_part(chemical_synonyms)
    
    # Get KC-specific terms
    kc_terms = KC_SEARCH_TERMS.get(kc_number, [])
    kc_query_parts = [f'"{term}"[Title/Abstract]' for term in kc_terms[:10]]  # Limit to 10 terms
    
    if not kc_query_parts:
        return ""
    
    kc_query = "(" + " OR ".join(kc_query_parts) + ")"
    
    # Liver/hepatotoxicity terms
    if include_liver_terms:
        liver_terms = [
            'liver[Title/Abstract]',
            'hepatotoxicity[Title/Abstract]',
            'hepatotoxic[Title/Abstract]',
            'DILI[Title/Abstract]',
            'drug-induced liver injury[Title/Abstract]',
            'Liver/chemically induced[MeSH Terms]',
            'Chemical and Drug Induced Liver Injury[MeSH Terms]'
        ]
        liver_query = "(" + " OR ".join(liver_terms) + ")"
        full_query = f"{chemical_query} AND {kc_query} AND {liver_query}"
    else:
        full_query = f"{chemical_query} AND {kc_query}"
    
    return full_query


def fetch_pubmed_by_kc(chemical_name: str, kc_number: int, max_results: int = 100,
                       use_history_server: bool = True) -> Dict:
    """
    Fetch PubMed results for a specific Key Characteristic
    
    Args:
        chemical_name: Name of the chemical
        kc_number: KC number (1-12)
        max_results: Maximum number of results to retrieve
        use_history_server: Whether to use History Server for batch retrieval
    
    Returns:
        Dictionary with pmids, webenv, query_key, kc tag, and query
    """
    Entrez.email = "ai.toxicologist@example.com"
    
    # Get enhanced synonyms
    synonyms = get_chemical_synonyms_enhanced(chemical_name)
    
    # Build KC-specific query
    query = build_kc_specific_query(synonyms, kc_number)
    
    if not query:
        logger.warning(f"Could not build query for KC{kc_number}")
        return {
            "pmids": [],
            "webenv": None,
            "query_key": None,
            "kc": f"KC{kc_number}",
            "query": "",
            "total_found": 0
        }
    
    logger.info(f"KC{kc_number} query: {query[:150]}...")
    
    try:
        if use_history_server:
            # Use History Server for efficient batch retrieval
            handle = Entrez.esearch(db="pubmed", term=query, retmax=0, usehistory="y")
            record = Entrez.read(handle)
            handle.close()
            
            webenv = record.get("WebEnv")
            query_key = record.get("QueryKey")
            total_found = int(record.get("Count", 0))
            
            # Get initial batch of PMIDs
            pmids = record.get("IdList", [])
            
            return {
                "pmids": pmids[:max_results],
                "webenv": webenv,
                "query_key": query_key,
                "kc": f"KC{kc_number}",
                "query": query,
                "total_found": total_found,
                "synonyms": synonyms
            }
        else:
            # Direct retrieval (fallback)
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results, usehistory="n")
            record = Entrez.read(handle)
            handle.close()
            
            pmids = record.get("IdList", [])
            total_found = int(record.get("Count", 0))
            
            return {
                "pmids": pmids,
                "webenv": None,
                "query_key": None,
                "kc": f"KC{kc_number}",
                "query": query,
                "total_found": total_found,
                "synonyms": synonyms
            }
    
    except Exception as e:
        logger.error(f"Error in KC{kc_number} PubMed search: {e}")
        return {
            "pmids": [],
            "webenv": None,
            "query_key": None,
            "kc": f"KC{kc_number}",
            "query": query,
            "total_found": 0,
            "error": str(e)
        }


def fetch_pubmed_all_kcs(chemical_name: str, max_results_per_kc: int = 100,
                         use_history_server: bool = True) -> Dict[str, Dict]:
    """
    Fetch PubMed results for all 12 Key Characteristics using modular queries
    
    Args:
        chemical_name: Name of the chemical
        max_results_per_kc: Maximum results per KC
        use_history_server: Whether to use History Server
    
    Returns:
        Dictionary mapping KC numbers to their search results
    """
    all_results = {}
    
    for kc_num in range(1, 13):
        logger.info(f"Fetching results for KC{kc_num}...")
        result = fetch_pubmed_by_kc(chemical_name, kc_num, max_results_per_kc, use_history_server)
        all_results[f"KC{kc_num}"] = result
        time.sleep(0.34)  # Rate limiting: ~3 requests/second
    
    return all_results


def fetch_batch_with_history_server(webenv: str, query_key: str, retstart: int = 0,
                                   retmax: int = 1000) -> List[str]:
    """
    Fetch a batch of PMIDs using History Server WebEnv/QueryKey
    
    Args:
        webenv: WebEnv token from esearch
        query_key: QueryKey from esearch
        retstart: Starting position (0-indexed)
        retmax: Number of records to retrieve
    
    Returns:
        List of PMIDs
    """
    try:
        handle = Entrez.efetch(db="pubmed", retstart=retstart, retmax=retmax,
                              webenv=webenv, query_key=query_key, rettype="medline", retmode="text")
        # Parse MEDLINE format to extract PMIDs
        content = handle.read()
        handle.close()
        
        import re
        pmids = re.findall(r'^PMID- (.+)$', content.decode('utf-8'), re.MULTILINE)
        return pmids
    
    except Exception as e:
        logger.error(f"Error fetching batch with History Server: {e}")
        return []


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


def merge_kc_results(kc_results: Dict[str, Dict]) -> Dict[str, any]:
    """
    Merge results from multiple KC queries, tagging each PMID with its KC labels
    
    Args:
        kc_results: Dictionary from fetch_pubmed_all_kcs()
    
    Returns:
        Dictionary with deduplicated PMIDs and their KC tags
    """
    pmid_to_kcs = {}  # Map PMID -> list of KCs
    
    # Collect all PMIDs and their KC tags
    for kc, result in kc_results.items():
        pmids = result.get("pmids", [])
        for pmid in pmids:
            if pmid not in pmid_to_kcs:
                pmid_to_kcs[pmid] = []
            pmid_to_kcs[pmid].append(kc)
    
    # Create merged result
    all_pmids = list(pmid_to_kcs.keys())
    
    return {
        "pmids": all_pmids,
        "pmid_to_kcs": pmid_to_kcs,  # For tagging at retrieval stage
        "kc_results": kc_results,
        "total_unique_pmids": len(all_pmids),
        "kc_coverage": {kc: len(result.get("pmids", [])) for kc, result in kc_results.items()}
    }
