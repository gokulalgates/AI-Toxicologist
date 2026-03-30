# How to Run Validation in Background

## Option 1: Run AI Analysis First (Recommended)

Since the AI analysis takes 30-60 minutes, run it separately first:

```bash
# Run AI analysis in background
./run_ai_analysis_background.sh

# Monitor progress
tail -f acetaminophen_analysis.log

# Once complete, run validation
python run_validation_nihms.py
```

## Option 2: Run Everything in Background

```bash
# Run validation script (which will trigger analysis) in background
./run_validation_background.sh

# Monitor progress
tail -f validation_nihms.log
```

## Option 3: Use Screen or TMUX (Best for Long Runs)

```bash
# Start a screen session
screen -S validation

# Run the analysis
python -c "from app import analyze_chemical; analyze_chemical('Acetaminophen', model_names=['llama3.2', 'mixtral'], enable_rob=True, enable_certainty=True)"

# Detach: Press Ctrl+A then D
# Reattach: screen -r validation
```

## Check Status

```bash
# Check if analysis is running
ps aux | grep -E "analyze_chemical|run_validation" | grep -v grep

# Check if results exist
ls -la results/Acetaminophen/study_records.jsonl

# View latest logs
tail -20 acetaminophen_analysis.log
```

## Expected Timeline

1. **PubMed Search**: ~10 seconds
2. **Relevance Filtering**: ~5-10 minutes (36 abstracts)
3. **KC Analysis**: ~20-40 minutes (36 abstracts × 2 models × ~30 seconds each)
4. **Risk-of-Bias**: ~10-15 minutes
5. **Certainty Grading**: ~5 minutes
6. **Total**: ~40-70 minutes

## After Analysis Completes

Once `results/Acetaminophen/study_records.jsonl` exists, run:

```bash
python run_validation_nihms.py
```

This will:
1. Load the gold standard
2. Load AI results
3. Compare and generate metrics
4. Create `validation_report_nihms.json`
