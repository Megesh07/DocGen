"""Extractors for specific AST node types.

This module contains specialized extractors for classes, functions,
decorators, and type hints.
"""
import ast
from typing import Optional, List

from autodocstring.models.metadata import (
    ClassMetadata,
    FunctionMetadata,
    ParameterMetadata,
    NodeType,
)


def extract_docstring(node: ast.AST) -> Optional[str]:
    """Extract docstring from an AST node.

    Args:
        node: AST node (Module, ClassDef, or FunctionDef).

    Returns:
        Docstring text if present, None otherwise.
    """
    return ast.get_docstring(node)


def get_type_annotation(annotation: Optional[ast.expr]) -> Optional[str]:
    """Convert type annotation to string.

    Args:
        annotation: AST annotation node.

    Returns:
        String representation of type annotation.
    """
    if annotation is None:
        return None
    try:
        if hasattr(ast, "unparse"):
            return ast.unparse(annotation)
        else:
            # Fallback for Python < 3.9
            return ast.dump(annotation)
    except Exception:
        return None


class DecoratorExtractor:
    """Extractor for decorator information."""

    @staticmethod
    def extract(node: ast.AST) -> List[str]:
        """Extract decorator names from a node.

        Args:
            node: AST node with decorators.

        Returns:
            List of decorator names.
        """
        decorators = []
        if hasattr(node, "decorator_list"):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                    decorators.append(dec.func.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(dec.attr)
        return decorators


class FunctionExtractor:
    """Extractor for function and method metadata."""

    def __init__(self, source_lines: List[str]):
        """Initialize extractor.

        Args:
            source_lines: Source code lines for reference.
        """
        self.source_lines = source_lines

    def extract(
        self, node: ast.AST, parent_class: Optional[str] = None
    ) -> FunctionMetadata:
        """Extract metadata from a function or method node.

        Args:
            node: FunctionDef or AsyncFunctionDef node.
            parent_class: Name of parent class if this is a method.

        Returns:
            FunctionMetadata object.
        """
        is_async = isinstance(node, ast.AsyncFunctionDef)
        decorators = DecoratorExtractor.extract(node)

        # Determine node type
        node_type = self._determine_node_type(decorators, is_async, parent_class)

        # Extract parameters
        parameters = self._extract_parameters(node.args)

        # Extract return type
        return_type = get_type_annotation(node.returns)

        # Check if generator
        is_generator = self._is_generator(node)

        # Extract raised exceptions
        raises = self._extract_raises(node)

        # Get docstring
        docstring = extract_docstring(node)

        return FunctionMetadata(
            name=node.name,
            node_type=node_type,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            parameters=parameters,
            return_type=return_type,
            decorators=decorators,
            is_async=is_async,
            is_generator=is_generator,
            raises=raises,
            docstring=docstring,
            parent_class=parent_class,
        )

    def _determine_node_type(
        self, decorators: List[str], is_async: bool, parent_class: Optional[str]
    ) -> NodeType:
        """Determine the specific node type.

        Args:
            decorators: List of decorator names.
            is_async: Whether function is async.
            parent_class: Parent class name if method.

        Returns:
            NodeType enum value.
        """
        if "property" in decorators:
            return NodeType.PROPERTY
        if "staticmethod" in decorators:
            return NodeType.STATICMETHOD
        if "classmethod" in decorators:
            return NodeType.CLASSMETHOD

        if parent_class:
            return NodeType.ASYNC_METHOD if is_async else NodeType.METHOD
        else:
            return NodeType.ASYNC_FUNCTION if is_async else NodeType.FUNCTION

    def _extract_parameters(self, args: ast.arguments) -> List[ParameterMetadata]:
        """Extract parameter metadata from function arguments.

        Args:
            args: ast.arguments node.

        Returns:
            List of ParameterMetadata objects.
        """
        parameters = []

        # Regular positional arguments
        defaults_offset = len(args.args) - len(args.defaults)
        for i, arg in enumerate(args.args):
            # Skip 'self' and 'cls' parameters
            if arg.arg in ("self", "cls"):
                continue

            default_idx = i - defaults_offset
            default_value = None
            if default_idx >= 0:
                default_node = args.defaults[default_idx]
                default_value = (
                    ast.unparse(default_node)
                    if hasattr(ast, "unparse")
                    else ast.dump(default_node)
                )
                # Normalize string quotes for consistency
                if default_value and isinstance(default_node, ast.Constant) and isinstance(default_node.value, str):
                    # Use double quotes for string literals
                    default_value = f'"{default_node.value}"'

            parameters.append(
                ParameterMetadata(
                    name=arg.arg,
                    type_hint=get_type_annotation(arg.annotation),
                    default_value=default_value,
                )
            )

        # *args
        if args.vararg:
            parameters.append(
                ParameterMetadata(
                    name=args.vararg.arg,
                    type_hint=get_type_annotation(args.vararg.annotation),
                    is_args=True,
                )
            )

        # Keyword-only arguments
        kw_defaults_map = {
            kw.arg: default for kw, default in zip(args.kwonlyargs, args.kw_defaults)
        }
        for arg in args.kwonlyargs:
            default_node = kw_defaults_map.get(arg.arg)
            default_value = None
            if default_node:
                default_value = (
                    ast.unparse(default_node)
                    if hasattr(ast, "unparse")
                    else ast.dump(default_node)
                )
                # Normalize string quotes for consistency
                if default_value and isinstance(default_node, ast.Constant) and isinstance(default_node.value, str):
                    # Use double quotes for string literals
                    default_value = f'"{default_node.value}"'

            parameters.append(
                ParameterMetadata(
                    name=arg.arg,
                    type_hint=get_type_annotation(arg.annotation),
                    default_value=default_value,
                )
            )

        # **kwargs
        if args.kwarg:
            parameters.append(
                ParameterMetadata(
                    name=args.kwarg.arg,
                    type_hint=get_type_annotation(args.kwarg.annotation),
                    is_kwargs=True,
                )
            )

        return parameters

    def _is_generator(self, node: ast.AST) -> bool:
        """Check if function is a generator (contains yield).

        Args:
            node: Function node.

        Returns:
            True if function contains yield statement.
        """
        for child in ast.walk(node):
            if isinstance(child, (ast.Yield, ast.YieldFrom)):
                return True
        return False

    def _extract_raises(self, node: ast.AST) -> List[str]:
        """Extract exception types that may be raised.

        Args:
            node: Function node.

        Returns:
            List of exception class names.
        """
        raises = []
        for child in ast.walk(node):
            if isinstance(child, ast.Raise):
                if child.exc:
                    if isinstance(child.exc, ast.Call):
                        if isinstance(child.exc.func, ast.Name):
                            raises.append(child.exc.func.id)
                    elif isinstance(child.exc, ast.Name):
                        raises.append(child.exc.id)
        return list(set(raises))  # Remove duplicates


class ClassExtractor:
    """Extractor for class metadata."""

    def __init__(self, source_lines: List[str]):
        """Initialize extractor.

        Args:
            source_lines: Source code lines for reference.
        """
        self.source_lines = source_lines
        self.function_extractor = FunctionExtractor(source_lines)

    def extract(self, node: ast.ClassDef) -> ClassMetadata:
        """Extract metadata from a class node.

        Args:
            node: ClassDef node.

        Returns:
            ClassMetadata object.
        """
        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(base.attr)

        # Extract decorators
        decorators = DecoratorExtractor.extract(node)
        is_dataclass = "dataclass" in decorators

        # Get docstring
        docstring = extract_docstring(node)

        # Extract methods
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_meta = self.function_extractor.extract(item, parent_class=node.name)
                methods.append(method_meta)

        # Extract attributes (for dataclasses and annotated attributes)
        attributes = self._extract_attributes(node)

        return ClassMetadata(
            name=node.name,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            bases=bases,
            decorators=decorators,
            methods=methods,
            attributes=attributes,
            docstring=docstring,
            is_dataclass=is_dataclass,
        )

    def _extract_attributes(self, node: ast.ClassDef) -> List[dict]:
        """Extract class attributes.

        Args:
            node: ClassDef node.

        Returns:
            List of attribute dictionaries.
        """
        attributes = []
        for item in node.body:
            # Annotated assignments (e.g., x: int = 5)
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                attributes.append(
                    {
                        "name": item.target.id,
                        "type": get_type_annotation(item.annotation),
                        "lineno": item.lineno,
                    }
                )
            # Regular assignments in __init__ are harder to track statically
            # For now, we focus on class-level attributes
        return attributes
