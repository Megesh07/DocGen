"""Automated Python Docstring Generator.

A production-grade system for generating, validating, and managing
Python docstrings using static analysis.
"""

__version__ = "2.0.0"
__author__ = "Megesh"
__license__ = "MIT"

from autodocstring.parser.ast_parser import SourceCodeParser
from autodocstring.generator.engine import DocstringGenerator
from autodocstring.validation.validator import DocstringValidator
from autodocstring.validation.coverage import CoverageAnalyzer

__all__ = [
    "SourceCodeParser",
    "DocstringGenerator",
    "DocstringValidator",
    "CoverageAnalyzer",
]
