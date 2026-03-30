"""
Full-text article retrieval for systematic reviews
Supports PMC (PubMed Central) API, AWS S3 bulk download, DOI resolution, and JATS XML parsing
"""

import requests
import time
import io
import pdfplumber
import os
import logging
from typing import Optional, Dict, Tuple, List
from Bio import Entrez
from exceptions import SearchError
from config import get_config
from utils import retry_with_backoff

logger = logging.getLogger(__name__)

# Try to import pubmed_parser for JATS XML parsing
try:
    import pubmed_parser as pp
    PUBMED_PARSER_AVAILABLE = True
except ImportError:
    PUBMED_PARSER_AVAILABLE = False
    logger.warning("pubmed_parser not available. Install with: pip install pubmed-parser")

# Try to import boto3 for AWS S3 access
try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not available. Install with: pip install boto3")

# Set up a requests session with a user-agent to mimic a browser
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

def get_pmc_id_from_pmid(pmid: str) -> Optional[str]:
    """
    Get PMC ID from PMID using Entrez API
    
    Args:
        pmid: PubMed ID
        
    Returns:
        PMC ID if available, None otherwise
    """
    try:
        Entrez.email = get_config().search.entrez_email
        handle = Entrez.elink(dbfrom="pubmed", db="pmc", linkname="pubmed_pmc", id=pmid)
        record = Entrez.read(handle)
        handle.close()
        
        if record and len(record) > 0 and len(record[0]["LinkSetDb"]) > 0:
            pmc_ids = record[0]["LinkSetDb"][0]["Link"]
            if pmc_ids:
                # Extract PMC ID (format: PMC123456)
                pmc_id = pmc_ids[0]["Id"]
                return pmc_id
    except Exception as e:
        logger.error(f"Error getting PMC ID for PMID {pmid}: {e}")
    
    return None


def get_doi_from_pmid(pmid: str) -> Optional[str]:
    """
    Get DOI from PMID using Entrez API
    
    Args:
        pmid: PubMed ID
        
    Returns:
        DOI if available, None otherwise
    """
    try:
        Entrez.email = get_config().search.entrez_email
        handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
        record = Entrez.read(handle)
        handle.close()
        
        if record and "PubmedArticle" in record:
            article = record["PubmedArticle"][0]
            if "MedlineCitation" in article:
                medline = article["MedlineCitation"]
                if "Article" in medline:
                    article_data = medline["Article"]
                    if "ELocationID" in article_data:
                        for eloc in article_data["ELocationID"]:
                            if eloc.attributes.get("EIdType") == "doi":
                                return eloc
    except Exception as e:
        logger.error(f"Error getting DOI for PMID {pmid}: {e}")
    
    return None


@retry_with_backoff(max_retries=3, delay=1.0)
def fetch_pmc_fulltext(pmc_id: str) -> Optional[str]:
    """
    Fetch full-text article from PMC using their API
    
    Args:
        pmc_id: PMC ID (e.g., "PMC123456" or "123456")
        
    Returns:
        Full-text XML content if available, None otherwise
    """
    # Remove "PMC" prefix if present
    pmc_id_clean = pmc_id.replace("PMC", "")
    
    try:
        # PMC API endpoint for full-text XML
        url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id=PMC{pmc_id_clean}"
        response = session.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse response to get download link
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.content)
        
        # Check if article is open access
        records = root.findall(".//record")
        if records:
            for record in records:
                # Get download link
                link = record.find(".//link[@format='xml']")
                if link is not None:
                    xml_url = link.get("href")
                    if xml_url:
                        # Download full-text XML
                        xml_response = session.get(xml_url, timeout=60)
                        xml_response.raise_for_status()
                        return xml_response.text
        
        # Try alternative: direct PMC XML fetch
        alt_url = f"https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi?verb=GetRecord&identifier=oai:pubmedcentral.nih.gov:{pmc_id_clean}&metadataPrefix=pmc"
        alt_response = session.get(alt_url, timeout=30)
        if alt_response.status_code == 200:
            return alt_response.text
            
    except Exception as e:
        logger.error(f"Error fetching PMC full-text for {pmc_id}: {e}")
    
    return None


def extract_text_from_pmc_xml(pmc_xml: str) -> Optional[str]:
    """
    Extract plain text from PMC XML.
    Uses pubmed_parser if available, otherwise uses robust manual extraction.
    
    Args:
        pmc_xml: PMC XML content
        
    Returns:
        Extracted text (abstract + body) or None
    """
    # Strategy 1: Use pubmed_parser if available (most robust)
    if PUBMED_PARSER_AVAILABLE:
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(pmc_xml)
                temp_path = f.name
            
            try:
                paragraphs = pp.parse_pubmed_paragraph(temp_path)
                full_text_parts = []
                for p in paragraphs:
                    text = p.get('text', '').strip()
                    if text:
                        # Optionally prepend section title
                        section = p.get('section', '')
                        if section and section.lower() not in ['paragraph', 'unknown']:
                             # full_text_parts.append(f"[{section.upper()}] {text}")
                             full_text_parts.append(text)
                        else:
                             full_text_parts.append(text)
                
                if full_text_parts:
                    return "\n\n".join(full_text_parts)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        except Exception as e:
            logger.warning(f"pubmed_parser failed, falling back to manual extraction: {e}")

    # Strategy 2: Robust Manual Extraction (Recursive)
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(pmc_xml)
        
        parts = []
        
        # Helper to recursively get text from an element
        def get_all_text(element):
            return "".join(element.itertext()).strip()

        # 1. Extract Abstract
        for abstract in root.findall(".//abstract"):
            text = get_all_text(abstract)
            if text:
                parts.append(f"ABSTRACT:\n{text}")
        
        # 2. Extract Body
        # Find all paragraphs in body, regardless of nesting
        body_parts = []
        body_found = False
        for body in root.findall(".//body"):
            body_found = True
            # Method A: Find all 'p' tags recursively
            p_tags = body.findall(".//p")
            if p_tags:
                for p in p_tags:
                    text = get_all_text(p)
                    if text:
                        body_parts.append(text)
            else:
                 # Method B: If no 'p' tags found, just get all text from body
                 text = get_all_text(body)
                 if text:
                     body_parts.append(text)
        
        if body_parts:
            parts.append("BODY:\n" + "\n\n".join(body_parts))
        elif not body_found:
             # Fallback for some XMLs that might not have a body tag but have other content?
             # Unlikely for JATS, but let's check for direct text at root
             pass
            
        full_text = "\n\n".join(parts)
        if full_text.strip():
            return full_text.strip()
            
    except Exception as e:
        logger.error(f"Error extracting text from PMC XML: {e}")
    
    return None


def _extract_text_from_pdf(pdf_content: bytes, doi: str) -> Optional[str]:
    """Helper to extract text from PDF content."""
    try:
        with io.BytesIO(pdf_content) as pdf_file:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())
        
        if full_text and full_text.strip():
            logger.info(f"Successfully extracted text from PDF for DOI {doi}")
            return full_text.strip()
        else:
            logger.warning(f"PDF for DOI {doi} was empty or text could not be extracted.")
            return None
    except Exception as e:
        logger.error(f"Error processing PDF for DOI {doi}: {e}")
        return None


def _find_pdf_link_in_html(html_content: str, base_url: str) -> Optional[str]:
    """
    Try to find a PDF download link in HTML content.
    
    Common patterns:
    - Links with href ending in .pdf
    - Links with text like "Download PDF", "Full Text PDF", etc.
    - Meta tags with PDF URLs
    """
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin, urlparse
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for direct PDF links
        pdf_links = soup.find_all('a', href=True)
        for link in pdf_links:
            href = link.get('href', '')
            text = link.get_text().lower()
            
            # Check if href points to PDF
            if href.lower().endswith('.pdf'):
                full_url = urljoin(base_url, href)
                return full_url
            
            # Check if link text suggests PDF
            if any(keyword in text for keyword in ['pdf', 'download', 'full text']):
                if '.pdf' in href.lower() or 'pdf' in href.lower():
                    full_url = urljoin(base_url, href)
                    return full_url
        
        # Look for meta tags
        meta_tags = soup.find_all('meta', attrs={'name': True})
        for meta in meta_tags:
            content = meta.get('content', '')
            if '.pdf' in content.lower():
                full_url = urljoin(base_url, content)
                return full_url
        
        # Look for iframe sources (some publishers embed PDFs)
        iframes = soup.find_all('iframe', src=True)
        for iframe in iframes:
            src = iframe.get('src', '')
            if '.pdf' in src.lower():
                full_url = urljoin(base_url, src)
                return full_url
                
    except ImportError:
        # BeautifulSoup not available, skip HTML parsing
        logger.warning("BeautifulSoup not available, skipping HTML parsing for PDF links")
    except Exception as e:
        logger.error(f"Error parsing HTML for PDF links: {e}")
    
    return None

@retry_with_backoff(max_retries=2, delay=1.0)
def fetch_fulltext_via_doi(doi: str) -> Optional[str]:
    """
    Attempt to fetch full-text via DOI by finding an open-access PDF link or trying direct download.
    
    Args:
        doi: DOI string
        
    Returns:
        Full-text content if available, None otherwise
    """
    doi_clean = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
    
    # 1. Try Unpaywall API to find an OA PDF link
    try:
        logger.info(f"Attempting Unpaywall for DOI: {doi_clean}")
        unpaywall_url = f"https://api.unpaywall.org/v2/{doi_clean}?email={get_config().search.entrez_email}"
        response = session.get(unpaywall_url, timeout=30)
        
        # Handle 422 errors gracefully (Unpaywall may reject some DOIs)
        if response.status_code == 422:
            logger.info(f"Unpaywall returned 422 for DOI {doi_clean} (DOI may not be in Unpaywall database)")
        else:
            response.raise_for_status()
            data = response.json()
            
            pdf_url = None
            if data.get("is_oa", False):
                oa_locations = data.get("oa_locations", [])
                for location in oa_locations:
                    if location.get("url_for_pdf"):
                        pdf_url = location.get("url_for_pdf")
                        break
            
            if pdf_url:
                logger.info(f"Found OA PDF link via Unpaywall: {pdf_url}")
                pdf_response = session.get(pdf_url, timeout=60)
                pdf_response.raise_for_status()
                return _extract_text_from_pdf(pdf_response.content, doi)

    except requests.exceptions.HTTPError as e:
        # Don't fail on HTTP errors from Unpaywall (422, 404, etc.)
        if e.response.status_code in [422, 404, 429]:
            logger.warning(f"Unpaywall request failed for DOI {doi}: {e.response.status_code} {e.response.reason}")
        else:
            logger.error(f"Unpaywall request failed for DOI {doi}: {e}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Unpaywall request failed for DOI {doi}: {e}")
    except Exception as e:
        logger.error(f"Error processing Unpaywall response for DOI {doi}: {e}")

    # 2. Fallback: Try downloading directly from the DOI resolver
    try:
        logger.info(f"Unpaywall failed or found no OA link. Attempting direct download for DOI: {doi_clean}")
        direct_url = f"https://doi.org/{doi_clean}"
        # The session will follow redirects to the PDF
        direct_response = session.get(direct_url, timeout=60, allow_redirects=True)
        direct_response.raise_for_status()

        # Check if the content is a PDF
        content_type = direct_response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            logger.info("Direct download returned a PDF. Extracting text.")
            return _extract_text_from_pdf(direct_response.content, doi)
        elif 'text/html' in content_type:
            # Try to parse HTML to find PDF links
            logger.info("Direct download returned HTML. Attempting to find PDF link...")
            pdf_url = _find_pdf_link_in_html(direct_response.text, direct_response.url)
            if pdf_url:
                logger.info(f"Found PDF link in HTML: {pdf_url}")
                pdf_response = session.get(pdf_url, timeout=60)
                pdf_response.raise_for_status()
                if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                    return _extract_text_from_pdf(pdf_response.content, doi)
            else:
                logger.info("Could not find PDF link in HTML. Content-Type: %s", content_type)
                logger.info("This may require institutional access. Full-text retrieval will use abstract only.")
        else:
            logger.info("Direct download did not return a PDF. Content-Type: %s", content_type)
            
    except requests.exceptions.RequestException as e:
        logger.warning(f"Direct download failed for DOI {doi}: {e}")
    except Exception as e:
        logger.error(f"Error processing direct download for DOI {doi}: {e}")

    return None


def fetch_fulltext(pmid: str, prefer_pmc: bool = True) -> Tuple[Optional[str], str]:
    """
    Fetch full-text article for a given PMID
    
    Args:
        pmid: PubMed ID
        prefer_pmc: If True, prefer PMC over other sources
        
    Returns:
        Tuple of (full_text, source) where source is "pmc", "doi", or "none"
    """
    full_text = None
    source = "none"
    
    # Try PMC first (most reliable for open access articles)
    if prefer_pmc:
        try:
            pmc_id = get_pmc_id_from_pmid(pmid)
            if pmc_id:
                pmc_xml = fetch_pmc_fulltext(pmc_id)
                if pmc_xml:
                    full_text = extract_text_from_pmc_xml(pmc_xml)
                    if full_text:
                        source = "pmc"
                        logger.info(f"Retrieved full-text from PMC for PMID {pmid}")
                        return full_text, source
        except Exception as e:
            logger.error(f"PMC retrieval failed for {pmid}: {e}")
    
    # Try DOI-based retrieval as fallback
    if not full_text:
        try:
            doi = get_doi_from_pmid(pmid)
            if doi:
                full_text = fetch_fulltext_via_doi(doi)
                if full_text:
                    source = "doi"
                    logger.info(f"Retrieved full-text via DOI for PMID {pmid}")
                    return full_text, source
        except Exception as e:
            logger.error(f"DOI retrieval failed for {pmid}: {e}")
    
    return None, source


def has_fulltext_available(pmid: str) -> bool:
    """
    Check if full-text is likely available for a PMID
    
    Args:
        pmid: PubMed ID
        
    Returns:
        True if full-text appears to be available, False otherwise
    """
    pmc_id = get_pmc_id_from_pmid(pmid)
    if pmc_id:
        return True
    
    doi = get_doi_from_pmid(pmid)
    if doi:
        # Check if DOI points to open access source
        # (simplified check - could be enhanced)
        return True
    
    return False


# ============================================================================
# JATS XML Parsing with pubmed_parser (Section-Aware Extraction)
# ============================================================================

def extract_sections_from_pmc_xml(pmc_xml_path: str) -> Dict[str, List[str]]:
    """
    Extract sections from PMC XML using pubmed_parser (JATS-aware)
    
    Args:
        pmc_xml_path: Path to PMC XML file
    
    Returns:
        Dictionary with sections: abstract, introduction, methods, results, discussion, conclusions
    """
    if not PUBMED_PARSER_AVAILABLE:
        logger.warning("pubmed_parser not available, falling back to custom parsing")
        # Fallback: try to parse from XML string if provided
        if isinstance(pmc_xml_path, str) and pmc_xml_path.startswith('<?xml'):
            return _extract_sections_fallback(pmc_xml_path)
        return {}
    
    try:
        paragraphs = pp.parse_pubmed_paragraph(pmc_xml_path)
        
        sections = {
            "abstract": [],
            "introduction": [],
            "methods": [],
            "results": [],
            "discussion": [],
            "conclusions": [],
            "other": []
        }
        
        for para in paragraphs:
            section_name = para.get('section', '').lower()
            text = para.get('text', '').strip()
            
            if not text:
                continue
            
            if 'abstract' in section_name or 'summary' in section_name:
                sections["abstract"].append(text)
            elif 'introduction' in section_name or 'background' in section_name:
                sections["introduction"].append(text)
            elif 'method' in section_name or 'materials' in section_name:
                sections["methods"].append(text)
            elif 'result' in section_name or 'finding' in section_name:
                sections["results"].append(text)
            elif 'discussion' in section_name:
                sections["discussion"].append(text)
            elif 'conclusion' in section_name:
                sections["conclusions"].append(text)
            else:
                sections["other"].append(text)
        
        return sections
    
    except Exception as e:
        logger.error(f"Error extracting sections with pubmed_parser: {e}")
        return {}


def extract_tables_from_pmc_xml(pmc_xml_path: str) -> List[Dict]:
    """
    Extract tables from PMC XML using pubmed_parser
    
    Args:
        pmc_xml_path: Path to PMC XML file
    
    Returns:
        List of dictionaries with table data and captions
    """
    if not PUBMED_PARSER_AVAILABLE:
        return []
    
    try:
        tables = pp.parse_pubmed_table(pmc_xml_path)
        return tables
    except Exception as e:
        logger.error(f"Error extracting tables with pubmed_parser: {e}")
        return []


def extract_captions_from_pmc_xml(pmc_xml_path: str) -> List[Dict]:
    """
    Extract figure/table captions from PMC XML using pubmed_parser
    
    Args:
        pmc_xml_path: Path to PMC XML file
    
    Returns:
        List of dictionaries with caption data
    """
    if not PUBMED_PARSER_AVAILABLE:
        return []
    
    try:
        captions = pp.parse_pubmed_caption(pmc_xml_path)
        return captions
    except Exception as e:
        logger.error(f"Error extracting captions with pubmed_parser: {e}")
        return []


def _extract_sections_fallback(xml_content: str) -> Dict[str, List[str]]:
    """Fallback section extraction using custom parsing"""
    sections = {
        "abstract": [],
        "introduction": [],
        "methods": [],
        "results": [],
        "discussion": [],
        "conclusions": []
    }
    
    # Use existing extract_text_from_pmc_xml logic
    text = extract_text_from_pmc_xml(xml_content)
    if text:
        sections["abstract"].append(text)  # Simplified fallback
    
    return sections


# ============================================================================
# AWS S3 Bulk Download for PMC Open Access Subset
# ============================================================================

def load_pmc_manifest(manifest_path: Optional[str] = None, 
                     bucket_name: str = "pmc-oa-opendata",
                     manifest_key: str = "oa_comm.filelist.csv") -> Dict[str, str]:
    """
    Load PMC manifest file mapping PMCIDs to S3 keys
    
    Args:
        manifest_path: Local path to manifest CSV (if None, downloads from S3)
        bucket_name: S3 bucket name (default: pmc-oa-opendata)
        manifest_key: S3 key for manifest file
    
    Returns:
        Dictionary mapping PMCID -> S3_Key
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available. Cannot load PMC manifest from S3")
        return {}
    
    try:
        import pandas as pd
        
        # Download manifest if not provided locally
        if manifest_path is None or not os.path.exists(manifest_path):
            logger.info("Downloading PMC manifest from S3...")
            s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
            
            # Download manifest to temp location
            temp_path = "/tmp/pmc_manifest.csv"
            s3_client.download_file(bucket_name, manifest_key, temp_path)
            manifest_path = temp_path
        
        # Load manifest into DataFrame
        df = pd.read_csv(manifest_path)
        
        # Create mapping: PMCID -> S3_Key
        # Assuming columns are: PMCID, S3_Key (adjust based on actual manifest format)
        if 'PMCID' in df.columns and 'S3_Key' in df.columns:
            pmcid_to_key = dict(zip(df['PMCID'], df['S3_Key']))
        elif len(df.columns) >= 2:
            # Try first two columns
            pmcid_to_key = dict(zip(df.iloc[:, 0], df.iloc[:, 1]))
        else:
            logger.error("Could not parse manifest file format")
            return {}
        
        logger.info(f"Loaded {len(pmcid_to_key)} PMCID mappings from manifest")
        return pmcid_to_key
    
    except Exception as e:
        logger.error(f"Error loading PMC manifest: {e}")
        return {}


@retry_with_backoff(max_retries=3, delay=1.0)
def download_pmc_from_s3(pmcid: str, pmcid_to_key: Dict[str, str],
                        output_dir: str = "/tmp/pmc_xml",
                        bucket_name: str = "pmc-oa-opendata") -> Optional[str]:
    """
    Download PMC XML file from AWS S3
    
    Args:
        pmcid: PMC ID (e.g., "PMC123456" or "123456")
        pmcid_to_key: Dictionary mapping PMCID -> S3_Key (from manifest)
        output_dir: Directory to save downloaded XML files
        bucket_name: S3 bucket name
    
    Returns:
        Path to downloaded XML file, or None if not found/error
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available. Cannot download from S3")
        return None
    
    # Clean PMCID
    pmcid_clean = pmcid.replace("PMC", "")
    
    # Look up S3 key
    s3_key = pmcid_to_key.get(pmcid_clean) or pmcid_to_key.get(f"PMC{pmcid_clean}")
    
    if not s3_key:
        logger.debug(f"PMCID {pmcid} not found in manifest")
        return None
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Download file
        s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        output_path = os.path.join(output_dir, f"{pmcid_clean}.xml")
        
        logger.info(f"Downloading {pmcid} from S3: {s3_key}")
        s3_client.download_file(bucket_name, s3_key, output_path)
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error downloading {pmcid} from S3: {e}")
        return None


def batch_download_pmc_from_s3(pmcids: List[str], pmcid_to_key: Optional[Dict[str, str]] = None,
                              output_dir: str = "/tmp/pmc_xml",
                              max_workers: int = 5) -> Dict[str, Optional[str]]:
    """
    Batch download multiple PMC XML files from S3
    
    Args:
        pmcids: List of PMC IDs
        pmcid_to_key: Manifest mapping (if None, loads from S3)
        output_dir: Output directory
        max_workers: Number of parallel downloads
    
    Returns:
        Dictionary mapping PMCID -> local file path (or None if failed)
    """
    if not BOTO3_AVAILABLE:
        logger.warning("boto3 not available. Cannot batch download from S3")
        return {pmcid: None for pmcid in pmcids}
    
    # Load manifest if not provided
    if pmcid_to_key is None:
        pmcid_to_key = load_pmc_manifest()
    
    if not pmcid_to_key:
        logger.error("Could not load PMC manifest")
        return {pmcid: None for pmcid in pmcids}
    
    results = {}
    
    # Use ThreadPoolExecutor for parallel downloads
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    def download_one(pmcid: str) -> Tuple[str, Optional[str]]:
        path = download_pmc_from_s3(pmcid, pmcid_to_key, output_dir)
        return pmcid, path
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(download_one, pmcid): pmcid for pmcid in pmcids}
        
        for future in as_completed(futures):
            pmcid, path = future.result()
            results[pmcid] = path
    
    successful = sum(1 for p in results.values() if p is not None)
    logger.info(f"Downloaded {successful}/{len(pmcids)} PMC files from S3")
    
    return results


# ============================================================================
# Enhanced Full-Text Retrieval with pubmed_parser
# ============================================================================

def fetch_fulltext_with_sections(pmid: str, prefer_pmc: bool = True,
                                 use_s3: bool = False) -> Tuple[Optional[Dict[str, List[str]]], str]:
    """
    Fetch full-text with section-aware extraction using pubmed_parser
    
    Args:
        pmid: PubMed ID
        prefer_pmc: Prefer PMC over other sources
        use_s3: Use AWS S3 for bulk download (requires manifest)
    
    Returns:
        Tuple of (sections_dict, source) where sections_dict has keys: abstract, methods, results, etc.
    """
    sections = {}
    source = "none"
    
    # Try PMC first
    if prefer_pmc:
        try:
            pmc_id = get_pmc_id_from_pmid(pmid)
            if pmc_id:
                pmc_id_clean = pmc_id.replace("PMC", "")
                
                xml_path = None
                
                # Try S3 download if enabled
                if use_s3 and BOTO3_AVAILABLE:
                    pmcid_to_key = load_pmc_manifest()
                    xml_path = download_pmc_from_s3(pmc_id, pmcid_to_key)
                
                # Fallback to PMC API
                if xml_path is None:
                    pmc_xml = fetch_pmc_fulltext(pmc_id)
                    if pmc_xml:
                        # Save to temp file for pubmed_parser
                        import tempfile
                        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                            f.write(pmc_xml)
                            xml_path = f.name
                
                if xml_path and os.path.exists(xml_path):
                    sections = extract_sections_from_pmc_xml(xml_path)
                    if sections:
                        source = "pmc"
                        # Clean up temp file if created
                        if xml_path.startswith('/tmp'):
                            try:
                                os.unlink(xml_path)
                            except OSError:
                                pass
                        return sections, source
        except Exception as e:
            logger.error(f"PMC retrieval with sections failed for {pmid}: {e}")
    
    # Fallback to regular retrieval
    full_text, source = fetch_fulltext(pmid, prefer_pmc)
    if full_text:
        sections = {"abstract": [full_text]}
    
    return sections, source