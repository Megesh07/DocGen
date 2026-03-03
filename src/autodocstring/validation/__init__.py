"""Validation package for docstring quality and coverage."""
from autodocstring.validation.validator import DocstringValidator, ValidationIssue
from autodocstring.validation.coverage import CoverageAnalyzer, CoverageStats, FileCoverage
from autodocstring.validation.rules import Severity, STANDARD_RULES

__all__ = [
    "DocstringValidator",
    "ValidationIssue",
    "CoverageAnalyzer",
    "CoverageStats",
    "FileCoverage",
    "Severity",
    "STANDARD_RULES",
]
