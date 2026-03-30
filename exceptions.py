"""
Custom exception classes for AI Toxicologist application.

Provides specific exception types for better error handling and debugging.
"""


class ToxicologistException(Exception):
    """Base exception for all application errors"""
    pass


class SearchError(ToxicologistException):
    """Error during PubMed search or data retrieval"""
    pass


class ChemicalStandardizationError(ToxicologistException):
    """Error standardizing chemical name or retrieving PubChem data"""
    pass


class LLMError(ToxicologistException):
    """Error during LLM processing"""
    pass


class LLMTimeoutError(LLMError):
    """LLM request timed out"""
    pass


class LLMParseError(LLMError):
    """Failed to parse LLM response"""
    pass


class AnalysisError(ToxicologistException):
    """Error during KC analysis or processing"""
    pass


class ValidationError(ToxicologistException):
    """Data validation error"""
    pass


class ConfigurationError(ToxicologistException):
    """Configuration error"""
    pass


class ProvenanceError(ToxicologistException):
    """Error saving or loading provenance data"""
    pass


class MultiReviewerError(ToxicologistException):
    """Error in multi-reviewer consensus building"""
    pass
