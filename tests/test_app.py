"""
Tests for main application functions.
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

import pandas as pd

from app import (
    analyze_abstract_with_llm,
    check_relevance,
    create_evidence_matrix,
    standardize_chemical_name,
)
from config import get_config


class TestApp(unittest.TestCase):
    """Test main application functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = get_config()
        self.config.debug = False  # Disable debug mode for tests

    def test_standardize_chemical_name(self):
        """Test chemical name standardization"""
        # Mock PubChem response
        with patch('app.pcp.get_compounds') as mock_get:
            mock_compound = Mock()
            mock_compound.iupac_name = "Test IUPAC Name"
            mock_compound.cid = 12345
            mock_compound.synonyms = ["synonym1", "synonym2", "test chemical"]
            mock_get.return_value = [mock_compound]

            name, cid, terms = standardize_chemical_name("test")

            self.assertEqual(cid, "12345")
            self.assertIn("test", terms)
            self.assertLessEqual(len(terms), self.config.search.max_search_terms)

    def test_standardize_chemical_name_not_found(self):
        """Test chemical name standardization when not found"""
        with patch('app.pcp.get_compounds') as mock_get:
            mock_get.return_value = []

            name, cid, terms = standardize_chemical_name("nonexistent")

            self.assertEqual(name, "nonexistent")
            self.assertIsNone(cid)
            self.assertEqual(terms, ["nonexistent"])

    @patch('app.ChatOllama')
    def test_check_relevance(self, mock_llm_class):
        """Test relevance checking"""
        # Mock LLM response
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = "YES"
        mock_llm.invoke.return_value = mock_response
        mock_llm_class.return_value = mock_llm

        result = check_relevance("abstract text", "title", "chemical")
        self.assertTrue(result)

    def test_create_evidence_matrix(self):
        """Test evidence matrix creation"""
        abstracts = [
            {"title": "Paper 1", "pmid": "123"},
            {"title": "Paper 2", "pmid": "456"}
        ]

        kc_analyses = [
            {"kc1_status": "SUPPORTED", "kc2_status": "NOT_MENTIONED"},
            {"kc1_status": "REFUTED", "kc2_status": "SUPPORTED"}
        ]

        df = create_evidence_matrix(abstracts, kc_analyses)

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertIn("KC1", df.columns)
        self.assertIn("KC2", df.columns)
        self.assertEqual(df.loc[0, "KC1"], 1)  # SUPPORTED
        self.assertEqual(df.loc[1, "KC1"], -1)  # REFUTED

    @patch('app.PydanticOutputParser')
    @patch('app.ChatOllama')
    def test_analyze_abstract_with_llm_dict_reasoning(self, mock_llm_class, mock_parser_class):
        """Test that analyze_abstract_with_llm correctly handles a dict in the reasoning field"""
        # Mock the LLM so we don't actually call it
        mock_llm_class.return_value.invoke.return_value.content = '{"kc1_status": "SUPPORTED", "reasoning": {"text": ["line 1", "line 2"]}}'

        # Mock the Pydantic parser to return a specific object
        mock_parser = MagicMock()

        mock_result = MagicMock()
        for i in range(1, 13):
            setattr(mock_result, f'kc{i}_status', "NOT_MENTIONED")
        mock_result.kc1_status = "SUPPORTED"
        mock_result.reasoning = {'text': ['line 1', 'line 2']}
        mock_result.causal_links = []
        mock_result.evidence_quotes = {}
        mock_result.dose_response = []

        mock_parser.parse.return_value = mock_result
        mock_parser_class.return_value = mock_parser

        # Call the function
        analysis, _ = analyze_abstract_with_llm("abstract", "title")

        # Check that the reasoning was correctly processed
        self.assertEqual(analysis["reasoning"], "line 1\nline 2")

if __name__ == "__main__":
    unittest.main()
