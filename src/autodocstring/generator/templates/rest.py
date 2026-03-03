"""reStructuredText-style docstring template."""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.models.metadata import FunctionMetadata, ClassMetadata


class RestTemplate(BaseTemplate):
    """reStructuredText-style docstring generator.

    Generates docstrings following Sphinx/reST conventions.
    See: https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html
    """

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate reST-style function docstring.

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

        # Parameters
        if metadata.parameters:
            for param in metadata.parameters:
                param_type = self._format_parameter_type(param)
                param_desc = self._generate_parameter_description(param)

                lines.append(f":param {param.name}: {param_desc}")
                lines.append(f":type {param.name}: {param_type}")

            if metadata.parameters:
                lines.append("")

        # Returns
        if self._should_include_returns(metadata):
            return_type = metadata.return_type or "Any"
            lines.append(":return: Return value description.")
            lines.append(f":rtype: {return_type}")
            lines.append("")

        # Yields (for generators)
        if self._should_include_yields(metadata):
            yield_type = metadata.return_type or "Any"
            lines.append(":yields: Yielded value description.")
            lines.append(f":ytype: {yield_type}")
            lines.append("")

        # Raises
        if metadata.raises:
            for exc in metadata.raises:
                lines.append(f":raises {exc}: Description of when this is raised.")
            lines.append("")

        # Remove trailing blank line
        while lines and not lines[-1].strip():
            lines.pop()

        # Close docstring
        lines.append('"""')

        return "\n".join(lines)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate reST-style class docstring.

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

        # Attributes
        if metadata.attributes:
            for attr in metadata.attributes:
                attr_name = attr["name"]
                attr_type = attr.get("type", "Any")
                lines.append(f":ivar {attr_name}: {attr_name} attribute.")
                lines.append(f":vartype {attr_name}: {attr_type}")
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
