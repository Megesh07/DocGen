"""Sphinx-style docstring template.

Sphinx is the most widely used Python documentation generator.
The Sphinx style is an extension of reST that is preferred for
projects hosted on Read the Docs and for many major open-source projects.
"""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.models.metadata import FunctionMetadata, ClassMetadata


class SphinxTemplate(BaseTemplate):
    """Sphinx-style docstring generator.

    Generates docstrings in Sphinx (autodoc) format using
    :param:, :type:, :returns:, :rtype:, :raises: directives.
    See: https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html
    """

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate Sphinx-style function docstring.

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

        # :param name: and :type name: directives (interleaved)
        for param in metadata.parameters:
            desc = self._generate_parameter_description(param)
            if param.default_value:
                desc += f" Defaults to {param.default_value}."
            lines.append(f":param {param.name}: {desc}")
            if param.type_hint:
                lines.append(f":type  {param.name}: {param.type_hint}")

        # :returns: / :rtype:
        if self._should_include_returns(metadata):
            lines.append(":returns: Return value description.")
            if metadata.return_type:
                lines.append(f":rtype:   {metadata.return_type}")

        # Yields
        if self._should_include_yields(metadata):
            lines.append(":yields: Generated value description.")

        # :raises ExcType: description
        for exc in metadata.raises:
            lines.append(f":raises {exc}: Description of when this is raised.")

        while lines and not lines[-1].strip():
            lines.pop()
        lines.append('"""')

        return "\n".join(lines)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate Sphinx-style class docstring.

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
                lines.append(f":ivar  {attr_name}: {attr_type} attribute.")
                lines.append(f":vartype {attr_name}: {attr_type}")

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
