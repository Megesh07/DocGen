"""Google-style docstring template."""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.models.metadata import FunctionMetadata, ClassMetadata


class GoogleTemplate(BaseTemplate):
    """Google-style docstring generator.

    Generates docstrings following the Google Python Style Guide.
    See: https://google.github.io/styleguide/pyguide.html
    """

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate Google-style function docstring.

        Args:
            metadata: Function metadata.

        Returns:
            Generated docstring text.
        """
        lines = []

        # Summary line
        summary = self._generate_summary(metadata)
        lines.append(f'"""{summary}')

        # Add blank line if there are additional sections
        if metadata.parameters or self._should_include_returns(metadata) or metadata.raises:
            lines.append("")

        # Args section
        if metadata.parameters:
            lines.append("Args:")
            for param in metadata.parameters:
                param_desc = self._generate_parameter_description(param)
                param_line = f"    {param.name}: {param_desc}"
                if param.default_value:
                    param_line += f" Defaults to {param.default_value}."
                lines.append(param_line)
            lines.append("")

        # Returns section
        if self._should_include_returns(metadata):
            lines.append("Returns:")
            return_desc = self._generate_return_description(metadata)
            lines.append(f"    {return_desc}")
            lines.append("")

        # Yields section (for generators)
        if self._should_include_yields(metadata):
            lines.append("Yields:")
            yield_desc = self._generate_yield_description(metadata)
            lines.append(f"    {yield_desc}")
            lines.append("")

        # Raises section
        if metadata.raises:
            lines.append("Raises:")
            for exc in metadata.raises:
                lines.append(f"    {exc}: Description of when this is raised.")
            lines.append("")

        # Remove trailing blank line
        while lines and not lines[-1].strip():
            lines.pop()

        # Close docstring
        lines.append('"""')

        return "\n".join(lines)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate Google-style class docstring.

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
        lines.append(f'"""{summary}')

        # Add blank line if there are additional sections
        if metadata.attributes or metadata.bases:
            lines.append("")

        # Attributes section
        if metadata.attributes:
            lines.append("Attributes:")
            for attr in metadata.attributes:
                attr_name = attr["name"]
                attr_type = attr.get("type", "Any")
                lines.append(f"    {attr_name}: {attr_type} attribute.")
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

    def _generate_return_description(self, metadata: FunctionMetadata) -> str:
        """Generate return value description.

        Args:
            metadata: Function metadata.

        Returns:
            Return description.
        """
        if metadata.return_type:
            return f"{metadata.return_type}: Return value description."
        return "Return value description."

    def _generate_yield_description(self, metadata: FunctionMetadata) -> str:
        """Generate yield value description.

        Args:
            metadata: Function metadata.

        Returns:
            Yield description.
        """
        if metadata.return_type:
            return f"{metadata.return_type}: Yielded value description."
        return "Yielded value description."
