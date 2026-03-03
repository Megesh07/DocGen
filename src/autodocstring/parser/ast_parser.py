"""AST-based Python source code parser.

This module provides the main parser for extracting metadata from Python
source files using the Abstract Syntax Tree (ast) module.
"""
import ast
from pathlib import Path
from typing import Optional

from autodocstring.models.metadata import ModuleMetadata, ClassMetadata, FunctionMetadata
from autodocstring.parser.extractors import (
    ClassExtractor,
    FunctionExtractor,
    extract_docstring,
)


class SourceCodeParser:
    """Main parser for Python source code.

    Uses AST to extract comprehensive metadata about modules, classes,
    functions, and their documentation.

    Attributes:
        filepath: Path to the source file being parsed.
        tree: Parsed AST tree.
        source_lines: Source code lines for reference.
    """

    def __init__(self, filepath: str):
        """Initialize parser with a source file.

        Args:
            filepath: Path to Python source file.

        Raises:
            FileNotFoundError: If filepath does not exist.
            SyntaxError: If file contains invalid Python syntax.
        """
        self.filepath = Path(filepath)
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(self.filepath, "r", encoding="utf-8") as f:
            self.source = f.read()
            self.source_lines = self.source.splitlines()

        try:
            self.tree = ast.parse(self.source, filename=str(self.filepath))
        except SyntaxError as e:
            raise SyntaxError(f"Syntax error in {filepath}: {e}")

    def parse(self) -> ModuleMetadata:
        """Parse the source file and extract all metadata.

        Returns:
            ModuleMetadata object containing all extracted information.
        """
        module_name = self.filepath.stem
        module_docstring = extract_docstring(self.tree)

        metadata = ModuleMetadata(
            filepath=str(self.filepath),
            module_name=module_name,
            docstring=module_docstring,
        )

        # Extract imports
        metadata.imports = self._extract_imports()

        # Extract classes and their methods
        class_extractor = ClassExtractor(self.source_lines)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                # Only process top-level classes (not nested)
                if self._is_top_level(node):
                    class_meta = class_extractor.extract(node)
                    metadata.classes.append(class_meta)

        # Extract module-level functions
        function_extractor = FunctionExtractor(self.source_lines)
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only process top-level functions (not methods)
                if self._is_top_level(node):
                    func_meta = function_extractor.extract(node)
                    metadata.functions.append(func_meta)

        # Extract module-level constants
        metadata.constants = self._extract_constants()

        return metadata

    def _is_top_level(self, node: ast.AST) -> bool:
        """Check if a node is at module level (not nested).

        Args:
            node: AST node to check.

        Returns:
            True if node is at module level.
        """
        for parent_node in ast.walk(self.tree):
            if isinstance(parent_node, ast.Module):
                if node in parent_node.body:
                    return True
        return False

    def _extract_imports(self) -> list:
        """Extract import statements from the module.

        Returns:
            List of import statement strings.
        """
        imports = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
        return imports

    def _extract_constants(self) -> list:
        """Extract module-level constant assignments.

        Returns:
            List of dictionaries with constant metadata.
        """
        constants = []
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        # Convention: UPPERCASE names are constants
                        if target.id.isupper():
                            constants.append(
                                {
                                    "name": target.id,
                                    "lineno": node.lineno,
                                    "value": ast.unparse(node.value)
                                    if hasattr(ast, "unparse")
                                    else None,
                                }
                            )
        return constants


def parse_file(filepath: str) -> ModuleMetadata:
    """Parse a Python file and extract metadata.

    Convenience function for one-shot parsing.

    Args:
        filepath: Path to Python source file.

    Returns:
        ModuleMetadata object with extracted information.

    Raises:
        FileNotFoundError: If file does not exist.
        SyntaxError: If file contains invalid Python.
    """
    parser = SourceCodeParser(filepath)
    return parser.parse()
