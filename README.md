# AI Toxicologist: Hepatotoxicity Assessment Tool

A Gradio-based application that performs systematic literature reviews to assess chemical hepatotoxicity potential based on the **Key Characteristics of Human Hepatotoxicants** (Rusyn et al., 2021).

## Features

- **Chemical Name Standardization**: Uses PubChem to resolve chemical names
- **PubMed Integration**: Fetches relevant abstracts automatically
- **AI-Powered Analysis**: Uses open-source LLMs (via Ollama) to analyze abstracts against 12 Key Characteristics
- **Evidence Matrix**: Visual heatmap showing which papers support which mechanisms
- **Pathway Network**: Interactive graph showing relationships between Key Characteristics

## Installation

1. Install Ollama (if not already installed):
   - Visit https://ollama.ai and follow installation instructions
   - Or use: `curl -fsSL https://ollama.ai/install.sh | sh`

2. Pull a model (recommended: llama3.1):
```bash
ollama pull llama3.1
```

Other good options:
```bash
ollama pull llama3.2    # Newer version
ollama pull mistral     # Alternative model
ollama pull mixtral     # Mixture of experts model
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python app.py
```

2. Open your browser to the URL shown (typically `http://localhost:7860`)

3. Enter:
   - A chemical name (e.g., "acetaminophen", "carbon tetrachloride", "ethanol")
   - Select your Ollama model from the dropdown (default: llama3.1)

4. Click "Analyze Chemical" and wait for results

**Note**: Make sure Ollama is running before starting the analysis. The first run may take longer as the model loads.

## Outputs

The application provides three outputs:

1. **Analysis Summary**: Text summary with chemical information and KC evidence counts
2. **Evidence Matrix Heatmap**: Visual representation of which papers support which Key Characteristics
3. **Mechanistic Pathway Network**: Network graph showing co-occurrence patterns between KCs

## Key Characteristics

The 12 Key Characteristics assessed:

- **KC1**: Reactive/Bioactivation
- **KC2**: Cell Death (apoptosis/necrosis)
- **KC3**: Proliferation/Regeneration
- **KC4**: Transport Disruption
- **KC5**: Oxidative Stress
- **KC6**: Immune Response
- **KC7**: Mitochondrial Dysfunction
- **KC8**: Stress Signaling
- **KC9**: Cholestasis
- **KC10**: Cytoskeleton Disruption
- **KC11**: Liver Fibrosis
- **KC12**: Metabolism Disruption

## Technical Details

- **UI Framework**: Gradio (Blocks layout)
- **Data Processing**: pandas, pubchempy, biopython
- **AI**: langchain, langchain-ollama (open-source LLMs via Ollama)
- **Visualization**: matplotlib, seaborn, networkx

## Notes

- The application fetches up to 10 abstracts from PubMed
- Each abstract is analyzed individually against all 12 KCs
- The network graph shows edges between KCs that co-occur in the same papers
- Edge weights indicate frequency of co-occurrence

## Reference

Rusyn et al. (2021). Key Characteristics of Human Hepatotoxicants. *Toxicological Sciences*.
