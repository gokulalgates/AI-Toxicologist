# Reload Previous Analysis Results Feature

## Overview
You can now reload previously run analyses and continue chatting about them, even after refreshing the page or restarting the app.

## Features

### 1. Automatic Saving
- When you run an analysis, abstracts are automatically saved to `results/{chemical_name}/abstracts_for_chat.json`
- This happens automatically after each analysis completes
- No manual steps required

### 2. Load Previous Analyses
- **Dropdown Menu**: Select from a list of all previous analyses
- **Refresh Button**: Click "🔄 Refresh List" to update the list
- **Load Button**: Click "Load" to load the selected analysis

### 3. Chat with Loaded Results
- Once loaded, you can ask questions about the abstracts just like after a fresh analysis
- The chatbot will initialize with the loaded abstracts
- All RAG functionality works the same way

## How to Use

### For New Analyses
1. Run an analysis as usual
2. Abstracts are automatically saved
3. Chat with the results immediately

### For Existing Results
1. Click "🔄 Refresh List" to see available analyses
2. Select an analysis from the dropdown (shows chemical name and number of abstracts)
3. Click "Load"
4. The chatbot will appear and you can start asking questions

### Converting Old Results
If you have old results that weren't automatically saved, run:
```bash
python3 prepare_existing_results_for_chat.py acetaminophen
```

Or convert all available results:
```bash
python3 prepare_existing_results_for_chat.py
```

## File Structure

```
results/
  {chemical_name}/
    study_records.jsonl          # Full analysis records
    abstracts_for_chat.json       # Abstracts for chat (auto-generated)
    ...
```

## Example Usage

1. **After running analysis:**
   - Analysis completes
   - Abstracts are saved automatically
   - Chatbot appears ready to use

2. **Reloading later:**
   - Open the web interface
   - Click "🔄 Refresh List"
   - Select "Acetaminophen (301 abstracts)"
   - Click "Load"
   - Ask: "What are the evidence of KC1"

3. **Chatting:**
   - The chatbot will search through all 301 abstracts
   - It will find relevant evidence for KC1
   - Responses cite specific PMIDs

## Technical Details

- **Storage Format**: JSON with metadata (chemical name, timestamp, abstract count)
- **Auto-loading**: If you ask a question without loading, the system tries to auto-load the most recent analysis
- **RAG System**: Uses the same AgentRAGSystem as fresh analyses
- **Performance**: Embeddings are generated on-demand when you first ask a question

## Troubleshooting

**Problem**: "No abstracts available" error
- **Solution**: Make sure you've either run an analysis or loaded a previous one

**Problem**: Dropdown is empty
- **Solution**: Click "🔄 Refresh List" or run the conversion script for old results

**Problem**: Can't find old results
- **Solution**: Run `python3 prepare_existing_results_for_chat.py` to convert existing `study_records.jsonl` files

## Benefits

1. **Persistent Chat**: Continue conversations about past analyses
2. **No Re-analysis Needed**: Don't re-run expensive analyses just to ask questions
3. **Comparison**: Load different analyses to compare results
4. **Sharing**: Share the `abstracts_for_chat.json` file with others
