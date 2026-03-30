# Performance Optimization Guide

## GPU Acceleration

### Automatic GPU Detection

The application automatically detects and uses GPUs if available:
- **CUDA** (NVIDIA GPUs)
- **ROCm** (AMD GPUs)
- **Metal** (Apple Silicon)

### Enabling GPU for Ollama

Ollama automatically uses GPU if available. To ensure optimal performance:

1. **Check GPU availability:**
```bash
python -c "from gpu_utils import check_gpu_available; print(check_gpu_available())"
```

2. **For NVIDIA GPUs:**
```bash
nvidia-smi  # Verify GPU is detected
```

3. **Set GPU layers (more layers = faster but uses more VRAM):**
```python
from config import get_config
config = get_config()
config.llm.gpu_layers = 35  # Default, increase if you have more VRAM
```

### GPU Configuration

```python
from config import get_config

config = get_config()
config.llm.use_gpu = True  # Enable GPU (default: True)
config.llm.gpu_layers = 35  # Layers to offload (default: 35)
```

## Parallel Processing

### Automatic Worker Calculation

The application automatically calculates optimal worker count based on:
- Number of abstracts to process
- Number of models (reviewers)
- GPU availability
- CPU cores

### Manual Configuration

```python
from config import get_config

config = get_config()
config.llm.enable_parallel = True  # Enable parallel processing
config.llm.max_workers = 8  # Set specific worker count (None = auto)
```

### Performance Tips

1. **For GPU systems:**
   - Workers are automatically scaled based on GPU count
   - Each GPU can handle 2+ concurrent requests
   - More GPUs = more parallel workers

2. **For CPU-only systems:**
   - Workers = CPU cores × 2 (for I/O-bound tasks)
   - Minimum 4 workers, maximum based on abstracts count

3. **Multi-reviewer mode:**
   - Each model runs in parallel
   - Abstracts are processed concurrently across models
   - Significantly faster than sequential processing

## MPI (Message Passing Interface)

### Installation

```bash
pip install mpi4py
```

### Running with MPI

**Single node (multiple processes):**
```bash
mpirun -np 4 python app.py
```

**Multiple nodes:**
```bash
mpirun -np 8 --hostfile hosts.txt python app.py
```

Where `hosts.txt` contains:
```
node1 slots=4
node2 slots=4
```

### MPI Configuration

The application automatically detects MPI and distributes work across processes:
- Abstracts are distributed across MPI ranks
- Each process analyzes its assigned abstracts
- Results are gathered to rank 0

## Performance Benchmarks

### Expected Speedup

| Configuration | Speedup |
|--------------|---------|
| Single CPU, Sequential | 1x (baseline) |
| Single CPU, Parallel (4 workers) | 2-3x |
| Single GPU, Parallel | 5-10x |
| Multi-GPU (2 GPUs), Parallel | 10-20x |
| MPI (4 processes) | 3-4x |
| MPI (8 processes) + GPU | 15-30x |

### Optimization Checklist

- [ ] GPU detected and enabled
- [ ] Parallel processing enabled
- [ ] Optimal worker count calculated
- [ ] Ollama using GPU (check with `ollama ps`)
- [ ] Sufficient VRAM for GPU layers
- [ ] Multiple models for multi-reviewer mode

## Troubleshooting

### GPU Not Detected

1. Check GPU drivers:
```bash
nvidia-smi  # For NVIDIA
rocm-smi    # For AMD
```

2. Verify Ollama is using GPU:
```bash
ollama ps
# Check if models show GPU usage
```

3. Set environment variables manually:
```bash
export OLLAMA_GPU_LAYERS=35
export CUDA_VISIBLE_DEVICES=0
```

### Slow Performance

1. **Increase workers:**
```python
config.llm.max_workers = 16  # Increase worker count
```

2. **Enable GPU:**
```python
config.llm.use_gpu = True
config.llm.gpu_layers = 40  # Increase if you have VRAM
```

3. **Use multiple GPUs:**
```bash
export CUDA_VISIBLE_DEVICES=0,1  # Use GPU 0 and 1
```

4. **Reduce analysis limit** (if processing too many abstracts):
```python
config.search.max_abstracts_analyze = 100  # Reduce from 500
```

### Out of Memory (OOM)

1. **Reduce GPU layers:**
```python
config.llm.gpu_layers = 20  # Reduce from 35
```

2. **Reduce workers:**
```python
config.llm.max_workers = 4  # Reduce worker count
```

3. **Process in batches:**
```python
config.search.max_abstracts_analyze = 50  # Process fewer at once
```

## Best Practices

1. **For large-scale analysis (500+ abstracts):**
   - Use GPU if available
   - Enable parallel processing
   - Use multiple models for consensus
   - Consider MPI for distributed computing

2. **For quick analysis (<50 abstracts):**
   - Single model is sufficient
   - GPU optional but recommended
   - Parallel processing still helps

3. **For production use:**
   - Always use GPU if available
   - Enable parallel processing
   - Monitor GPU/CPU usage
   - Adjust workers based on system resources

## Monitoring Performance

### Check GPU Usage

```bash
watch -n 1 nvidia-smi  # Monitor GPU usage
```

### Check CPU Usage

```bash
htop  # Monitor CPU and memory
```

### Check Ollama Status

```bash
ollama ps  # See running models and GPU usage
```

## Example Configurations

### High-Performance Setup (Multi-GPU)

```python
from config import get_config

config = get_config()
config.search.max_abstracts_analyze = 500
config.llm.use_gpu = True
config.llm.gpu_layers = 40
config.llm.enable_parallel = True
config.llm.max_workers = None  # Auto-calculate based on GPUs
```

### Balanced Setup (Single GPU)

```python
config.search.max_abstracts_analyze = 200
config.llm.use_gpu = True
config.llm.gpu_layers = 35
config.llm.enable_parallel = True
config.llm.max_workers = 8
```

### CPU-Only Setup

```python
config.search.max_abstracts_analyze = 100
config.llm.use_gpu = False
config.llm.enable_parallel = True
config.llm.max_workers = 4  # Based on CPU cores
```
