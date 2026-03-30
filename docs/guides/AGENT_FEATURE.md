# Hepatotoxicity Chat Agent Feature

## Overview

A new interactive chat agent has been integrated into the AI Toxicologist application, based on the implementation from `NEW_KC_LIVER/`. This agent provides a conversational interface for querying chemicals and their Key Characteristics (KCs) with automatic PubMed abstract retrieval.

## Features

### 1. **Interactive Chat Interface**
- Natural language queries about chemicals and hepatotoxicity
- Multi-turn conversations with context preservation
- Clean, user-friendly Gradio chat interface

### 2. **RAG (Retrieval-Augmented Generation)**
- Automatic PubMed abstract downloading for mentioned chemicals
- Semantic search using Ollama embeddings (`nomic-embed-text`)
- Context-aware responses based on retrieved research abstracts

### 3. **Multi-Model Ensemble**
- Support for multiple Ollama models simultaneously
- Consensus-based responses for improved accuracy
- Configurable model selection

### 4. **Automatic Chemical Detection**
- Extracts chemical names from user queries
- Automatically downloads relevant PubMed abstracts
- Caches abstracts for faster subsequent queries

## Usage

### Via Gradio Web Interface

1. Start the application:
   ```bash
   python app.py
   ```

2. Navigate to the **"💬 Chat Agent"** tab in the web interface

3. Configure settings:
   - **Select Model(s)**: Choose one or more Ollama models
   - **Enable RAG**: Toggle automatic PubMed abstract retrieval
   - **RAG Top-K**: Number of abstracts to retrieve (1-10)

4. Start chatting:
   - Type your question (e.g., "What are the key characteristics of acetaminophen?")
   - The agent will automatically download PubMed abstracts if a chemical is detected
   - Responses are generated using the selected models and retrieved context

### Via Command Line

You can also use the agent directly from the command line:

```bash
python hepatotoxicity_agent.py
```

This will start an interactive CLI session where you can chat with the agent.

## Architecture

### New Modules

1. **`hepatotoxicity_agent.py`**
   - Main agent class (`HepatotoxicityAgent`)
   - Handles chat interactions, model ensemble, and RAG integration
   - Command-line interface for direct usage

2. **`agent_rag_system.py`**
   - RAG system using Ollama embeddings
   - Semantic search over PubMed abstracts
   - Falls back to keyword search if embeddings unavailable

3. **`agent_pubmed_downloader.py`**
   - PubMed abstract downloader using BioPython Entrez
   - Chemical-specific and general hepatotoxicity searches
   - Batch processing with rate limiting

### Integration with Existing Codebase

- Uses existing `config.py` for configuration
- Leverages existing BioPython Entrez setup
- Compatible with existing LangChain/Ollama infrastructure
- Separate from existing `rag_system.py` (which uses sentence-transformers)

## Dependencies

The agent requires the `ollama` Python package:

```bash
pip install ollama
```

This is already included in `requirements.txt`.

## Configuration

The agent uses settings from `config.py`:

- **Email**: `config.search.entrez_email` (for NCBI API)
- **Default Models**: `config.llm.default_models`
- **Temperature**: `config.llm.temperature`

## Example Queries

- "What are the key characteristics of acetaminophen?"
- "Predict the toxicity of PFOA"
- "Analyze the mechanisms of carbon tetrachloride"
- "What is the evidence for oxidative stress in ethanol hepatotoxicity?"

## Key Characteristics (KCs)

The agent is trained on the 12 Key Characteristics framework:

1. **KC1**: Reactive/Bioactivation
2. **KC2**: Cell Death (apoptosis/necrosis)
3. **KC3**: Proliferation/Regeneration
4. **KC4**: Transport Disruption
5. **KC5**: Oxidative Stress
6. **KC6**: Immune Response
7. **KC7**: Mitochondrial Dysfunction
8. **KC8**: Stress Signaling
9. **KC9**: Cholestasis (liver-specific)
10. **KC10**: Cytoskeleton Disruption
11. **KC11**: Liver Fibrosis
12. **KC12**: Metabolism Disruption

## Differences from NEW_KC_LIVER

The implementation has been adapted to work with the existing codebase:

1. **BioPython Entrez**: Uses BioPython instead of Entrez Direct command-line tools
2. **LangChain Integration**: Uses LangChain's ChatOllama instead of direct ollama API
3. **Config Integration**: Uses existing config system instead of hardcoded values
4. **Gradio Integration**: Integrated as a tab in the main application

## Troubleshooting

### Agent fails to initialize
- Ensure Ollama is running: `ollama serve`
- Check that models are available: `ollama list`
- Pull required models: `ollama pull llama3.1`

### RAG not working
- Ensure embedding model is available: `ollama pull nomic-embed-text`
- Check network connection for PubMed downloads
- Verify NCBI email is configured in `config.py`

### Slow responses
- Reduce RAG Top-K value
- Use fewer models in ensemble
- Check GPU availability for faster inference

## Future Enhancements

Potential improvements:
- Persistent chat history across sessions
- Export chat conversations
- Integration with systematic review results
- Advanced ensemble methods (voting, weighted consensus)
- Support for full-text article retrieval
