# Full-Text Retrieval Guide

## Overview

The system supports multiple methods for full-text PDF retrieval:
1. **PMC (PubMed Central)** - Open access articles (no credentials needed)
2. **Institutional/VPN Access** - Works when connected to university VPN (no API keys needed)
3. **Pybliometrics/Scopus API** - Requires API key (optional)
4. **DOI-based** - Unpaywall and direct DOI resolution

## VPN/Institutional Access (Recommended - No API Keys Needed)

If you have VPN access to your university, the system will automatically try to download PDFs from publisher sites using your institutional access. **No API keys or configuration needed** - just connect to your university VPN before running the analysis.

### How It Works

When connected via VPN, the system tries direct PDF links from major publishers:
- ScienceDirect (Elsevier)
- Wiley Online Library
- Springer
- Nature Publishing Group
- PLOS journals
- BioMed Central
- Taylor & Francis
- Oxford University Press
- And more...

The system automatically detects when PDFs are available through your institutional access.

### Usage

Simply:
1. Connect to your university VPN
2. Enable full-text retrieval in config: `config.search.enable_fulltext_retrieval = True`
3. Run your analysis - the system will automatically use institutional access

## Pybliometrics Setup (Optional - Requires API Key)

Pybliometrics provides additional PDF download capabilities via the Scopus API.

## Installation

```bash
pip install pybliometrics>=3.0.0
```

## Configuration

Pybliometrics requires Scopus API credentials. Create a configuration file at `~/.scopus/config.ini`:

```ini
[Authentication]
APIKey = YOUR_SCOPUS_API_KEY
InstToken = YOUR_INSTITUTION_TOKEN  # Optional but recommended for higher rate limits
```

### Getting Scopus API Credentials

1. Go to [Elsevier Developer Portal](https://dev.elsevier.com/)
2. Sign up or log in
3. Create a new application to get your API Key
4. For institutional access, contact your library or IT department for an Institution Token

## Usage

The system will automatically use pybliometrics when:
- Full-text retrieval is enabled (`config.search.enable_fulltext_retrieval = True`)
- Pybliometrics is installed and configured
- A DOI is available for the paper

### Retrieval Priority

The system tries full-text retrieval in this order:
1. **PMC (PubMed Central)** - Open access articles
2. **Pybliometrics/Scopus** - If API key is configured
3. **DOI-based** - Unpaywall and direct DOI resolution

### Benefits

- Access to more PDFs through Scopus database
- Better coverage for subscription-based journals
- Institutional access support via InstToken
- Automatic DOI to Scopus ID resolution

## Troubleshooting

### Module Not Found
If you see "pybliometrics not available", install it:
```bash
pip install pybliometrics
```

### API Authentication Errors
- Verify your API key is correct in `~/.scopus/config.ini`
- Check that your API key has not expired
- Ensure the config file is in the correct location (`~/.scopus/config.ini`)

### Rate Limiting
- Use an Institution Token for higher rate limits
- The system includes retry logic with backoff
- Consider reducing concurrent requests if hitting limits

## Notes

- Pybliometrics is optional - the system works without it using PMC and DOI-based methods
- Scopus API has rate limits (typically 20,000 requests/week for free tier)
- Some PDFs may require institutional access even with API key
