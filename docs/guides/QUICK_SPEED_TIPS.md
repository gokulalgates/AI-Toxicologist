# ⚡ Quick Speed Improvement Tips

## 🚀 Fastest Improvements (Try These First!)

### 1. **Reduce Abstracts Analyzed** (2x faster)
**In Web Interface**: After entering chemical name, look for "Max abstracts to analyze" setting and reduce from 20 to 10.

**Or set environment variable:**
```bash
export MAX_ABSTRACTS_ANALYZE=10
python app.py
```

### 2. **Use Single Model** (2-3x faster)
**In Web Interface**: Select only **ONE** model instead of multiple models.

**Recommended fast models:**
- `phi3` - Fastest (3.8B)
- `llama3.1` - Fast (8B)  
- `mistral` - Fast (7B)

**Avoid for speed:**
- `llama3.2` - Slower (70B)
- `mixtral` - Slower (47B)

### 3. **Disable Risk-of-Bias** (30% faster)
**In Web Interface**: Uncheck "Enable Risk-of-Bias Assessment"

### 4. **Disable Certainty Grading** (10% faster)
**In Web Interface**: Uncheck "Enable Certainty Grading"

## ⚙️ Configuration File Changes

Edit `config.py`:

```python
# Line 16-17: Reduce abstracts
max_abstracts_initial: int = 50  # Reduced from 100
max_abstracts_analyze: int = 10  # Reduced from 20

# Line 60: Increase GPU layers (if you have VRAM)
gpu_layers: int = 50  # Increased from 35

# Line 58: Set explicit workers
max_workers: int = 8  # Instead of None (auto)
```

## 🎯 Recommended Fast Setup

**For Maximum Speed:**
1. Set `MAX_ABSTRACTS_ANALYZE=10` (or 5 for very fast)
2. Use 1 model: `phi3` or `llama3.1`
3. Disable Risk-of-Bias
4. Disable Certainty Grading

**Expected time**: 5-10 minutes (vs 30-60 minutes default)

**For Balanced Speed/Quality:**
1. Set `MAX_ABSTRACTS_ANALYZE=15`
2. Use 1-2 models: `llama3.2` or `mistral`
3. Keep Risk-of-Bias enabled
4. Keep Certainty Grading enabled

**Expected time**: 15-25 minutes

## 🔧 Using the Optimization Script

```bash
# Apply fast settings
python optimize_performance.py 1

# Apply balanced settings  
python optimize_performance.py 2

# Apply maximum speed settings
python optimize_performance.py 3
```

Then restart `app.py`

## 📊 Check Current Settings

```python
from config import get_config
config = get_config()
print(f"Max abstracts: {config.search.max_abstracts_analyze}")
print(f"Workers: {config.llm.max_workers}")
print(f"GPU layers: {config.llm.gpu_layers}")
```

## 💡 Additional Tips

1. **Check GPU Usage**: `nvidia-smi` - should show GPU utilization
2. **Use Faster Models**: phi3 is 5x faster than llama3.2
3. **Reduce Initial Fetch**: `MAX_ABSTRACTS_INITIAL=50` instead of 100
4. **Monitor Progress**: Watch the progress bar for bottlenecks

## ⚠️ Trade-offs

| Optimization | Speed Gain | Quality Loss |
|--------------|------------|--------------|
| Reduce abstracts (20→10) | 2x | Small |
| Single model | 2-3x | Moderate |
| Disable RoB | 1.3x | Small |
| Faster model (phi3) | 5x | Moderate |
| All combined | 10-20x | Moderate |
