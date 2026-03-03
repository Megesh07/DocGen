"""Parser package for AST-based code analysis."""
from autodocstring.parser.ast_parser import SourceCodeParser, parse_file
from autodocstring.parser.extractors import (
    ClassExtractor,
    FunctionExtractor,
    DecoratorExtractor,
)

__all__ = [
    "SourceCodeParser",
    "parse_file",
    "ClassExtractor",
    "FunctionExtractor",
    "DecoratorExtractor",
]
