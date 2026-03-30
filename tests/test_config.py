"""
Tests for configuration management.
"""

import unittest
import os
from config import AppConfig, get_config, set_config, reset_config


class TestConfig(unittest.TestCase):
    """Test configuration management"""
    
    def setUp(self):
        """Reset config before each test"""
        reset_config()
    
    def test_default_config(self):
        """Test default configuration values"""
        config = get_config()
        
        self.assertEqual(config.search.max_abstracts_initial, 75)
        self.assertEqual(config.search.max_abstracts_analyze, 15)
        self.assertEqual(config.search.max_search_terms, 8)
        self.assertEqual(config.llm.temperature, 0.1)
        self.assertEqual(config.llm.max_retries, 3)
    
    def test_config_from_env(self):
        """Test loading configuration from environment variables"""
        os.environ["MAX_ABSTRACTS_INITIAL"] = "200"
        os.environ["MAX_ABSTRACTS_ANALYZE"] = "30"
        os.environ["LLM_TEMPERATURE"] = "0.5"
        
        reset_config()  # Force reload
        config = AppConfig.from_env()
        
        self.assertEqual(config.search.max_abstracts_initial, 200)
        self.assertEqual(config.search.max_abstracts_analyze, 30)
        self.assertEqual(config.llm.temperature, 0.5)
        
        # Cleanup
        del os.environ["MAX_ABSTRACTS_INITIAL"]
        del os.environ["MAX_ABSTRACTS_ANALYZE"]
        del os.environ["LLM_TEMPERATURE"]
    
    def test_set_config(self):
        """Test setting custom configuration"""
        custom_config = AppConfig()
        custom_config.search.max_abstracts_initial = 150
        
        set_config(custom_config)
        config = get_config()
        
        self.assertEqual(config.search.max_abstracts_initial, 150)
    
    def test_config_singleton(self):
        """Test that get_config returns the same instance"""
        config1 = get_config()
        config2 = get_config()
        
        self.assertIs(config1, config2)


if __name__ == "__main__":
    unittest.main()
