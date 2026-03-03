"""Base template class for docstring generation."""
from abc import ABC, abstractmethod
from typing import Optional

from autodocstring.models.metadata import (
    FunctionMetadata,
    ClassMetadata,
    ParameterMetadata,
)


class BaseTemplate(ABC):
    """Abstract base class for docstring templates.

    All style-specific templates inherit from this class and implement
    the abstract methods for generating docstrings.
    """

    @abstractmethod
    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate docstring for a function.

        Args:
            metadata: Function metadata.

        Returns:
            Generated docstring text.
        """
        pass

    @abstractmethod
    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate docstring for a class.

        Args:
            metadata: Class metadata.

        Returns:
            Generated docstring text.
        """
        pass

    def _format_parameter_type(self, param: ParameterMetadata) -> str:
        """Format parameter type for display.

        Args:
            param: Parameter metadata.

        Returns:
            Formatted type string.
        """
        if param.type_hint:
            return param.type_hint
        return "Any"

    def _generate_parameter_description(self, param: ParameterMetadata) -> str:
        """Generate a basic description for a parameter.

        Args:
            param: Parameter metadata.

        Returns:
            Parameter description.
        """
        if param.description:
            return param.description

        # Generate basic description based on name
        name = param.name.replace("_", " ")
        if param.is_args:
            return "Variable length argument list."
        elif param.is_kwargs:
            return "Arbitrary keyword arguments."
        else:
            return f"The {name} parameter."

    def _should_include_returns(self, metadata: FunctionMetadata) -> bool:
        """Check if Returns section should be included.

        Args:
            metadata: Function metadata.

        Returns:
            True if Returns section should be included.
        """
        # Include if return type is specified and not None
        if metadata.return_type and metadata.return_type.lower() != "none":
            return True
        # Don't include for __init__ methods
        if metadata.name == "__init__":
            return False
        return False

    def _should_include_yields(self, metadata: FunctionMetadata) -> bool:
        """Check if Yields section should be included.

        Args:
            metadata: Function metadata.

        Returns:
            True if Yields section should be included.
        """
        return metadata.is_generator

    def _indent_docstring(self, text: str, indent: int = 4) -> str:
        """Indent docstring text.

        Args:
            text: Docstring text.
            indent: Number of spaces to indent.

        Returns:
            Indented text.
        """
        lines = text.split("\n")
        indent_str = " " * indent
        return "\n".join(indent_str + line if line.strip() else "" for line in lines)
