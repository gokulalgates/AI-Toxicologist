# Performance Optimization Guide

## Current Performance Settings

### GPU Acceleration
- **Status**: Enabled (if GPU available)
- **GPU Layers**: 35 (configurable)
- **Location**: `config.py` line 60

### Parallel Processing
- **Status**: Enabled by default
- **Workers**: Auto-calculated based on GPU count
- **Location**: `config.py` line 57-58

### Analysis Limits
- **Initial Abstracts**: 100 (configurable)
- **Analyzed Abstracts**: 20 (configurable)
- **Location**: `config.py` line 16-17

## Speed Improvement Strategies

### 1. **Reduce Number of Abstracts Analyzed** ⚡ FASTEST
**Impact**: High (linear speedup)
**Trade-off**: Less comprehensive analysis

```python
# In config.py or set environment variable:
MAX_ABSTRACTS_ANALYZE=10  # Reduce from 20 to 10
```

**Speedup**: ~2x faster (half the abstracts)

### 2. **Use Fewer Models (Single Reviewer)** ⚡ FAST
**Impact**: High (linear with number of models)
**Trade-off**: Less consensus/reliability

**In Web Interface**: Select only 1 model instead of multiple

**Speedup**: 2-3x faster (if using 2-3 models, use 1 instead)

### 3. **Increase GPU Layers** ⚡ MODERATE
**Impact**: Moderate (faster inference per request)
**Trade-off**: More VRAM usage

```python
# In config.py:
gpu_layers: int = 50  # Increase from 35 to 50 (if you have VRAM)
```

**Speedup**: ~20-30% faster per request

### 4. **Increase Parallel Workers** ⚡ MODERATE
**Impact**: Moderate (more concurrent requests)
**Trade-off**: More memory/VRAM usage

```python
# In config.py:
max_workers: int = 8  # Set explicit number (default is auto)
```

**Speedup**: ~2-4x faster (depending on GPU/CPU)

### 5. **Disable Optional Features** ⚡ MODERATE
**Impact**: Moderate (skip expensive steps)
**Trade-off**: Less detailed results

**In Web Interface**:
- Uncheck "Enable Risk-of-Bias Assessment" (saves ~30% time)
- Uncheck "Enable Certainty Grading" (saves ~10% time)

**Speedup**: ~40% faster

### 6. **Use Faster Models** ⚡ MODERATE
**Impact**: Moderate (smaller models = faster)
**Trade-off**: Potentially lower accuracy

**Faster Models** (in order):
1. `phi3` (3.8B) - Fastest
2. `llama3.1` (8B) - Fast
3. `mistral` (7B) - Fast
4. `llama3.2` (70B) - Slower but more accurate
5. `mixtral` (47B) - Slower but more accurate

**Speedup**: 2-5x faster (phi3 vs llama3.2)

### 7. **Disable RAG and Hierarchical Processing** ⚡ SMALL
**Impact**: Small (saves per-request overhead)
**Trade-off**: Less context-aware analysis

```python
# In config.py:
enable_rag: bool = False
enable_hierarchical: bool = False
```

**Speedup**: ~10-15% faster

### 8. **Reduce Initial PubMed Fetch** ⚡ SMALL
**Impact**: Small (less to filter)
**Trade-off**: Might miss relevant papers

```python
# In config.py:
max_abstracts_initial: int = 50  # Reduce from 100
```

**Speedup**: ~5-10% faster

## Recommended Quick Wins

### For Maximum Speed (Fastest Analysis)
```python
# config.py changes:
max_abstracts_analyze: int = 10  # Reduce analyzed abstracts
enable_rag: bool = False  # Disable RAG
enable_hierarchical: bool = False  # Disable hierarchical
gpu_layers: int = 50  # More GPU layers if VRAM available
max_workers: int = 8  # More parallel workers

# In web interface:
- Use 1 model (phi3 or llama3.1)
- Disable Risk-of-Bias
- Disable Certainty Grading
```

**Expected Speedup**: 5-10x faster

### For Balanced Speed/Quality
```python
# config.py changes:
max_abstracts_analyze: int = 15  # Slight reduction
gpu_layers: int = 40  # Moderate increase
max_workers: int = 6  # Moderate parallelization

# In web interface:
- Use 1-2 models (llama3.2 or mistral)
- Keep Risk-of-Bias enabled
- Keep Certainty Grading enabled
```

**Expected Speedup**: 2-3x faster

## Environment Variables (Quick Configuration)

You can set these without editing config.py:

```bash
export MAX_ABSTRACTS_ANALYZE=10
export MAX_ABSTRACTS_INITIAL=50
export OLLAMA_GPU_LAYERS=50
```

Then run: `python app.py`

## GPU Optimization

### Check GPU Usage
```bash
# Monitor GPU while running
watch -n 1 nvidia-smi
```

### Increase GPU Layers (if VRAM available)
```python
# In config.py:
gpu_layers: int = 50  # Default is 35, increase if you have VRAM
```

### Multi-GPU Setup
If you have multiple GPUs, Ollama can distribute load. Check:
```bash
nvidia-smi  # Should show multiple GPUs
```

## Parallel Processing Optimization

### Current Behavior
- Auto-calculates workers based on GPU count
- Uses ThreadPoolExecutor for I/O-bound LLM calls
- Processes abstracts in parallel per model

### Manual Override
```python
# In config.py:
max_workers: int = 8  # Set explicit number
```

## Model Selection for Speed

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| phi3 | 3.8B | ⚡⚡⚡ | ⭐⭐ | Fastest analysis |
| llama3.1 | 8B | ⚡⚡ | ⭐⭐⭐ | Balanced |
| mistral | 7B | ⚡⚡ | ⭐⭐⭐ | Balanced |
| llama3.2 | 70B | ⚡ | ⭐⭐⭐⭐ | Best quality |
| mixtral | 47B | ⚡ | ⭐⭐⭐⭐ | Best quality |

## Bottleneck Analysis

### Where Time is Spent (Typical Analysis)
1. **LLM Analysis** (60-70%): Analyzing abstracts against KCs
2. **Risk-of-Bias** (20-30%): Assessing study quality
3. **PubMed Search** (5-10%): Fetching abstracts
4. **Certainty Grading** (5-10%): Calculating certainty
5. **Visualization** (1-2%): Creating plots

### Optimization Priority
1. **Reduce abstracts analyzed** (biggest impact)
2. **Use fewer models** (high impact)
3. **Disable RoB** (moderate impact)
4. **Increase parallelization** (moderate impact)
5. **Use faster models** (moderate impact)

## Example: Fast Configuration

Create `fast_config.py`:
```python
from config import AppConfig, SearchConfig, LLMConfig, AnalysisConfig

# Fast configuration
fast_config = AppConfig(
    search=SearchConfig(
        max_abstracts_initial=50,
        max_abstracts_analyze=10,
    ),
    llm=LLMConfig(
        enable_parallel=True,
        max_workers=8,
        gpu_layers=50,
        use_gpu=True,
    ),
    analysis=AnalysisConfig(
        enable_rag=False,
        enable_hierarchical=False,
        enable_rob_default=False,  # Disable RoB for speed
        enable_certainty_default=False,  # Disable certainty for speed
    )
)

# Use it:
from config import set_config
set_config(fast_config)
```

## Monitoring Performance

### Check Current Settings
```python
from config import get_config
config = get_config()
print(f"Parallel: {config.llm.enable_parallel}")
print(f"Workers: {config.llm.max_workers}")
print(f"GPU Layers: {config.llm.gpu_layers}")
print(f"Max Abstracts: {config.search.max_abstracts_analyze}")
```

### Time Analysis
The app prints timing information:
```
⏱️ Total processing time: XXX seconds
```

Look for:
- Per-abstract time (should be < 10s with GPU)
- Total time breakdown by step

## Quick Performance Test

Run a small test to measure speed:
```python
# Test with 5 abstracts
export MAX_ABSTRACTS_ANALYZE=5
python app.py
# Enter a chemical, select 1 fast model (phi3), disable RoB
# Check the total time
```

## Troubleshooting Slow Performance

1. **Check GPU Usage**: `nvidia-smi` - should show GPU utilization
2. **Check Parallel Workers**: Look for "Workers: X" in output
3. **Check Model Size**: Smaller models = faster
4. **Check Number of Abstracts**: Reduce if too many
5. **Check Ollama Status**: `ollama list` - ensure models are loaded

## Advanced: Batch Processing

For analyzing multiple chemicals, consider:
- Running multiple instances (different ports)
- Using MPI for distributed processing
- Processing chemicals sequentially (reuse model loading)
