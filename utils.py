"""
Utility functions for AI Toxicologist application.

Includes retry logic, caching, and performance optimizations.
"""

from __future__ import annotations

import functools
import hashlib
import time
from typing import Any, Callable, Dict, Optional

from config import get_config
from exceptions import LLMError, LLMTimeoutError

# Simple in-memory cache for LLM responses
_cache: Dict[str, tuple[Any, float]] = {}
_cache_ttl: float = 3600.0  # 1 hour default TTL


def clear_cache() -> None:
    """Clear the in-memory cache"""
    global _cache
    _cache.clear()


def get_cache_size() -> int:
    """Get current cache size"""
    return len(_cache)


def retry_with_backoff(
    max_retries: Optional[int] = None,
    delay: Optional[float] = None,
    backoff_factor: float = 2.0,
    timeout: Optional[float] = None,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries (uses config if None)
        delay: Initial delay in seconds (uses config if None)
        backoff_factor: Multiplier for delay after each retry
        timeout: Maximum time to wait in seconds (uses config if None)
        exceptions: Tuple of exceptions to catch and retry on
    """
    config = get_config()

    if max_retries is None:
        max_retries = config.llm.max_retries
    if delay is None:
        delay = config.llm.retry_delay
    if timeout is None:
        timeout = config.search.llm_timeout

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            start_time = time.time()

            for attempt in range(max_retries + 1):
                try:
                    # Check timeout
                    if timeout and (time.time() - start_time) > timeout:
                        raise LLMTimeoutError(
                            f"Function {func.__name__} timed out after {timeout}s"
                        )

                    return func(*args, **kwargs)

                except exceptions as e:
                    if attempt == max_retries:
                        # Last attempt failed
                        raise LLMError(
                            f"Function {func.__name__} failed after {max_retries} retries: {e}"
                        ) from e

                    # Wait before retrying
                    time.sleep(current_delay)
                    current_delay *= backoff_factor

                    if config.debug:
                        print(f"Retry {attempt + 1}/{max_retries} for {func.__name__} after {current_delay:.1f}s delay")

            # Should never reach here, but just in case
            raise LLMError(f"Function {func.__name__} failed unexpectedly")

        return wrapper
    return decorator


def cache_result(ttl: Optional[float] = None, key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time-to-live in seconds (uses default if None)
        key_func: Function to generate cache key from args/kwargs
    """
    if ttl is None:
        ttl = _cache_ttl

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: hash of function name + args + kwargs
                key_data = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
                cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Check cache
            if cache_key in _cache:
                result, timestamp = _cache[cache_key]
                if time.time() - timestamp < ttl:
                    if get_config().debug:
                        print(f"Cache hit for {func.__name__}")
                    return result
                else:
                    # Expired
                    del _cache[cache_key]

            # Call function and cache result
            result = func(*args, **kwargs)
            _cache[cache_key] = (result, time.time())

            if get_config().debug:
                print(f"Cached result for {func.__name__}")

            return result

        return wrapper
    return decorator


def hash_text(text: str) -> str:
    """Generate SHA256 hash of text"""
    return hashlib.sha256(text.encode()).hexdigest()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
