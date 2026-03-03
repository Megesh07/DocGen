"""Docstring style and completeness verification.

Style-aware docstring checking is the back-bone of the entire "skip vs
regenerate" decision.  Every rule here flows through ``_docstring_status``
in ``api/app.py`` and through ``HybridDocstringEngine.generate`` in
``generator/engine.py``.

Design contract
---------------
``is_style_match(docstring, style, metadata)``
    Returns True **only** when the docstring actively follows the named
    style's section markup — OR when the function has no documentable
    elements (no non-self params, no non-None return, no raises), in which
    case a plain summary sentence is valid in every style.

``is_complete(docstring, metadata)``
    Returns True when every non-self/cls parameter is mentioned *and*
    (if the function annotates a non-None return) a Returns / Yields
    section marker is present.

Combining both::

    fully_ok = is_style_match(doc, style, meta) and is_complete(doc, meta)

A function is considered "already documented" only when ``fully_ok`` is
True; otherwise a new docstring is generated.

Edge cases handled
------------------
* One-liner on no-param/no-return function  → valid in any style (no false regen)
* Correct-style Args but missing Returns    → incomplete
* NumPy headers when Google was requested    → style mismatch → regen
* Completely empty / whitespace-only         → always False
* ``*args`` / ``**kwargs`` parameters        → considered documentable
* Return type of ``None`` or ``NoReturn``    → not counted as needing Returns
"""

import re
from typing import List, Optional

from autodocstring.models.metadata import FunctionMetadata

# ---------------------------------------------------------------------------
# Compiled patterns for "Returns" section detection (all styles)
# ---------------------------------------------------------------------------

# Matches a Returns/Yields section header in any supported style:
#   Google   → "Returns:" or "Yields:"
#   NumPy    → "Returns\n---..."  or "Yields\n---..."
#   reST     → ":returns:" / ":return:" / ":rtype:"
#   Sphinx   → same as reST
#   Epytext  → "@return" / "@returns" / "@rtype"
_RETURNS_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:"
    r"returns?\s*:"                    # Google Returns: / Return:
    r"|yields?\s*:"                    # Google Yields:
    r"|returns?\s*\n\s*-+"            # NumPy Returns\n-------
    r"|yields?\s*\n\s*-+"             # NumPy Yields\n-------
    r"|:returns?:"                     # reST/Sphinx :returns: / :return:
    r"|:rtype:"                        # reST/Sphinx :rtype:
    r"|@returns?\b"                    # Epytext @return / @returns
    r"|@rtype\b"                       # Epytext @rtype
    r")",
    re.IGNORECASE | re.MULTILINE,
)

# Return types that do NOT need a Returns section
_VOID_RETURN_TYPES = frozenset({"None", "NoReturn", "typing.NoReturn", "None | None"})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _has_documentable_elements(metadata: FunctionMetadata) -> bool:
    """Return True if the function has any elements that require style sections.

    A function needs structured sections when it has:
    * one or more non-self/cls parameters (including *args / **kwargs), OR
    * a non-void return type annotation, OR
    * one or more documented raises declarations.

    Args:
        metadata: Extracted function metadata.

    Returns:
        True if the function needs Args/Returns/Raises sections.
    """
    has_params = any(p.name not in ("self", "cls") for p in metadata.parameters)
    return_type = metadata.return_type or ""
    has_return = bool(
        return_type
        and return_type.strip() not in _VOID_RETURN_TYPES
        and not return_type.strip().startswith("None")
    )
    has_raises = bool(metadata.raises)
    return has_params or has_return or has_raises


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_style_match(
    docstring: str,
    requested_style: str,
    metadata: Optional[FunctionMetadata] = None,
) -> bool:
    """Check whether an existing docstring follows the requested style conventions.

    When ``metadata`` is provided the function first checks whether the
    function actually needs any style-specific sections (params / returns /
    raises).  If not — e.g. a zero-argument function with no return
    annotation — any non-trivial summary sentence is considered valid for
    every style, preventing needless regeneration.

    Args:
        docstring: The existing docstring text (raw, without triple-quotes).
        requested_style: One of ``google``, ``numpy``, ``rest``, ``sphinx``,
            ``epytext``.
        metadata: Optional function metadata used for the no-section shortcut.

    Returns:
        True if the docstring matches the requested style (or needs no
        style-specific sections and has a non-empty summary).
    """
    if not docstring or not docstring.strip():
        return False

    # ── Shortcut: function has nothing that needs structured sections ────────
    # A one-liner "Run the process." is valid in every style when the function
    # has no params, no non-None return, and no raises.
    if metadata is not None and not _has_documentable_elements(metadata):
        # Accept any non-trivial summary (≥ 4 meaningful chars, not just quotes)
        cleaned = docstring.strip().strip('"""').strip("'''").strip()
        return len(cleaned) >= 4

    # ── Style-specific section header detection ──────────────────────────────
    # Normalise to lower-case for case-insensitive matching.
    lines = [line.strip() for line in docstring.split("\n")]
    full_text = "\n".join(lines).lower()

    if requested_style == "google":
        # Google headers: "Args:", "Returns:", "Raises:", "Yields:", "Attributes:"
        return bool(
            re.search(
                r"(?:^|\n)\s*(args|arguments|returns?|raises?|yields?|attributes?|note|example)\s*:",
                full_text,
            )
        )

    elif requested_style == "numpy":
        # NumPy headers are always followed by a dashed underline
        return bool(
            re.search(
                r"(?:^|\n)\s*(parameters?|returns?|raises?|yields?|attributes?|notes?|examples?)\s*\n\s*-+\s*",
                full_text,
            )
        )

    elif requested_style in ("rest", "sphinx"):
        # reST / Sphinx field lists: :param ...:, :type ...:, :returns:, :rtype:
        return bool(
            re.search(r"(?:^|\n)\s*:(param|type|returns?|rtype|raises?|var|ivar|cvar)\b", full_text)
        )

    elif requested_style == "epytext":
        # Epytext fields: @param, @type, @return, @rtype, @raise
        return bool(
            re.search(r"(?:^|\n)\s*@(param|type|returns?|rtype|raises?|keyword)\b", full_text)
        )

    # Unknown style — do not assume a match, trigger regeneration
    return False


def is_complete(docstring: str, metadata: FunctionMetadata) -> bool:
    """Check whether an existing docstring documents all required elements.

    Completeness requires:
    1. Every non-self/cls parameter (by name) is mentioned in the docstring.
    2. If the function has a non-void return type annotation, a Returns /
       Yields section marker must be present (any style).

    A completely empty or whitespace-only docstring always returns False.

    Args:
        docstring: The existing docstring text.
        metadata: The function metadata containing parameters and return type.

    Returns:
        True when both parameter coverage and (if applicable) returns
        documentation requirements are satisfied.
    """
    if not docstring or not docstring.strip():
        return False

    docstring_lower = docstring.lower()

    # ── 1. Parameter coverage ────────────────────────────────────────────────
    required_params = [
        p.name for p in metadata.parameters if p.name not in ("self", "cls")
    ]
    for param_name in required_params:
        # Match the parameter name as a whole word (handles param_name:, @param
        # param_name, *param_name in *args, etc.)
        pattern = rf"\b{re.escape(param_name)}\b"
        if not re.search(pattern, docstring_lower):
            return False

    # ── 2. Returns section requirement ──────────────────────────────────────
    return_type = (metadata.return_type or "").strip()
    if (
        return_type
        and return_type not in _VOID_RETURN_TYPES
        and not return_type.startswith("None")
    ):
        if not _RETURNS_SECTION_RE.search(docstring):
            return False

    return True
