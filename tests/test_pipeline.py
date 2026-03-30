import unittest
from unittest.mock import MagicMock, patch
import logging

# Import the class to test
from pipeline import HepatotoxicityPipeline

class TestHepatotoxicityPipeline(unittest.TestCase):
    def setUp(self):
        self.pipeline = HepatotoxicityPipeline()
        # Disable logging during tests
        logging.getLogger('pipeline').setLevel(logging.CRITICAL)

    @patch('pipeline.standardize_chemical_name')
    @patch('pipeline.fetch_pubmed_enhanced')
    @patch('pipeline.check_relevance')
    @patch('pipeline.analyze_abstract_with_llm')
    def test_run_pipeline_success(self, mock_analyze, mock_relevance, mock_fetch, mock_standardize):
        # Setup mocks
        mock_standardize.return_value = ("Acetaminophen", "1983", ["acetaminophen", "paracetamol"])
        
        mock_fetch.return_value = [
            {"title": "Paper 1", "text": "Abstract 1", "pmid": "1"},
            {"title": "Paper 2", "text": "Abstract 2", "pmid": "2"}
        ]
        
        # Mock relevance: Paper 1 is relevant, Paper 2 is not
        mock_relevance.side_effect = [True, False]
        
        # Mock analysis result
        mock_analyze.return_value = ({
            "kc1_status": "SUPPORTED",
            "reasoning": "Test reasoning"
        }, "hash123")
        
        # Run pipeline
        results = self.pipeline.run_pipeline(
            chemical_name="test_chem",
            models=["llama3"],
            enable_rob=False
        )
        
        # Assertions
        self.assertEqual(results["chemical_name"], "Acetaminophen")
        self.assertEqual(len(results["abstracts"]), 1) # Only 1 relevant
        self.assertEqual(results["abstracts"][0]["title"], "Paper 1")
        self.assertEqual(len(results["analyzed_records"]), 1)
        self.assertEqual(results["analyzed_records"][0]["analysis"]["kc1_status"], "SUPPORTED")
        
        # Verify calls
        mock_standardize.assert_called_once()
        mock_fetch.assert_called_once()
        self.assertEqual(mock_relevance.call_count, 2)
        mock_analyze.assert_called_once()

    @patch('pipeline.standardize_chemical_name')
    @patch('pipeline.fetch_pubmed_enhanced')
    def test_run_pipeline_no_abstracts(self, mock_fetch, mock_standardize):
        mock_standardize.return_value = ("Unknown", None, ["Unknown"])
        mock_fetch.return_value = [] # No results
        
        from exceptions import SearchError
        with self.assertRaises(SearchError):
            self.pipeline.run_pipeline("unknown_chem", ["llama3"])

if __name__ == '__main__':
    unittest.main()
