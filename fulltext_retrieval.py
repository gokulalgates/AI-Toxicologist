"""
Full-text article retrieval for systematic reviews
Supports PMC (PubMed Central) API, DOI resolution, and pybliometrics
"""

import io
from typing import Optional, Tuple

import pdfplumber
import requests
from Bio import Entrez

from config import get_config
from utils import retry_with_backoff

# Try to import pybliometrics for enhanced PDF downloads
try:
    from pybliometrics.scopus import AbstractRetrieval
    from pybliometrics.scopus.exception import Scopus400Error, Scopus404Error
    PYBLIOMETRICS_AVAILABLE = True
except ImportError:
    PYBLIOMETRICS_AVAILABLE = False
    print("Note: pybliometrics not available. Install with: pip install pybliometrics")

# Try to import BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BEAUTIFULSOUP_AVAILABLE = True
except ImportError:
    BEAUTIFULSOUP_AVAILABLE = False
    print("Note: BeautifulSoup4 not available. Install with: pip install beautifulsoup4")

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
        handle = Entrez.elink(dbfrom="pubmed", db="pmc", id=pmid)
        record = Entrez.read(handle)
        handle.close()

        if record and len(record) > 0 and len(record[0]["LinkSetDb"]) > 0:
            pmc_ids = record[0]["LinkSetDb"][0]["Link"]
            if pmc_ids:
                # Extract PMC ID (format: PMC123456)
                pmc_id = pmc_ids[0]["Id"]
                return pmc_id
    except Exception as e:
        print(f"Error getting PMC ID for PMID {pmid}: {e}")

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
        print(f"Error getting DOI for PMID {pmid}: {e}")

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
        print(f"Error fetching PMC full-text for {pmc_id}: {e}")

    return None


def extract_text_from_pmc_xml(pmc_xml: str) -> Optional[str]:
    """
    Extract plain text from PMC XML
    
    Args:
        pmc_xml: PMC XML content
        
    Returns:
        Extracted text (abstract + body) or None
    """
    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(pmc_xml)

        # Extract abstract
        abstract_parts = []
        for abstract in root.findall(".//abstract"):
            for sec in abstract.findall(".//sec"):
                title = sec.find(".//title")
                title_text = title.text if title is not None else ""
                para_texts = [p.text for p in sec.findall(".//p") if p.text]
                if para_texts:
                    abstract_parts.append(f"{title_text}: {' '.join(para_texts)}")

        # Extract body text
        body_parts = []
        for body in root.findall(".//body"):
            for sec in body.findall(".//sec"):
                title = sec.find(".//title")
                title_text = title.text if title is not None else ""
                para_texts = []
                for p in sec.findall(".//p"):
                    # Get all text content including nested elements
                    text_content = "".join(p.itertext())
                    if text_content.strip():
                        para_texts.append(text_content.strip())

                if para_texts:
                    body_parts.append(f"{title_text}: {' '.join(para_texts)}")

        # Combine abstract and body
        full_text = "\n\n".join(abstract_parts + body_parts)

        if full_text.strip():
            return full_text.strip()

    except Exception as e:
        print(f"Error extracting text from PMC XML: {e}")

    return None


def _extract_text_from_pdf(pdf_content: bytes, doi: str) -> Optional[str]:
    """Helper to extract text from PDF content."""
    try:
        with io.BytesIO(pdf_content) as pdf_file, pdfplumber.open(pdf_file) as pdf:
            full_text = " ".join(page.extract_text() for page in pdf.pages if page.extract_text())

        if full_text and full_text.strip():
            print(f"Successfully extracted text from PDF for DOI {doi}")
            return full_text.strip()
        else:
            print(f"Warning: PDF for DOI {doi} was empty or text could not be extracted.")
            return None
    except Exception as e:
        print(f"Error processing PDF for DOI {doi}: {e}")
        return None


def _find_pdf_link_in_html(html_content: str, base_url: str) -> Optional[str]:
    """
    Try to find a PDF download link in HTML content.
    
    Common patterns:
    - Links with href ending in .pdf
    - Links with text like "Download PDF", "Full Text PDF", etc.
    - Meta tags with PDF URLs
    """
    if not BEAUTIFULSOUP_AVAILABLE:
        # Try simple regex fallback
        import re
        pdf_patterns = [
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'url\(["\']?([^"\']*\.pdf[^"\']*)["\']?\)',
        ]
        for pattern in pdf_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                from urllib.parse import urljoin
                pdf_url = urljoin(base_url, matches[0])
                return pdf_url
        return None

    try:
        from urllib.parse import urljoin

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

    except Exception as e:
        print(f"Error parsing HTML for PDF links: {e}")

    return None

def get_scopus_id_from_doi(doi: str) -> Optional[str]:
    """
    Get Scopus ID from DOI using pybliometrics.
    
    Args:
        doi: DOI string
        
    Returns:
        Scopus ID if found, None otherwise
    """
    if not PYBLIOMETRICS_AVAILABLE:
        return None

    try:
        doi_clean = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")
        ab = AbstractRetrieval(doi_clean, id_type="doi", view="META")
        return ab.eid if hasattr(ab, 'eid') else None
    except Exception:
        return None


@retry_with_backoff(max_retries=2, delay=1.0)
def fetch_fulltext_via_pybliometrics(doi: str, scopus_id: Optional[str] = None) -> Optional[str]:
    """
    Attempt to fetch full-text PDF using pybliometrics (Scopus API).
    
    Requires Scopus API key configured in ~/.scopus/config.ini:
    [Authentication]
    APIKey = YOUR_API_KEY
    InstToken = YOUR_INST_TOKEN  # Optional but recommended
    
    Args:
        doi: DOI string
        scopus_id: Optional Scopus ID if available (will be looked up if not provided)
        
    Returns:
        Full-text content if available, None otherwise
    """
    if not PYBLIOMETRICS_AVAILABLE:
        return None

    try:
        doi_clean = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

        # Get Scopus ID if not provided
        if not scopus_id:
            scopus_id = get_scopus_id_from_doi(doi_clean)

        # Try to retrieve abstract from Scopus using DOI or Scopus ID
        try:
            if scopus_id:
                ab = AbstractRetrieval(scopus_id, view="FULL")
            else:
                # Search by DOI
                ab = AbstractRetrieval(doi_clean, id_type="doi", view="FULL")

            # Check if PDF link is available
            if hasattr(ab, 'link') and ab.link:
                pdf_links = [link for link in ab.link if link.get('@type') == 'pdf']
                if pdf_links:
                    pdf_url = pdf_links[0].get('@href')
                    if pdf_url:
                        print(f"Found PDF link via pybliometrics: {pdf_url}")
                        pdf_response = session.get(pdf_url, timeout=60)
                        pdf_response.raise_for_status()
                        content_type = pdf_response.headers.get('Content-Type', '').lower()
                        if 'application/pdf' in content_type:
                            return _extract_text_from_pdf(pdf_response.content, doi)
                        elif 'text/html' in content_type:
                            # Sometimes Scopus returns HTML with embedded PDF, try to extract
                            pdf_url_alt = _find_pdf_link_in_html(pdf_response.text, pdf_url)
                            if pdf_url_alt:
                                pdf_response_alt = session.get(pdf_url_alt, timeout=60)
                                pdf_response_alt.raise_for_status()
                                if 'application/pdf' in pdf_response_alt.headers.get('Content-Type', '').lower():
                                    return _extract_text_from_pdf(pdf_response_alt.content, doi)

            # Alternative: Check if full-text is available in Scopus description field
            if hasattr(ab, 'description') and ab.description:
                # Sometimes Scopus provides full-text in description field
                full_text = ab.description
                if full_text and len(full_text) > 500:  # Reasonable length check
                    print(f"Retrieved full-text from Scopus description field for DOI {doi}")
                    return full_text

        except (Scopus404Error, Scopus400Error) as e:
            print(f"Scopus API error for DOI {doi}: {e}")
        except Exception as e:
            print(f"Error retrieving from Scopus for DOI {doi}: {e}")

    except Exception as e:
        print(f"Error using pybliometrics for DOI {doi}: {e}")

    return None


def _detect_publisher_from_doi(doi: str) -> str:
    """
    Detect publisher from DOI prefix.
    
    Returns:
        Publisher name or 'unknown'
    """
    doi_clean = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

    # Common DOI prefixes by publisher
    if doi_clean.startswith('10.1016'):  # ScienceDirect/Elsevier
        return 'sciencedirect'
    elif doi_clean.startswith('10.1002') or doi_clean.startswith('10.1111') or doi_clean.startswith('10.14814'):  # Wiley
        return 'wiley'
    elif doi_clean.startswith('10.1007') or doi_clean.startswith('10.1186') or doi_clean.startswith('10.1185'):  # Springer
        return 'springer'
    elif doi_clean.startswith('10.1038') or doi_clean.startswith('10.1039'):  # Nature or RSC
        if '10.1039' in doi_clean:
            return 'rsc'
        return 'nature'
    elif doi_clean.startswith('10.1371'):  # PLOS
        return 'plos'
    elif doi_clean.startswith('10.1093'):  # Oxford University Press
        return 'oup'
    elif doi_clean.startswith('10.1080') or doi_clean.startswith('10.1081'):  # Taylor & Francis
        return 'tandf'
    elif doi_clean.startswith('10.1017'):  # Cambridge University Press
        return 'cambridge'
    else:
        return 'unknown'


@retry_with_backoff(max_retries=2, delay=1.0)
def fetch_fulltext_via_institutional_access(doi: str, pmid: Optional[str] = None) -> Optional[str]:
    """
    Attempt to fetch full-text PDF via institutional/VPN access.
    This works when connected to university VPN without requiring API keys.
    
    Tries publisher-specific URLs based on DOI detection.
    Works best when connected to university VPN that provides institutional access.
    
    Args:
        doi: DOI string
        pmid: Optional PubMed ID for additional lookup
        
    Returns:
        Full-text content if available, None otherwise
    """
    doi_clean = doi.replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

    # Extract DOI parts for constructing URLs
    doi_parts = doi_clean.split('/')
    doi_prefix = doi_parts[0] if len(doi_parts) > 0 else ''
    doi_suffix = doi_parts[-1] if len(doi_parts) > 1 else doi_clean

    # Detect publisher from DOI
    publisher = _detect_publisher_from_doi(doi_clean)

    # Build publisher-specific URL patterns
    publisher_patterns = []

    if publisher == 'sciencedirect':
        # ScienceDirect (Elsevier) - need to get PII from article page first
        # First try to access article page via DOI to extract PII
        publisher_patterns.extend([
            f"https://www.sciencedirect.com/science/article/pii/{doi_clean}",  # Try DOI directly
            f"https://www.sciencedirect.com/science/article/abs/pii/{doi_clean}",
            f"https://doi.org/{doi_clean}",  # DOI resolver may redirect to ScienceDirect
        ])

    elif publisher == 'wiley':
        # Wiley Online Library - try journal-specific subdomains first
        # Extract journal name from DOI if possible (e.g., 10.14814/phy2 -> physoc)
        doi_suffix_parts = doi_suffix.split('.')
        journal_hints = []

        if len(doi_suffix_parts) > 0:
            # Common Wiley journal subdomains based on DOI patterns
            journal_map = {
                'phy2': 'physoc',  # Physiological Reports
                'bcpt': 'onlinelibrary',  # Basic Clinical Pharmacology & Toxicology
                'jbt': 'onlinelibrary',  # Journal of Biochemical and Molecular Toxicology
            }
            journal_hint = journal_map.get(doi_suffix_parts[0], None)
            if journal_hint:
                journal_hints.append(journal_hint)

        # Try journal-specific subdomain first, then generic
        for journal_hint in journal_hints:
            if journal_hint != 'onlinelibrary':
                publisher_patterns.extend([
                    f"https://{journal_hint}.onlinelibrary.wiley.com/doi/pdfdirect/{doi_clean}",
                    f"https://{journal_hint}.onlinelibrary.wiley.com/doi/pdf/{doi_clean}",
                    f"https://{journal_hint}.onlinelibrary.wiley.com/doi/epdf/{doi_clean}",
                ])

        # Generic Wiley URLs (will redirect to journal-specific if needed)
        publisher_patterns.extend([
            f"https://onlinelibrary.wiley.com/doi/pdfdirect/{doi_clean}",
            f"https://onlinelibrary.wiley.com/doi/pdf/{doi_clean}",
            f"https://onlinelibrary.wiley.com/doi/epdf/{doi_clean}",
            f"https://onlinelibrary.wiley.com/doi/full/{doi_clean}",  # Full text page, then find PDF
        ])

    elif publisher == 'springer':
        # Springer
        publisher_patterns.extend([
            f"https://link.springer.com/content/pdf/{doi_clean}.pdf",
            f"https://link.springer.com/article/{doi_clean}/pdf",
            f"https://link.springer.com/article/{doi_clean}",
        ])

    elif publisher == 'nature':
        # Nature Publishing Group
        publisher_patterns.extend([
            f"https://www.nature.com/articles/{doi_suffix}.pdf",
            f"https://www.nature.com/articles/{doi_suffix}",
        ])

    elif publisher == 'rsc':
        # Royal Society of Chemistry
        publisher_patterns.extend([
            f"https://pubs.rsc.org/en/content/articlepdf/{doi_clean.replace('/', '/')}",
            f"https://pubs.rsc.org/en/content/articlelanding/{doi_clean}",
        ])

    elif publisher == 'plos':
        # PLOS journals
        journal_name = 'plosone'  # Default, could be detected from DOI
        if 'plosmed' in doi_clean.lower() or 'medicine' in doi_clean.lower():
            journal_name = 'plosmedicine'
        publisher_patterns.extend([
            f"https://journals.plos.org/{journal_name}/article/file?id={doi_clean}&type=printable",
            f"https://journals.plos.org/{journal_name}/article?id={doi_clean}",
        ])

    elif publisher == 'oup':
        # Oxford University Press
        publisher_patterns.extend([
            f"https://academic.oup.com/{doi_suffix}/pdf",
            f"https://academic.oup.com/{doi_suffix}/article-pdf",
            f"https://academic.oup.com/{doi_suffix}",
        ])

    elif publisher == 'tandf':
        # Taylor & Francis
        publisher_patterns.extend([
            f"https://www.tandfonline.com/doi/pdf/{doi_clean}",
            f"https://www.tandfonline.com/doi/epdf/{doi_clean}",
            f"https://www.tandfonline.com/doi/full/{doi_clean}",
        ])

    elif publisher == 'cambridge':
        # Cambridge University Press
        publisher_patterns.append(f"https://www.cambridge.org/core/services/aop-cambridge-core/content/view/{doi_suffix}")

    # Always try DOI resolver as fallback (may redirect to publisher PDF with VPN)
    publisher_patterns.append(f"https://doi.org/{doi_clean}")

    # Try each publisher pattern
    for pdf_url in publisher_patterns:
        try:
            print(f"Attempting institutional access via {publisher}: {pdf_url[:80]}...")
            response = session.get(pdf_url, timeout=30, allow_redirects=True, stream=True)

            # Check if we got a PDF directly
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' in content_type:
                print(f"✓ Found PDF via institutional access: {pdf_url[:80]}...")
                pdf_content = response.content
                if len(pdf_content) > 1000:  # Reasonable size check
                    return _extract_text_from_pdf(pdf_content, doi)

            # Check if HTML response contains PDF link
            elif 'text/html' in content_type:
                # For ScienceDirect, extract PII and construct PDF URL
                if publisher == 'sciencedirect':
                    import re
                    # Try multiple patterns to find PII
                    pii_patterns = [
                        r'pii[=:]([A-Z0-9]+)',  # pii=S1687157X25001611
                        r'"pii":"([A-Z0-9]+)"',  # JSON format
                        r'data-pii="([A-Z0-9]+)"',  # data attribute
                        r'/pii/([A-Z0-9]+)',  # URL pattern
                        r'article/pii/([A-Z0-9]+)',  # Full URL pattern
                    ]

                    pii = None
                    for pattern in pii_patterns:
                        matches = re.findall(pattern, response.text, re.IGNORECASE)
                        if matches:
                            pii = matches[0].upper()
                            break

                    # Also check URL for PII
                    if not pii:
                        url_pii_match = re.search(r'/pii/([A-Z0-9]+)', response.url, re.IGNORECASE)
                        if url_pii_match:
                            pii = url_pii_match.group(1).upper()

                    if pii:
                        # Try multiple ScienceDirect PDF URL formats
                        sciencedirect_pdf_urls = [
                            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft?isDTMRedir=true&download=true",
                            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdfft",
                            f"https://www.sciencedirect.com/science/article/pii/{pii}/pdf",
                        ]

                        for pdf_url in sciencedirect_pdf_urls:
                            try:
                                pdf_response = session.get(pdf_url, timeout=60, stream=True, allow_redirects=True)
                                pdf_content_type = pdf_response.headers.get('Content-Type', '').lower()
                                if 'application/pdf' in pdf_content_type:
                                    pdf_content = pdf_response.content
                                    if len(pdf_content) > 1000:
                                        print(f"✓ Found PDF via ScienceDirect PII: {pii}")
                                        return _extract_text_from_pdf(pdf_content, doi)
                            except:
                                continue

                    # Fallback: look for PDF link in HTML
                    pdf_link = _find_pdf_link_in_html(response.text, response.url)
                    if pdf_link and 'sciencedirect' in pdf_link.lower():
                        print(f"✓ Found PDF link in ScienceDirect HTML: {pdf_link[:80]}...")
                        pdf_response = session.get(pdf_link, timeout=60, stream=True)
                        if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                            pdf_content = pdf_response.content
                            if len(pdf_content) > 1000:
                                return _extract_text_from_pdf(pdf_content, doi)

                # For Wiley, check if we got redirected to journal-specific subdomain
                elif publisher == 'wiley':
                    # Check if current URL is journal-specific and try PDF links
                    if 'onlinelibrary.wiley.com' in response.url:
                        # Extract journal subdomain
                        import re
                        journal_match = re.search(r'https://([^.]+)\.onlinelibrary\.wiley\.com', response.url)
                        if journal_match:
                            journal_subdomain = journal_match.group(1)
                            # Try PDF links with journal subdomain
                            wiley_pdf_urls = [
                                f"https://{journal_subdomain}.onlinelibrary.wiley.com/doi/pdfdirect/{doi_clean}",
                                f"https://{journal_subdomain}.onlinelibrary.wiley.com/doi/pdf/{doi_clean}",
                            ]
                            for pdf_url in wiley_pdf_urls:
                                try:
                                    pdf_response = session.get(pdf_url, timeout=60, stream=True)
                                    if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                                        pdf_content = pdf_response.content
                                        if len(pdf_content) > 1000:
                                            print(f"✓ Found PDF via Wiley journal subdomain: {journal_subdomain}")
                                            return _extract_text_from_pdf(pdf_content, doi)
                                except:
                                    continue

                    # General HTML parsing for PDF links
                    pdf_link = _find_pdf_link_in_html(response.text, response.url)
                    if pdf_link:
                        print(f"✓ Found PDF link in Wiley HTML: {pdf_link[:80]}...")
                        pdf_response = session.get(pdf_link, timeout=60, stream=True)
                        if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                            pdf_content = pdf_response.content
                            if len(pdf_content) > 1000:
                                return _extract_text_from_pdf(pdf_content, doi)

                # General HTML parsing for PDF links
                pdf_link = _find_pdf_link_in_html(response.text, response.url)
                if pdf_link:
                    print(f"✓ Found PDF link in HTML, downloading: {pdf_link[:80]}...")
                    pdf_response = session.get(pdf_link, timeout=60, stream=True)
                    pdf_response.raise_for_status()
                    if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                        pdf_content = pdf_response.content
                        if len(pdf_content) > 1000:
                            return _extract_text_from_pdf(pdf_content, doi)

        except requests.exceptions.RequestException:
            # Continue to next pattern (don't print every failed attempt)
            continue
        except Exception as e:
            # Only print unexpected errors
            if '403' not in str(e) and '404' not in str(e):
                print(f"Error trying institutional access pattern: {e}")
            continue

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
        print(f"Attempting Unpaywall for DOI: {doi_clean}")
        unpaywall_url = f"https://api.unpaywall.org/v2/{doi_clean}?email={get_config().search.entrez_email}"
        response = session.get(unpaywall_url, timeout=30)

        # Handle 422 errors gracefully (Unpaywall may reject some DOIs)
        if response.status_code == 422:
            print(f"Unpaywall returned 422 for DOI {doi_clean} (DOI may not be in Unpaywall database)")
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
                print(f"Found OA PDF link via Unpaywall: {pdf_url}")
                pdf_response = session.get(pdf_url, timeout=60)
                pdf_response.raise_for_status()
                return _extract_text_from_pdf(pdf_response.content, doi)

    except requests.exceptions.HTTPError as e:
        # Don't fail on HTTP errors from Unpaywall (422, 404, etc.)
        if e.response.status_code in [422, 404, 429]:
            print(f"Unpaywall request failed for DOI {doi}: {e.response.status_code} {e.response.reason}")
        else:
            print(f"Unpaywall request failed for DOI {doi}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Unpaywall request failed for DOI {doi}: {e}")
    except Exception as e:
        print(f"Error processing Unpaywall response for DOI {doi}: {e}")

    # 2. Fallback: Try downloading directly from the DOI resolver
    try:
        print(f"Unpaywall failed or found no OA link. Attempting direct download for DOI: {doi_clean}")
        direct_url = f"https://doi.org/{doi_clean}"
        # The session will follow redirects to the PDF
        direct_response = session.get(direct_url, timeout=60, allow_redirects=True)
        direct_response.raise_for_status()

        # Check if the content is a PDF
        content_type = direct_response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type:
            print("Direct download returned a PDF. Extracting text.")
            return _extract_text_from_pdf(direct_response.content, doi)
        elif 'text/html' in content_type:
            # Try to parse HTML to find PDF links
            print("Direct download returned HTML. Attempting to find PDF link...")
            pdf_url = _find_pdf_link_in_html(direct_response.text, direct_response.url)
            if pdf_url:
                print(f"Found PDF link in HTML: {pdf_url}")
                pdf_response = session.get(pdf_url, timeout=60)
                pdf_response.raise_for_status()
                if 'application/pdf' in pdf_response.headers.get('Content-Type', '').lower():
                    return _extract_text_from_pdf(pdf_response.content, doi)
            else:
                print("Could not find PDF link in HTML. Content-Type:", content_type)
                print("Note: This may require institutional access. Full-text retrieval will use abstract only.")
        else:
            print("Direct download did not return a PDF. Content-Type:", content_type)

    except requests.exceptions.RequestException as e:
        print(f"Direct download failed for DOI {doi}: {e}")
    except Exception as e:
        print(f"Error processing direct download for DOI {doi}: {e}")

    return None


def fetch_fulltext(pmid: str, prefer_pmc: bool = True, use_pybliometrics: bool = True,
                   use_institutional_access: bool = True) -> Tuple[Optional[str], str]:
    """
    Fetch full-text article for a given PMID
    
    Args:
        pmid: PubMed ID
        prefer_pmc: If True, prefer PMC over other sources
        use_pybliometrics: If True, try pybliometrics (Scopus) as an additional source
        use_institutional_access: If True, try institutional/VPN-based access (works without API keys)
        
    Returns:
        Tuple of (full_text, source) where source is "pmc", "doi", "scopus", "institutional", or "none"
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
                        print(f"Retrieved full-text from PMC for PMID {pmid}")
                        return full_text, source
        except Exception as e:
            print(f"PMC retrieval failed for {pmid}: {e}")

    # Get DOI for subsequent methods
    doi = None
    try:
        doi = get_doi_from_pmid(pmid)
    except Exception as e:
        print(f"Could not get DOI for PMID {pmid}: {e}")

    # Try institutional/VPN access (works without API keys when connected to university VPN)
    if not full_text and use_institutional_access and doi:
        try:
            full_text = fetch_fulltext_via_institutional_access(doi, pmid)
            if full_text:
                source = "institutional"
                print(f"Retrieved full-text via institutional/VPN access for PMID {pmid}")
                return full_text, source
        except Exception as e:
            print(f"Institutional access retrieval failed for {pmid}: {e}")

    # Try pybliometrics (Scopus) if available and enabled (requires API key)
    if not full_text and use_pybliometrics and PYBLIOMETRICS_AVAILABLE and doi:
        try:
            full_text = fetch_fulltext_via_pybliometrics(doi)
            if full_text:
                source = "scopus"
                print(f"Retrieved full-text via pybliometrics/Scopus for PMID {pmid}")
                return full_text, source
        except Exception as e:
            print(f"Pybliometrics retrieval failed for {pmid}: {e}")

    # Try DOI-based retrieval as fallback (Unpaywall, direct DOI resolution)
    if not full_text and doi:
        try:
            full_text = fetch_fulltext_via_doi(doi)
            if full_text:
                source = "doi"
                print(f"Retrieved full-text via DOI for PMID {pmid}")
                return full_text, source
        except Exception as e:
            print(f"DOI retrieval failed for {pmid}: {e}")

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
