"""NumPy-style docstring template."""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.models.metadata import FunctionMetadata, ClassMetadata


class NumpyTemplate(BaseTemplate):
    """NumPy-style docstring generator.

    Generates docstrings following the NumPy documentation standard.
    See: https://numpydoc.readthedocs.io/en/latest/format.html
    """

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate NumPy-style function docstring.

        Args:
            metadata: Function metadata.

        Returns:
            Generated docstring text.
        """
        lines = []

        # Summary line
        summary = self._generate_summary(metadata)
        lines.append('"""')
        lines.append(summary)

        # Add blank line if there are additional sections
        if metadata.parameters or self._should_include_returns(metadata) or metadata.raises:
            lines.append("")

        # Parameters section
        if metadata.parameters:
            lines.append("Parameters")
            lines.append("----------")
            for param in metadata.parameters:
                param_type = self._format_parameter_type(param)
                optional = ", optional" if param.default_value else ""
                lines.append(f"{param.name} : {param_type}{optional}")

                param_desc = self._generate_parameter_description(param)
                if param.default_value:
                    param_desc += f" Defaults to {param.default_value}."
                lines.append(f"    {param_desc}")

            lines.append("")

        # Returns section
        if self._should_include_returns(metadata):
            lines.append("Returns")
            lines.append("-------")
            return_type = metadata.return_type or "Any"
            lines.append(return_type)
            lines.append("    Return value description.")
            lines.append("")

        # Yields section (for generators)
        if self._should_include_yields(metadata):
            lines.append("Yields")
            lines.append("------")
            yield_type = metadata.return_type or "Any"
            lines.append(yield_type)
            lines.append("    Yielded value description.")
            lines.append("")

        # Raises section
        if metadata.raises:
            lines.append("Raises")
            lines.append("------")
            for exc in metadata.raises:
                lines.append(exc)
                lines.append("    Description of when this is raised.")
            lines.append("")

        # Remove trailing blank line
        while lines and not lines[-1].strip():
            lines.pop()

        # Close docstring
        lines.append('"""')

        return "\n".join(lines)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate NumPy-style class docstring.

        Args:
            metadata: Class metadata.

        Returns:
            Generated docstring text.
        """
        lines = []

        # Summary line
        summary = f"{metadata.name} class."
        if metadata.is_dataclass:
            summary = f"{metadata.name} dataclass."
        lines.append('"""')
        lines.append(summary)

        # Add blank line if there are additional sections
        if metadata.attributes or metadata.bases:
            lines.append("")

        # Attributes section
        if metadata.attributes:
            lines.append("Attributes")
            lines.append("----------")
            for attr in metadata.attributes:
                attr_name = attr["name"]
                attr_type = attr.get("type", "Any")
                lines.append(f"{attr_name} : {attr_type}")
                lines.append(f"    {attr_name} attribute.")
            lines.append("")

        # Remove trailing blank line
        while lines and not lines[-1].strip():
            lines.pop()

        # Close docstring
        lines.append('"""')

        return "\n".join(lines)

    def _generate_summary(self, metadata: FunctionMetadata) -> str:
        """Generate summary line for function.

        Args:
            metadata: Function metadata.

        Returns:
            Summary text.
        """
        name = metadata.name.replace("_", " ").title()

        if metadata.name.startswith("__") and metadata.name.endswith("__"):
            return f"{name} method."

        if metadata.node_type.value in ["method", "async_method"]:
            return f"{name} method."
        elif metadata.node_type.value == "property":
            return f"{name} property."
        else:
            return f"{name} function."
