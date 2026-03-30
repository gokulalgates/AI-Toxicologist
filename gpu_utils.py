"""
GPU and parallel processing utilities for AI Toxicologist.

Provides GPU detection, multi-GPU support, and optimized parallel processing.
"""

import os
import subprocess
from typing import Dict

from config import get_config


def check_gpu_available() -> Dict[str, bool]:
    """
    Check GPU availability (CUDA, ROCm, Metal).
    
    Returns:
        Dict with 'cuda', 'rocm', 'metal', 'available' keys
    """
    gpu_info = {
        'cuda': False,
        'rocm': False,
        'metal': False,
        'available': False
    }

    # Check CUDA
    try:
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            gpu_info['cuda'] = True
            gpu_info['available'] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check ROCm (AMD)
    try:
        result = subprocess.run(['rocm-smi'], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            gpu_info['rocm'] = True
            gpu_info['available'] = True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check Metal (Apple Silicon)
    if os.uname().sysname == 'Darwin':
        try:
            result = subprocess.run(['system_profiler', 'SPDisplaysDataType'],
                                  capture_output=True, text=True, timeout=2)
            if 'Metal' in result.stdout:
                gpu_info['metal'] = True
                gpu_info['available'] = True
        except:
            pass

    return gpu_info


def get_gpu_count() -> int:
    """Get number of available GPUs"""
    gpu_info = check_gpu_available()

    if gpu_info['cuda']:
        try:
            result = subprocess.run(['nvidia-smi', '--list-gpus'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return len(result.stdout.strip().split('\n'))
        except:
            pass

    if gpu_info['rocm']:
        try:
            result = subprocess.run(['rocm-smi', '--showid'],
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                # Count unique GPU IDs
                lines = [l for l in result.stdout.split('\n') if 'GPU' in l]
                return len(set(lines))
        except:
            pass

    return 1 if gpu_info['available'] else 0


def configure_ollama_gpu() -> Dict[str, str]:
    """
    Configure Ollama to use GPU.
    
    Returns:
        Dict with environment variables to set for GPU usage
    """
    gpu_info = check_gpu_available()
    env_vars = {}

    if gpu_info['cuda']:
        # CUDA/ROCm - Ollama should auto-detect, but we can set explicit vars
        env_vars['OLLAMA_GPU_LAYERS'] = os.getenv('OLLAMA_GPU_LAYERS', '35')  # Use more GPU layers
        env_vars['CUDA_VISIBLE_DEVICES'] = os.getenv('CUDA_VISIBLE_DEVICES', '')  # Use all GPUs by default

    if gpu_info['rocm']:
        env_vars['HIP_VISIBLE_DEVICES'] = os.getenv('HIP_VISIBLE_DEVICES', '')

    if gpu_info['metal']:
        # Metal is auto-detected on macOS
        pass

    return env_vars


def get_optimal_workers(num_abstracts: int, num_models: int, num_gpus: int = 0) -> int:
    """
    Calculate optimal number of worker processes/threads.
    
    Args:
        num_abstracts: Number of abstracts to process
        num_models: Number of models (reviewers)
        num_gpus: Number of available GPUs
    
    Returns:
        Optimal number of workers
    """
    config = get_config()

    if config.llm.max_workers is not None:
        return config.llm.max_workers

    # If GPUs available, use one worker per GPU per model
    if num_gpus > 0:
        # Each GPU can handle multiple requests, but limit to avoid OOM
        # Increased from 2 to 4 for better parallelization (if VRAM allows)
        workers_per_gpu = 4  # More aggressive parallelization
        optimal = min(num_abstracts, num_models * num_gpus * workers_per_gpu)
        # Ensure at least 2 workers for parallelization benefits
        return max(2, optimal)

    # CPU-only: use CPU count, but limit based on task
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()

    # For I/O-bound LLM calls, we can use more workers than CPU cores
    # But limit to avoid overwhelming the system
    # Increased multiplier from 2 to 3 for better CPU utilization
    return min(num_abstracts, max(4, cpu_count * 3))


def setup_gpu_environment():
    """Set up environment variables for GPU usage"""
    gpu_env = configure_ollama_gpu()
    for key, value in gpu_env.items():
        if value:  # Only set if value is not empty
            os.environ[key] = value

    return gpu_env
