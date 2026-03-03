"""Docstring generation engine.

Two generation modes are provided:

1. ``DocstringGenerator`` – the original deterministic engine that renders
   docstrings using style-specific Jinja templates.  Unchanged from the
   original codebase.

2. ``HybridDocstringEngine`` – the new production engine that:
   * Scores confidence for every function via ``ConfidenceScorer``
   * Delegates template rendering to the deterministic layer
   * Optionally refines only the *summary sentence* via an LLM provider
   * Returns structured ``DocstringResult`` objects instead of raw strings
"""
from typing import Optional, Literal, List

from autodocstring.models.metadata import FunctionMetadata, ClassMetadata, ModuleMetadata
from autodocstring.generator.templates import (
    BaseTemplate,
    GoogleTemplate,
    NumpyTemplate,
    RestTemplate,
)

from autodocstring.generator.templates.epytext import EpytextTemplate
from autodocstring.generator.templates.sphinx import SphinxTemplate

DocstringStyle = Literal["google", "numpy", "rest", "epytext", "sphinx"]


class DocstringGenerator:
    """Main docstring generation engine.

    Orchestrates docstring generation using style-specific templates.

    Attributes:
        style: Docstring style to use (google, numpy, or rest).
        template: Template instance for the selected style.
    """

    def __init__(self, style: DocstringStyle = "google"):
        """Initialize generator with a specific style.

        Args:
            style: Docstring style (google, numpy, or rest). Defaults to google.

        Raises:
            ValueError: If style is not supported.
        """
        self.style = style
        self.template = self._get_template(style)

    def _get_template(self, style: DocstringStyle) -> BaseTemplate:
        """Get template instance for the specified style.

        Args:
            style: Docstring style.

        Returns:
            Template instance.

        Raises:
            ValueError: If style is not supported.
        """
        templates = {
            "google": GoogleTemplate(),
            "numpy": NumpyTemplate(),
            "rest": RestTemplate(),
            "epytext": EpytextTemplate(),
            "sphinx": SphinxTemplate(),
        }

        if style not in templates:
            raise ValueError(
                f"Unsupported style: {style}. Choose from: {list(templates.keys())}"
            )

        return templates[style]

    def generate_function_docstring(self, metadata: FunctionMetadata) -> str:
        """Generate docstring for a function.

        Args:
            metadata: Function metadata.

        Returns:
            Generated docstring text.
        """
        return self.template.generate_function_docstring(metadata)

    def generate_class_docstring(self, metadata: ClassMetadata) -> str:
        """Generate docstring for a class.

        Args:
            metadata: Class metadata.

        Returns:
            Generated docstring text.
        """
        return self.template.generate_class_docstring(metadata)

    def generate_module_docstring(self, metadata: ModuleMetadata) -> str:
        """Generate docstring for a module.

        Args:
            metadata: Module metadata.

        Returns:
            Generated module docstring.
        """
        if metadata.docstring:
            return metadata.docstring

        # Generate basic module docstring
        module_name = metadata.module_name.replace("_", " ").title()
        return f'"""{module_name} module."""'

    def should_update_docstring(
        self, existing: Optional[str], metadata: FunctionMetadata
    ) -> bool:
        """Determine if an existing docstring should be updated.

        Args:
            existing: Existing docstring text.
            metadata: Function metadata.

        Returns:
            True if docstring should be updated.
        """
        # Don't update if there's a substantial existing docstring
        if existing and len(existing.strip()) > 50:
            # Check if it has proper sections
            if any(
                keyword in existing
                for keyword in ["Args:", "Parameters", ":param", "Returns:", "Raises:"]
            ):
                return False

        # Update if missing or minimal
        return True

    def update_existing_docstring(
        self, existing: str, metadata: FunctionMetadata
    ) -> str:
        """Update an existing docstring with missing sections.

        Args:
            existing: Existing docstring text.
            metadata: Function metadata.

        Returns:
            Updated docstring text.
        """
        # For now, if we decide to update, we regenerate completely
        # In a more sophisticated version, we could parse and merge sections
        return self.generate_function_docstring(metadata)

    def generate_for_module(self, metadata: ModuleMetadata) -> dict:
        """Generate docstrings for all items in a module.

        Args:
            metadata: Module metadata.

        Returns:
            Dictionary mapping (type, name, lineno) to generated docstring.
        """
        docstrings = {}

        # Module docstring
        if not metadata.docstring:
            docstrings[("module", metadata.module_name, 1)] = (
                self.generate_module_docstring(metadata)
            )

        # Class docstrings
        for cls in metadata.classes:
            if not cls.docstring or self.should_update_docstring(
                cls.docstring, None
            ):
                key = ("class", cls.name, cls.lineno)
                docstrings[key] = self.generate_class_docstring(cls)

            # Method docstrings
            for method in cls.methods:
                if not method.docstring or self.should_update_docstring(
                    method.docstring, method
                ):
                    key = ("method", f"{cls.name}.{method.name}", method.lineno)
                    docstrings[key] = self.generate_function_docstring(method)

        # Function docstrings
        for func in metadata.functions:
            if not func.docstring or self.should_update_docstring(
                func.docstring, func
            ):
                key = ("function", func.name, func.lineno)
                docstrings[key] = self.generate_function_docstring(func)

        return docstrings


# ---------------------------------------------------------------------------
# HybridDocstringEngine – two-layer generation (deterministic + optional LLM)
# ---------------------------------------------------------------------------

_IGNORE_DIRECTIVE = "# autodoc: ignore"


class HybridDocstringEngine:
    """Production docstring engine combining deterministic and LLM layers.

    Generation pipeline per function:
    1. Check for ``# autodoc: ignore`` directive → skip
    2. Check if docstring already present and ``rewrite_existing=False`` → skip
    3. Call ``ConfidenceScorer`` → determine risk
    4. If confidence below threshold → skip with reason
    5. Render full docstring via deterministic ``DocstringGenerator``
    6. Optionally refine *summary sentence only* via LLM provider
    7. Return ``DocstringResult``

    Attributes:
        style: Docstring style (google, numpy, rest).
        provider: Optional LLM provider for summary refinement.
        confidence_threshold: Minimum confidence to generate a docstring.
        rewrite_existing: Whether to overwrite existing docstrings.
    """

    def __init__(
        self,
        style: DocstringStyle = "google",
        provider: Optional[object] = None,
        confidence_threshold: float = 0.60,
        rewrite_existing: bool = False,
        session_id: Optional[str] = None,
    ):
        """Initialize the hybrid engine.

        Args:
            style: Docstring style. Defaults to ``google``.
            provider: Optional LLM provider instance. Defaults to None.
            confidence_threshold: Minimum confidence score to generate.
                Defaults to 0.60.
            rewrite_existing: If True, overwrite existing docstrings.
                Defaults to False.
        """
        from autodocstring.confidence.scorer import ConfidenceScorer, AUTO_APPLY
        from autodocstring.models.metadata import DocstringResult, RiskLevel

        self.style = style
        self.provider = provider
        self.confidence_threshold = confidence_threshold
        self.rewrite_existing = rewrite_existing
        self.session_id = session_id
        
        self._cache = {}
        if self.session_id:
            from pathlib import Path
            import json
            cache_path = Path(".autodocstring_sessions") / self.session_id / "generation_cache.json"
            if cache_path.exists():
                try:
                    self._cache = json.loads(cache_path.read_text("utf-8"))
                except Exception:
                    pass

        self._generator = DocstringGenerator(style=style)
        self._scorer = ConfidenceScorer()
        self._AUTO_APPLY = 0.4  # Lowered to ensure AI summaries are more frequent
        self._DocstringResult = DocstringResult
        self._RiskLevel = RiskLevel

    def generate(
        self,
        metadata: FunctionMetadata,
        filepath: str = "",
        source_lines: Optional[List[str]] = None,
    ) -> "DocstringResult":
        """Generate a docstring result for a single function.

        Args:
            metadata: Extracted function metadata.
            filepath: Absolute path to the source file.
            source_lines: Source code lines (used for ignore directive check).

        Returns:
            DocstringResult with docstring, confidence, risk, and reason, and generation_type.
        """
        from autodocstring.models.metadata import DocstringResult, RiskLevel

        func_name = (
            f"{metadata.parent_class}.{metadata.name}"
            if metadata.parent_class
            else metadata.name
        )

        # --- Check ignore directive ---
        if source_lines and _has_ignore_directive(source_lines, metadata.lineno):
            return DocstringResult(
                file=filepath,
                function=func_name,
                lineno=metadata.lineno,
                skipped=True,
                skip_reason="autodoc: ignore directive present",
                generation_type="skipped",
            )

        # --- Deterministic Cache ---
        cache_key = None
        if source_lines:
            import hashlib
            body_lines = source_lines[metadata.lineno - 1:metadata.end_lineno]
            body_text = "\n".join(body_lines)
            if metadata.docstring:
                body_text = body_text.replace(metadata.docstring, "")
            signature = f"{func_name}({','.join(p.name for p in metadata.parameters)}) -> {metadata.return_type}"
            raw_key = f"{filepath}::{func_name}::{metadata.lineno}::{signature}::{body_text}"
            cache_key = hashlib.md5(raw_key.encode("utf-8")).hexdigest()
            
            if cache_key in self._cache:
                return DocstringResult(**self._cache[cache_key])
                
        # --- Confidence scoring ---
        scoring = self._scorer.score(metadata)

        # --- Check existing docstring ---
        if metadata.docstring:
            if not self.rewrite_existing:
                from autodocstring.validation.style_checker import is_style_match, is_complete
                
                # Pass metadata so is_style_match can apply the no-section shortcut
                # (one-liner on no-param/no-return function is valid in every style).
                if is_style_match(metadata.docstring, self.style, metadata=metadata) and is_complete(metadata.docstring, metadata):
                    return DocstringResult(
                        file=filepath,
                        function=func_name,
                        lineno=metadata.lineno,
                        docstring=metadata.docstring,
                        confidence=scoring.confidence,
                        risk=scoring.risk,
                        reason="existing docstring matches style and is complete",
                        skipped=False,
                        generation_type="existing",
                    )

        if scoring.confidence < self.confidence_threshold:
            return DocstringResult(
                file=filepath,
                function=func_name,
                lineno=metadata.lineno,
                confidence=scoring.confidence,
                risk=scoring.risk,
                reason=scoring.reason,
                skipped=True,
                skip_reason=(
                    f"confidence {scoring.confidence:.2f} below threshold "
                    f"{self.confidence_threshold:.2f}: {scoring.reason}"
                ),
                generation_type="skipped",
            )

        # --- Deterministic layer ---
        base_docstring = self._generator.generate_function_docstring(metadata)

        # --- Enhancement layer (LLM summary only) ---
        final_docstring, used_llm = self._maybe_enhance_summary(base_docstring, metadata, scoring)
        
        gen_type = "hybrid" if used_llm else "template"

        res = DocstringResult(
            file=filepath,
            function=func_name,
            lineno=metadata.lineno,
            docstring=final_docstring,
            confidence=scoring.confidence,
            risk=scoring.risk,
            reason=scoring.reason,
            generation_type=gen_type,
        )
        if cache_key and not res.skipped:
            self._cache[cache_key] = res.to_dict() if hasattr(res, "to_dict") else res.model_dump()
            if self.session_id:
                from pathlib import Path
                import json
                cache_path = Path(".autodocstring_sessions") / self.session_id / "generation_cache.json"
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(self._cache, indent=2), "utf-8")
        return res

    def generate_for_module(
        self,
        module_metadata,
        filepath: str = "",
        source_lines: Optional[List[str]] = None,
    ) -> List["DocstringResult"]:
        """Generate docstring results for all functions in a module.

        Args:
            module_metadata: Parsed ModuleMetadata object.
            filepath: Absolute path to the source file.
            source_lines: Source code lines for ignore directive checks.

        Returns:
            List of DocstringResult for every function and method found.
        """
        results: List = []

        # Module-level functions
        for func in module_metadata.functions:
            result = self.generate(func, filepath=filepath, source_lines=source_lines)
            results.append(result)

        # Class methods
        for cls in module_metadata.classes:
            for method in cls.methods:
                result = self.generate(
                    method, filepath=filepath, source_lines=source_lines
                )
                results.append(result)

        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _maybe_enhance_summary(
        self,
        base_docstring: str,
        metadata: FunctionMetadata,
        scoring,
    ) -> tuple[str, bool]:
        """Replace only the summary block via LLM using structured extraction.

        Args:
            base_docstring: Deterministically generated docstring.
            metadata: Function metadata.
            scoring: ScoringResult from confidence scorer.

        Returns:
            Tuple of (Docstring text, whether LLM was successfully used).
        """
        if self.provider is None or scoring.confidence < self._AUTO_APPLY:
            return base_docstring, False

        metadata_dict = {
            "name": metadata.name,
            "params": [
                f"{p.name}: {p.type_hint or 'Any'}" for p in metadata.parameters
            ],
            "return_type": metadata.return_type or "None",
            "raises": metadata.raises,
        }

        try:
            new_summary = self.provider.generate_summary(metadata_dict)
        except Exception:
            new_summary = None

        if not new_summary or not new_summary.strip():
            return base_docstring, False

        # Structured replacement: 
        # Identify the end of the summary paragraph by scanning for section headers or empty lines.
        lines = base_docstring.split("\n")
        
        # Strip opening quotes if present on first line
        if lines and lines[0].strip().startswith('"""'):
            lines[0] = lines[0].replace('"""', '', 1)
            
        summary_end_idx = len(lines)
        section_headers = {"Args:", "Returns:", "Raises:", "Yields:", "Attributes:", "Parameters:", "Examples:"}
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Stop summary block reading when we hit an empty line or a section header
            if not stripped and i > 0:
                summary_end_idx = i
                break
            if stripped in section_headers:
                summary_end_idx = i
                break
                
        # Strip closing quotes from the last line to cleanly reconstruct
        if lines and lines[-1].strip().endswith('"""'):
            lines[-1] = lines[-1].replace('"""', '')
            
        remaining_lines = lines[summary_end_idx:]
        
        # Cleanly attach new summary
        new_summary_text = new_summary.strip().rstrip(".") + "."
        
        new_doc = [f'"""{new_summary_text}']
        
        # Ensure proper spacing before structural sections
        if remaining_lines:
            if remaining_lines[0].strip() != "":
                new_doc.append("")
            new_doc.extend(remaining_lines)
            
        # Add back closing quotes 
        # If the last remaining line is empty, put quotes on that line, otherwise new line
        while new_doc and not new_doc[-1].strip() and new_doc[-1] != '"""':
            new_doc.pop()
        new_doc.append('"""')
        
        return "\n".join(new_doc), True


def _has_ignore_directive(source_lines: List[str], lineno: int) -> bool:
    """Check if the line before ``lineno`` contains an autodoc ignore directive.

    Args:
        source_lines: All source lines (0-indexed list).
        lineno: 1-based line number of the function definition.

    Returns:
        True if the preceding line contains ``# autodoc: ignore``.
    """
    preceding_idx = lineno - 2  # lineno is 1-based; preceding line is idx-1
    if preceding_idx < 0 or preceding_idx >= len(source_lines):
        return False
    return _IGNORE_DIRECTIVE in source_lines[preceding_idx]
