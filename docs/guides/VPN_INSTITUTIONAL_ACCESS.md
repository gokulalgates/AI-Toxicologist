# VPN/Institutional Access Guide

## Overview

The system now supports automatic PDF downloads when connected to your university VPN. **No API keys or special configuration required** - just connect to VPN and the system will automatically access publisher PDFs through your institutional subscription.

## How It Works

When you're connected to your university VPN, the system:

1. **Detects institutional access** - Publisher sites recognize your VPN connection
2. **Tries direct PDF links** - Attempts to download PDFs from major publishers
3. **Falls back gracefully** - If VPN access fails, tries other methods (PMC, DOI-based)

## Supported Publishers

The system automatically tries PDF downloads from:

- **ScienceDirect (Elsevier)** - Direct PDF download links
- **Wiley Online Library** - Multiple PDF access patterns
- **Springer** - Direct PDF links and article pages
- **Nature Publishing Group** - PDF download links
- **PLOS Journals** - Printable PDF versions
- **BioMed Central** - Direct PDF access
- **Taylor & Francis** - PDF download links
- **Oxford University Press** - Article PDFs
- **Cambridge University Press** - Core content access
- **And more** - DOI resolver redirects to publisher PDFs

## Usage

### Step 1: Connect to VPN

Connect to your university VPN before running the analysis:

```bash
# Example VPN connection (varies by university)
# Check your university IT department for VPN setup instructions
```

### Step 2: Enable Full-Text Retrieval

In your config or when running the analysis, ensure full-text retrieval is enabled:

```python
config.search.enable_fulltext_retrieval = True
```

### Step 3: Run Analysis

The system will automatically:
- Try PMC first (open access)
- Then try institutional/VPN access (if connected)
- Fall back to DOI-based methods if needed

## Priority Order

The system tries full-text retrieval in this order:

1. **PMC (PubMed Central)** - Fastest, open access only
2. **Institutional/VPN Access** - Works with VPN, no API keys needed ⭐
3. **Pybliometrics/Scopus** - Requires API key (optional)
4. **DOI-based** - Unpaywall and direct DOI resolution

## Troubleshooting

### PDFs Not Downloading

1. **Check VPN connection**
   - Ensure you're connected to university VPN
   - Try accessing a publisher site manually in browser to verify access

2. **Check publisher access**
   - Some publishers may require additional authentication
   - Your library may need to configure proxy settings

3. **Check logs**
   - The system prints which methods it's trying
   - Look for "Found PDF via institutional access" messages

### VPN Not Working

- Contact your university IT department for VPN setup help
- Some universities use different VPN clients (Cisco AnyConnect, OpenVPN, etc.)
- Ensure your VPN is configured correctly

### Partial Access

- Some articles may not be available through your institution
- The system will automatically fall back to other methods
- Check if the article is in your library's subscription

## Benefits

✅ **No API keys needed** - Works with just VPN connection  
✅ **Automatic detection** - System tries institutional access automatically  
✅ **Multiple publishers** - Supports all major academic publishers  
✅ **Graceful fallback** - Falls back to other methods if VPN fails  
✅ **No configuration** - Just connect VPN and run  

## Example Output

When working correctly, you'll see messages like:

```
Attempting institutional access via: https://www.sciencedirect.com/science/article/pii/S...
Found PDF via institutional access: https://www.sciencedirect.com/science/article/pii/S...
Successfully extracted text from PDF for DOI 10.1016/j...
Retrieved full-text via institutional/VPN access for PMID 12345678
```

## Notes

- VPN access works best when connected before starting the analysis
- Some publishers may have rate limits even with institutional access
- PDF quality depends on publisher - some may have OCR issues
- The system extracts text from PDFs automatically using pdfplumber
