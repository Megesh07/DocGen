"""Epytext-style docstring template (Epydoc format).

Epytext is the markup language used by Epydoc, one of the earliest Python
documentation generators. Still used in many legacy codebases.
"""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.models.metadata import FunctionMetadata, ClassMetadata


class EpytextTemplate(BaseTemplate):
    """Epytext-style docstring generator.

    Generates docstrings following the Epydoc / Epytext markup format.
    See: http://epydoc.sourceforge.net/epytext.html
    """

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate Epytext-style function docstring.

        Args:
            metadata: Function metadata.

        Returns:
            Generated docstring text.
        """
        lines = []

        # Summary line
        summary = self._generate_summary(metadata)
        lines.append(f'"""{summary}')

        has_body = bool(
            metadata.parameters
            or self._should_include_returns(metadata)
            or metadata.raises
        )

        if has_body:
            lines.append("")

        # @param directives
        for param in metadata.parameters:
            desc = self._generate_parameter_description(param)
            if param.default_value:
                desc += f" Defaults to {param.default_value}."
            if param.type_hint:
                lines.append(f"@type  {param.name}: {param.type_hint}")
            lines.append(f"@param {param.name}: {desc}")

        # @return / @rtype
        if self._should_include_returns(metadata):
            if metadata.return_type:
                lines.append(f"@rtype:  {metadata.return_type}")
            lines.append("@return: Return value description.")

        # Yields (non-standard in epytext, use note)
        if self._should_include_yields(metadata):
            lines.append("@note:   This is a generator function.")

        # @raise directives
        for exc in metadata.raises:
            lines.append(f"@raise {exc}: Description of when this is raised.")

        # Close docstring
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append('"""')

        return "\n".join(lines)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate Epytext-style class docstring.

        Args:
            metadata: Class metadata.

        Returns:
            Generated docstring text.
        """
        lines = []
        summary = f"{metadata.name} class."
        if metadata.is_dataclass:
            summary = f"{metadata.name} dataclass."
        lines.append(f'"""{summary}')

        if metadata.attributes:
            lines.append("")
            for attr in metadata.attributes:
                attr_name = attr["name"]
                attr_type = attr.get("type", "Any")
                lines.append(f"@ivar  {attr_name}: {attr_type} attribute.")

        while lines and not lines[-1].strip():
            lines.pop()
        lines.append('"""')

        return "\n".join(lines)

    def _generate_summary(self, metadata: FunctionMetadata) -> str:
        name = metadata.name.replace("_", " ").title()
        if metadata.node_type.value in ["method", "async_method"]:
            return f"{name} method."
        elif metadata.node_type.value == "property":
            return f"{name} property."
        else:
            return f"{name} function."
