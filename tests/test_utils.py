"""
Tests for utility functions.
"""

import time
import unittest

from exceptions import LLMError
from utils import cache_result, clear_cache, hash_text, retry_with_backoff, truncate_text


class TestUtils(unittest.TestCase):
    """Test utility functions"""

    def setUp(self):
        """Clear cache before each test"""
        clear_cache()

    def test_hash_text(self):
        """Test text hashing"""
        text1 = "test text"
        text2 = "test text"
        text3 = "different text"

        hash1 = hash_text(text1)
        hash2 = hash_text(text2)
        hash3 = hash_text(text3)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 64)  # SHA256 hex length

    def test_truncate_text(self):
        """Test text truncation"""
        long_text = "a" * 100
        short_text = "abc"

        truncated = truncate_text(long_text, 50)
        self.assertEqual(len(truncated), 50)
        self.assertTrue(truncated.endswith("..."))

        not_truncated = truncate_text(short_text, 50)
        self.assertEqual(not_truncated, short_text)

    def test_retry_success(self):
        """Test retry decorator with successful call"""
        call_count = [0]

        @retry_with_backoff(max_retries=3, delay=0.01)
        def successful_func():
            call_count[0] += 1
            return "success"

        result = successful_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 1)

    def test_retry_failure(self):
        """Test retry decorator with failing call"""
        call_count = [0]

        @retry_with_backoff(max_retries=2, delay=0.01)
        def failing_func():
            call_count[0] += 1
            raise ValueError("test error")

        with self.assertRaises(LLMError):
            failing_func()

        self.assertEqual(call_count[0], 3)  # Initial + 2 retries

    def test_cache_result(self):
        """Test result caching"""
        call_count = [0]

        @cache_result(ttl=1.0)
        def cached_func(x):
            call_count[0] += 1
            return x * 2

        # First call - should execute function
        result1 = cached_func(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count[0], 1)

        # Second call - should use cache
        result2 = cached_func(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count[0], 1)  # No additional call

        # Different argument - should execute again
        result3 = cached_func(6)
        self.assertEqual(result3, 12)
        self.assertEqual(call_count[0], 2)

    def test_cache_expiration(self):
        """Test cache expiration"""
        call_count = [0]

        @cache_result(ttl=0.1)  # Very short TTL
        def cached_func(x):
            call_count[0] += 1
            return x * 2

        # First call
        cached_func(5)
        self.assertEqual(call_count[0], 1)

        # Second call immediately - should use cache
        cached_func(5)
        self.assertEqual(call_count[0], 1)

        # Wait for expiration
        time.sleep(0.15)

        # Third call - should execute again
        cached_func(5)
        self.assertEqual(call_count[0], 2)


if __name__ == "__main__":
    unittest.main()
