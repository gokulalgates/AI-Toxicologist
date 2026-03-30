import os
import time
import json
import re
import logging
from typing import List, Dict, Tuple, Optional, Set, Union, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import pubchempy as pcp
from Bio import Entrez
from pydantic import BaseModel, Field
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.messages import SystemMessage

from config import get_config
from utils import retry_with_backoff, hash_text
from exceptions import (
    SearchError, ChemicalStandardizationError, LLMError, LLMTimeoutError,
    LLMParseError
)
from search_enhanced import fetch_pubmed_enhanced, get_chemical_synonyms_enhanced
from rag_system import get_rag_system
from prompt_templates import get_prompt_for_abstract  # kept for potential custom prompt modes
from prompt_improvements import (  # kept for potential custom prompt modes
    get_enhanced_prompt_with_synonyms, 
    get_acetaminophen_specific_prompt, 
    get_liberal_prompt
)
from causal_reasoning import enhance_causal_reasoning_prompt  # kept for potential custom prompt modes
from provenance import hash_prompt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = get_config()

KC_DEFINITIONS = {
    "KC1": "Is reactive and/or is metabolized (bioactivated) to reactive moieties.",
    "KC2": "Causes death (apoptosis and/or necrosis) of liver cells.",
    "KC3": "Affects liver cell proliferation and/or tissue regeneration.",
    "KC4": "Disrupts transport function.",
    "KC5": "Induces oxidative stress (imbalance between ROS and antioxidants).",
    "KC6": "Triggers immune-mediated responses in liver.",
    "KC7": "Causes mitochondrial dysfunction.",
    "KC8": "Activates stress signaling pathways.",
    "KC9": "Causes cholestasis.",
    "KC10": "Disrupts cellular cytoskeleton.",
    "KC11": "Causes liver fibrosis.",
    "KC12": "Disrupts liver metabolism, including of lipids and proteins."
}

KC_NAMES = {
    "KC1": "Reactive/Bioactivation",
    "KC2": "Cell Death",
    "KC3": "Proliferation/Regeneration",
    "KC4": "Transport Disruption",
    "KC5": "Oxidative Stress",
    "KC6": "Immune Response",
    "KC7": "Mitochondrial Dysfunction",
    "KC8": "Stress Signaling",
    "KC9": "Cholestasis",
    "KC10": "Cytoskeleton Disruption",
    "KC11": "Liver Fibrosis",
    "KC12": "Metabolism Disruption"
}

class CausalLink(BaseModel):
    """Represents a causal relationship between two KCs"""
    source: str = Field(description="Source KC (e.g., 'KC1')")
    target: str = Field(description="Target KC (e.g., 'KC5')")
    evidence: str = Field(description="Text evidence from abstract supporting this causal link")
    strength: str = Field(default="MODERATE", description="Strength: 'STRONG', 'MODERATE', or 'WEAK'")


class KCAnalysis(BaseModel):
    """Analysis of an abstract against Key Characteristics with causal reasoning"""
    kc1_status: str = Field(default="NOT_MENTIONED", description="KC1: Reactive/Bioactivation")
    kc2_status: str = Field(default="NOT_MENTIONED", description="KC2: Cell Death")
    kc3_status: str = Field(default="NOT_MENTIONED", description="KC3: Proliferation/Regeneration")
    kc4_status: str = Field(default="NOT_MENTIONED", description="KC4: Transport Disruption")
    kc5_status: str = Field(default="NOT_MENTIONED", description="KC5: Oxidative Stress")
    kc6_status: str = Field(default="NOT_MENTIONED", description="KC6: Immune Response")
    kc7_status: str = Field(default="NOT_MENTIONED", description="KC7: Mitochondrial Dysfunction")
    kc8_status: str = Field(default="NOT_MENTIONED", description="KC8: Stress Signaling")
    kc9_status: str = Field(default="NOT_MENTIONED", description="KC9: Cholestasis")
    kc10_status: str = Field(default="NOT_MENTIONED", description="KC10: Cytoskeleton Disruption")
    kc11_status: str = Field(default="NOT_MENTIONED", description="KC11: Liver Fibrosis")
    kc12_status: str = Field(default="NOT_MENTIONED", description="KC12: Metabolism Disruption")
    
    # Enhanced Toxicological Metadata
    species: str = Field(default="Unknown", description="Test species (e.g., 'Human', 'Rat', 'Mouse', 'In Vitro')")
    study_type: str = Field(default="Unknown", description="Study type (e.g., 'In Vivo', 'In Vitro', 'Clinical', 'Review')")
    
    reasoning: Union[str, Dict, List, Any] = Field(default="No reasoning provided", description="Step-by-step reasoning")
    causal_links: List[CausalLink] = Field(default_factory=list, description="List of causal relationships")
    dose_response: List[str] = Field(default_factory=list, description="Dose-response information")
    evidence_quotes: Dict[str, List[str]] = Field(default_factory=dict, description="Evidence quotes keyed by KC")

def _extract_balanced_json(text: str) -> Optional[str]:
    """Extract the first balanced JSON object from text using brace counting."""
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        c = text[i]
        if escape_next:
            escape_next = False
            continue
        if c == '\\' and in_string:
            escape_next = True
            continue
        if c == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None


def _build_empty_analysis(reason: str = "No analysis available") -> Dict:
    """Build an empty analysis dict with all KCs set to NOT_MENTIONED"""
    result = {}
    for i in range(1, 13):
        kc_key = f"KC{i}"
        result[kc_key] = False
        result[f"{kc_key}_status"] = "NOT_MENTIONED"
        result[f"kc{i}_status"] = "NOT_MENTIONED"
    result["reasoning"] = reason
    result["species"] = "Unknown"
    result["study_type"] = "Unknown"
    result["causal_links"] = []
    result["dose_response"] = []
    result["evidence_quotes"] = {}
    return result


def standardize_chemical_name(chemical_name: str) -> Tuple[str, Optional[str], List[str]]:
    """Standardize chemical name using PubChem and get synonyms"""
    chemical_name = chemical_name.lower()
    try:
        compounds = pcp.get_compounds(chemical_name, 'name')
        if compounds:
            compound = compounds[0]
            standardized_name = compound.iupac_name or compound.synonyms[0] if compound.synonyms else chemical_name
            cid = str(compound.cid)
            search_terms = [chemical_name]
            
            if compound.synonyms:
                common_names = []
                for s in compound.synonyms[:30]:
                    if (len(s) < 80 and not s.startswith('4-[') and not s.startswith('(') and
                        not s.replace('.', '').replace('-', '').isdigit() and s not in search_terms):
                        common_names.append(s)
                        if len(common_names) >= 5:
                            break
                search_terms.extend(common_names)
            
            if standardized_name != chemical_name and standardized_name not in search_terms:
                search_terms.append(standardized_name)
            
            return standardized_name, cid, search_terms[:config.search.max_search_terms]
        return chemical_name, None, [chemical_name]
    except Exception as e:
        error_msg = f"Error standardizing chemical name: {e}"
        logger.warning(error_msg)
        if config.debug:
            raise ChemicalStandardizationError(error_msg) from e
        return chemical_name, None, [chemical_name]

def check_relevance(abstract_text: str, title: str, chemical_name: str, model_name: str = "llama3.1") -> bool:
    """Check if abstract is relevant to liver toxicity"""
    try:
        llm = ChatOllama(
            model=model_name, 
            temperature=config.llm.temperature_relevance,
            timeout=config.search.llm_timeout
        )
        
        SYSTEM_PROMPT_GATEKEEPER = """### TASK
Determine if the following abstract is relevant to studying the effects of '{chemical_name}' (or any of its synonyms/trade names) on the **LIVER**.

A paper is relevant if it discusses ANY of the following in relation to the liver:
- Toxicity, adverse effects, or safety concerns
- Mechanisms of action (e.g., oxidative stress, bioactivation, metabolism)
- Cell death, inflammation, fibrosis, cholestasis, or mitochondrial effects
- In vivo or in vitro hepatotoxicity studies
- Drug-induced liver injury (DILI)
- Hepatocyte or liver cell experiments
- Liver biomarkers (ALT, AST, bilirubin, etc.)

The chemical may appear under common names, trade names, abbreviations, or chemical identifiers.

### OUTPUT
Answer with a single word: "YES" or "NO".

Title: {title}
Abstract: {abstract_text}"""
        
        truncate_len = config.search.relevance_check_truncate
        prompt = SYSTEM_PROMPT_GATEKEEPER.format(
            chemical_name=chemical_name,
            title=title,
            abstract_text=abstract_text[:truncate_len]
        )
        
        response = llm.invoke(prompt)
        answer = response.content.strip().upper()
        
        is_relevant = "YES" in answer and "NO" not in answer[:10]
        if not is_relevant:
            is_relevant = answer.startswith("Y") and not answer.startswith("NO")
        
        logger.info(f"Relevance check for '{title[:50]}...': {answer[:20]} -> {'RELEVANT' if is_relevant else 'EXCLUDED'}")
        return is_relevant
    
    except Exception as e:
        logger.warning(f"Relevance check failed for '{title[:50]}...', including abstract by default: {e}")
        return True

COMPACT_SYSTEM_PROMPT = """You are a toxicology expert. Analyze the abstract for ALL hepatotoxicity mechanisms present.

IMPORTANT: Check EVERY KC carefully. Many abstracts describe multiple mechanisms. Mark ALL that apply as SUPPORTED.

KC1: Reactive/Bioactivation - metabolism, reactive metabolite, NAPQI, CYP450, CYP2E1, CYP3A4, bioactivation, electrophile, phase I, hydroxylation, glucuronidation, sulfation
KC2: Cell Death - apoptosis, necrosis, hepatocyte death, liver injury, cytotoxicity, cell killing, caspase, TUNEL, ALT elevation, AST elevation, hepatocellular damage
KC3: Proliferation/Regeneration - cell proliferation, regeneration, mitosis, compensatory hyperplasia, liver repair, hepatocyte recovery, cell cycle, Ki-67, PCNA, growth factor
KC4: Transport Disruption - transporter, bile acid transport, BSEP, MRP, OATP, uptake, efflux, P-glycoprotein, ABC transporter, drug accumulation
KC5: Oxidative Stress - ROS, reactive oxygen, glutathione depletion, GSH, lipid peroxidation, antioxidant, SOD, catalase, Nrf2, MDA, redox, thioredoxin, 4-HNE
KC6: Immune Response - inflammation, inflammatory, cytokines, TNF-alpha, IL-1beta, IL-6, neutrophils, Kupffer cells, macrophages, immune, NF-kB, innate immunity, adaptive immunity, sterile inflammation, DAMPs, TLR
KC7: Mitochondrial Dysfunction - mitochondria, mitochondrial damage, ATP depletion, membrane potential, MPT, electron transport chain, respiratory chain, cytochrome c release, mitochondrial swelling, Bcl-2
KC8: Stress Signaling - JNK, c-Jun, MAPK, p38, NF-kB, ERK, kinase, signaling pathway, stress response, ER stress, UPR, unfolded protein, ASK1, RIPK
KC9: Cholestasis - cholestasis, bile flow, bile accumulation, cholestatic, bilirubin elevation, jaundice
KC10: Cytoskeleton Disruption - cytoskeleton, keratin, actin, microtubules, cell morphology, Mallory-Denk bodies, ballooning
KC11: Liver Fibrosis - fibrosis, collagen, stellate cells, ECM, scarring, cirrhosis, TGF-beta, alpha-SMA
KC12: Metabolism Disruption - lipid metabolism, steatosis, fatty acid, protein synthesis, metabolic disruption, lipid accumulation, triglycerides, ammonia, urea cycle, gluconeogenesis

Return ONLY valid JSON with ALL 12 KC statuses. Example:
{"kc1_status":"SUPPORTED","kc2_status":"SUPPORTED","kc3_status":"NOT_MENTIONED","kc4_status":"NOT_MENTIONED","kc5_status":"SUPPORTED","kc6_status":"SUPPORTED","kc7_status":"SUPPORTED","kc8_status":"SUPPORTED","kc9_status":"NOT_MENTIONED","kc10_status":"NOT_MENTIONED","kc11_status":"NOT_MENTIONED","kc12_status":"SUPPORTED","reasoning":"KC1: metabolized by CYP2E1 to NAPQI. KC2: causes hepatocellular necrosis. KC5: depletes GSH causing oxidative stress. KC6: activates inflammatory response. KC7: mitochondrial dysfunction. KC8: JNK activation. KC12: disrupts lipid metabolism","species":"Mouse","study_type":"In Vivo"}"""


def _extract_kc_statuses_regex(text: str) -> Optional[Dict]:
    """Last-resort extraction: scan text for KC status mentions using regex."""
    result = {}
    for i in range(1, 13):
        pattern = rf'"?kc{i}_status"?\s*:\s*"?(SUPPORTED|REFUTED|NOT_MENTIONED|ASSOCIATED|CAUSALLY_LINKED)"?'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result[f"kc{i}_status"] = match.group(1).upper()
    if len(result) >= 6:
        for i in range(1, 13):
            result.setdefault(f"kc{i}_status", "NOT_MENTIONED")
        return result
    return None


@retry_with_backoff(exceptions=(LLMError, LLMTimeoutError, Exception))
def analyze_abstract_with_llm(abstract_text: str, title: str, model_name: str = "llama3.1", 
                              prompt_hash: Optional[str] = None, fulltext: Optional[str] = None,
                              chemical_name: Optional[str] = None, use_rag: bool = True,
                              use_hierarchical: bool = True, search_terms: Optional[List[str]] = None,
                              prompt_mode: Optional[str] = None, custom_prompt: Optional[str] = None) -> Tuple[Dict, str]:
    """Analyze abstract against 12 KC definitions using LLM.
    
    Uses a compact prompt optimized for small local models (llama3.2 3B).
    Falls back through multiple parsing strategies: JSON -> regex extraction.
    """
    try:
        llm = ChatOllama(
            model=model_name,
            temperature=config.llm.temperature,
            timeout=config.search.llm_timeout,
        )
        
        text_to_analyze = abstract_text
        if use_hierarchical and fulltext:
            text_to_analyze = fulltext[:config.search.abstract_truncate_length]

        system_prompt = COMPACT_SYSTEM_PROMPT
        current_prompt_hash = prompt_hash or hash_prompt(system_prompt)
        
        system_message_object = SystemMessage(content=system_prompt)
        prompt_template = ChatPromptTemplate.from_messages([
            system_message_object,
            ("human", "Title: {title}\n\nAbstract: {abstract}\n\nReturn ONLY the JSON."),
        ])
        
        chain = prompt_template | llm
        raw_response = chain.invoke({
            "title": title,
            "abstract": text_to_analyze[:4000]
        })
        
        response_text = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
        
        cleaned_text = re.sub(r'```json\s*', '', response_text)
        cleaned_text = re.sub(r'```\s*', '', cleaned_text)
        cleaned_text = cleaned_text.strip()
        
        refusal_phrases = ["i can't do that", "i cannot", "i'm unable", "i am unable", "as an ai"]
        if any(phrase in cleaned_text.lower() for phrase in refusal_phrases) and '{' not in cleaned_text:
            logger.warning(f"LLM refused to analyze: {cleaned_text[:100]}")
            return _build_empty_analysis(f"LLM refused: {cleaned_text[:200]}"), current_prompt_hash
        
        json_data = None
        
        # Strategy 1: Extract balanced JSON and parse
        json_str = _extract_balanced_json(cleaned_text)
        if json_str:
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                fixed = re.sub(r',\s*}', '}', json_str)
                fixed = re.sub(r',\s*]', ']', fixed)
                try:
                    json_data = json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        
        # Strategy 2: Try full cleaned text as JSON
        if json_data is None:
            try:
                json_data = json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Regex extraction of individual KC statuses from raw text
        if json_data is None:
            logger.warning(f"JSON parsing failed, trying regex extraction: {cleaned_text[:150]}...")
            regex_result = _extract_kc_statuses_regex(cleaned_text)
            if regex_result:
                json_data = regex_result
                logger.info("Regex extraction recovered KC statuses")
        
        if json_data is None:
            logger.warning(f"All parsing strategies failed for: {cleaned_text[:200]}...")
            return _build_empty_analysis(f"Parse failed: {cleaned_text[:100]}..."), current_prompt_hash
        
        # Normalize: the LLM may return nested or extra fields - extract what we need
        kc_dict = {}
        for i in range(1, 13):
            kc_key = f"KC{i}"
            status = (
                json_data.get(f"kc{i}_status")
                or json_data.get(f"KC{i}_status")
                or json_data.get(f"kc{i}")
                or json_data.get(kc_key)
                or "NOT_MENTIONED"
            )
            if isinstance(status, bool):
                status = "SUPPORTED" if status else "NOT_MENTIONED"
            status = str(status).upper().strip().strip('"')
            if status not in ("SUPPORTED", "REFUTED", "NOT_MENTIONED", "ASSOCIATED", "CAUSALLY_LINKED"):
                status = "SUPPORTED" if any(w in status.lower() for w in ("support", "yes", "true", "present")) else "NOT_MENTIONED"
            
            kc_dict[kc_key] = status == "SUPPORTED"
            kc_dict[f"{kc_key}_status"] = status
            kc_dict[f"kc{i}_status"] = status
        
        reasoning = json_data.get("reasoning", "")
        if isinstance(reasoning, dict):
            reasoning = json.dumps(reasoning)
        elif isinstance(reasoning, list):
            reasoning = "; ".join(str(r) for r in reasoning)
        kc_dict["reasoning"] = reasoning or "No reasoning provided"
        kc_dict["species"] = str(json_data.get("species", "Unknown"))
        kc_dict["study_type"] = str(json_data.get("study_type", "Unknown"))
        kc_dict["dose_response"] = json_data.get("dose_response", [])
        if not isinstance(kc_dict["dose_response"], list):
            kc_dict["dose_response"] = []
        kc_dict["evidence_quotes"] = json_data.get("evidence_quotes", {})
        if not isinstance(kc_dict["evidence_quotes"], dict):
            kc_dict["evidence_quotes"] = {}
        
        raw_links = json_data.get("causal_links", [])
        if isinstance(raw_links, list):
            kc_dict["causal_links"] = [
                {"source": l.get("source", ""), "target": l.get("target", ""),
                 "evidence": l.get("evidence", ""), "strength": l.get("strength", "MODERATE")}
                for l in raw_links if isinstance(l, dict)
            ]
        else:
            kc_dict["causal_links"] = []
        
        supported_count = sum(1 for i in range(1, 13) if kc_dict.get(f"kc{i}_status") == "SUPPORTED")
        logger.info(f"Analysis complete: {supported_count}/12 KCs supported for '{title[:50]}...'")
        
        return kc_dict, current_prompt_hash

    except (LLMError, LLMTimeoutError) as e:
        logger.error(f"LLM error analyzing abstract: {e}")
        raise e
    except Exception as e:
        logger.error(f"Error in analyze_abstract_with_llm: {e}")
        return _build_empty_analysis(f"Error: {str(e)}"), prompt_hash or "error"

def fetch_pubmed_abstracts(search_terms: List[str], max_results: Optional[int] = None) -> Tuple[List[Dict[str, str]], Dict]:
    """Fetch abstracts from PubMed using enhanced MeSH-aware search"""
    if max_results is None:
        max_results = config.search.max_abstracts_initial
    
    Entrez.email = config.search.entrez_email
    
    try:
        synonyms = get_chemical_synonyms_enhanced(search_terms[0] if search_terms else "")
        search_result = fetch_pubmed_enhanced(search_terms[0] if search_terms else "", max_results=max_results)
        pmids = search_result.get("pmids", [])
        search_log = search_result.get("search_log", {})
        
        if not pmids:
            search_names = [name for name in search_terms if len(name) < 80]
            if not search_names:
                search_names = search_terms[:3]
            
            name_query = " OR ".join([f'"{name}"[Title/Abstract]' for name in search_names[:5]])
            query = f'({name_query}) AND (liver OR hepatotoxicity)'
            
            handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
            record = Entrez.read(handle)
            handle.close()
            pmids = record["IdList"]
            search_log = {"query": query, "method": "fallback"}
        
        if not pmids:
            return [], search_log
        
        handle = Entrez.efetch(db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        abstracts = []
        for record in records["PubmedArticle"]:
            try:
                article = record["MedlineCitation"]["Article"]
                title = article["ArticleTitle"]
                
                abstract_text = ""
                if "Abstract" in article:
                    abstract_list = article["Abstract"]["AbstractText"]
                    if isinstance(abstract_list, list):
                        abstract_text = " ".join([str(item) for item in abstract_list])
                    else:
                        abstract_text = str(abstract_list)
                
                pmid = str(record["MedlineCitation"]["PMID"])
                
                year = None
                authors = None
                journal = None
                
                try:
                    if "PubDate" in article:
                        pub_date = article["PubDate"]
                        if "Year" in pub_date:
                            year = int(pub_date["Year"])
                except (KeyError, ValueError, TypeError):
                    pass
                
                try:
                    if "AuthorList" in article:
                        author_list = article["AuthorList"]
                        if author_list:
                            authors = ", ".join([f"{a.get('LastName', '')}, {a.get('ForeName', '')}" 
                                               for a in author_list[:3]])
                except (KeyError, AttributeError, TypeError):
                    pass
                
                try:
                    if "Journal" in article:
                        journal = article["Journal"].get("Title", "")
                except (KeyError, AttributeError, TypeError):
                    pass
                
                if abstract_text.strip():
                    abstracts.append({
                        "title": title,
                        "abstract": abstract_text,
                        "pmid": pmid,
                        "year": year,
                        "authors": authors,
                        "journal": journal
                    })
            except Exception as e:
                logger.warning(f"Error parsing article: {e}")
                continue
        
        return abstracts, search_log
    
    except Exception as e:
        error_msg = f"Error fetching PubMed abstracts: {e}"
        logger.error(error_msg)
        if config.debug:
            raise SearchError(error_msg) from e
        return [], {"error": str(e)}