"""Safe, idempotent applier for generated docstrings.

Safety guarantees
-----------------
1. **Idempotency** – if the existing docstring already matches the
   generated one, the file is not modified.
2. **Syntax safety** – after writing, the file is reparsed with
   ``ast.parse``.  On ``SyntaxError`` the original content is restored.
3. **Non-intrusive** – only docstring *statement* nodes are touched.
   Imports, spacing, comments, and formatting are left untouched.
4. **Failure transparency** – every skipped function is recorded in
   a ``SkipRecord`` with a reason.
"""
import ast
import difflib
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from autodocstring.models.metadata import DocstringResult


@dataclass
class SkipRecord:
    """Record of a skipped function during apply.

    Attributes:
        function: Fully qualified function name.
        lineno: Line number of the function.
        reason: Human-readable skip reason.
    """

    function: str
    lineno: int
    reason: str


@dataclass
class ApplyResult:
    """Result of applying docstrings to a single file.

    Attributes:
        filepath: Absolute path to the file.
        applied: Number of docstrings successfully written.
        skipped: Number of docstrings skipped.
        skip_records: Detail records for each skip.
        diff: Unified diff string (empty in non-dry-run mode).
        rolled_back: True if the file was rolled back due to syntax error.
    """

    filepath: str
    applied: int = 0
    skipped: int = 0
    skip_records: List[SkipRecord] = field(default_factory=list)
    diff: str = ""
    rolled_back: bool = False


class SafeApplier:
    """Applies generated docstrings to Python source files safely.

    Attributes:
        dry_run: If True, compute diffs but do not write files.
    """

    def __init__(self, dry_run: bool = False):
        """Initialize the safe applier.

        Args:
            dry_run: If True, return diffs without modifying files.
                Defaults to False.
        """
        self.dry_run = dry_run

    def apply_to_file(
        self,
        filepath: str,
        results: List[DocstringResult],
    ) -> ApplyResult:
        """Apply docstring results to a single Python source file.

        Args:
            filepath: Absolute path to the target file.
            results: List of DocstringResult objects for this file.

        Returns:
            ApplyResult summarising what was applied and what was skipped.
        """
        path = Path(filepath)
        if not path.exists():
            return ApplyResult(
                filepath=filepath,
                skip_records=[SkipRecord("(file)", 0, f"File not found: {filepath}")],
            )

        original_source = path.read_text(encoding="utf-8")
        apply_result = ApplyResult(filepath=filepath)

        # Filter out skipped results
        to_apply = [r for r in results if not r.skipped and r.docstring]

        if not to_apply:
            apply_result.skip_records = [
                SkipRecord(r.function, r.lineno, r.skip_reason or "skipped")
                for r in results
                if r.skipped
            ]
            apply_result.skipped = len(apply_result.skip_records)
            return apply_result

        # Apply docstrings to source
        new_source, applied, skip_records = _insert_docstrings(original_source, to_apply)

        apply_result.applied = applied
        apply_result.skip_records = skip_records + [
            SkipRecord(r.function, r.lineno, r.skip_reason or "skipped")
            for r in results
            if r.skipped
        ]
        apply_result.skipped = len(apply_result.skip_records)

        if new_source == original_source:
            return apply_result  # Nothing changed (idempotent)

        # Generate diff
        apply_result.diff = _unified_diff(original_source, new_source, filepath)

        if self.dry_run:
            return apply_result

        # Syntax check before writing
        try:
            ast.parse(new_source, filename=filepath)
        except SyntaxError as exc:
            apply_result.rolled_back = True
            apply_result.applied = 0
            apply_result.skip_records.append(
                SkipRecord("(file)", 0, f"Syntax error after generation – rolled back: {exc}")
            )
            return apply_result

        # Write atomically
        path.write_text(new_source, encoding="utf-8")
        return apply_result

    def diff(
        self,
        filepath: str,
        results: List[DocstringResult],
    ) -> str:
        """Return the unified diff that would result from applying results.

        Args:
            filepath: Absolute path to the target file.
            results: List of DocstringResult objects.

        Returns:
            Unified diff string.
        """
        original = SafeApplier(dry_run=True)
        result = original.apply_to_file(filepath, results)
        return result.diff


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _insert_docstrings(
    source: str,
    results: List[DocstringResult],
) -> tuple:
    """Insert docstrings into source using AST node positions.

    Modifies the source string by inserting or replacing docstrings at the
    correct indentation level, ordered in reverse line order to avoid offset
    drift.

    Args:
        source: Original Python source code.
        results: Results to apply (must not be skipped, must have docstrings).

    Returns:
        Tuple of (new_source, applied_count, skip_records).
    """
    lines = source.splitlines(keepends=True)
    applied = 0
    skip_records: List[SkipRecord] = []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return source, 0, [SkipRecord("(file)", 0, "Cannot parse source")]

    # Build map: lineno → result
    result_by_lineno = {r.lineno: r for r in results}

    # Collect all function/method nodes sorted in reverse order
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.lineno in result_by_lineno:
                nodes.append(node)

    # Process in reverse order to preserve line indices
    nodes.sort(key=lambda n: n.lineno, reverse=True)

    for node in nodes:
        result = result_by_lineno[node.lineno]
        # Find insert position: line after the def: line
        def_line_idx = _find_def_end(lines, node.lineno)
        if def_line_idx is None:
            skip_records.append(
                SkipRecord(result.function, result.lineno, "Could not find def end line")
            )
            continue

        # Determine indentation (body indent = def indent + 4)
        def_line = lines[node.lineno - 1]
        def_indent = len(def_line) - len(def_line.lstrip())
        body_indent = def_indent + 4

        # Check idempotency: if first statement is already the same docstring
        existing_docstring = ast.get_docstring(node)
        new_docstring_text = result.docstring.strip().strip('"""')
        if existing_docstring and existing_docstring.strip() == new_docstring_text.strip():
            skip_records.append(
                SkipRecord(result.function, result.lineno, "Docstring already identical (idempotent)")
            )
            continue

        # If there's an existing docstring node, replace it
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            # Remove existing docstring lines
            ds_node = node.body[0]
            start_idx = ds_node.lineno - 1
            end_idx = ds_node.end_lineno  # exclusive (0-based end + 1)
            del lines[start_idx:end_idx]
            insert_idx = start_idx
        else:
            insert_idx = def_line_idx

        # Format docstring
        formatted = _format_docstring(result.docstring, body_indent)
        lines.insert(insert_idx, formatted + "\n")
        applied += 1

    return "".join(lines), applied, skip_records


def _find_def_end(lines: List[str], lineno: int) -> Optional[int]:
    """Find the 0-based index of the line after the function def signature.

    Handles multi-line function signatures (arguments spread across lines).

    Args:
        lines: Source lines (with line endings).
        lineno: 1-based line number of the ``def`` statement.

    Returns:
        0-based index of the line immediately following the ``:`` that ends
        the def, or None if not found.
    """
    idx = lineno - 1  # 0-based
    paren_depth = 0

    while idx < len(lines):
        line = lines[idx]
        for char in line:
            if char == "(":
                paren_depth += 1
            elif char == ")":
                paren_depth -= 1
        if paren_depth <= 0 and line.rstrip().endswith(":"):
            return idx + 1
        idx += 1

    return None


def _format_docstring(docstring: str, indent: int) -> str:
    """Format a docstring text with proper indentation and triple quotes.

    Args:
        docstring: Raw docstring text (may or may not include triple quotes).
        indent: Number of spaces for indentation.

    Returns:
        Formatted docstring line(s) ready for insertion.
    """
    # Strip any existing triple quotes
    text = docstring.strip()
    if text.startswith('"""') and text.endswith('"""'):
        text = text[3:-3].strip()

    indent_str = " " * indent

    lines = text.split("\n")
    if len(lines) == 1 and len(text) < 80:
        # Single-line docstring
        return f'{indent_str}"""{text}"""'
    else:
        # Multi-line docstring
        formatted_lines = [f'{indent_str}"""']
        for line in lines:
            formatted_lines.append(indent_str + line if line.strip() else "")
        formatted_lines.append(f'{indent_str}"""')
        return "\n".join(formatted_lines)


def _unified_diff(original: str, new: str, filepath: str) -> str:
    """Generate a unified diff between two source strings.

    Args:
        original: Original file content.
        new: New file content.
        filepath: File path for diff header.

    Returns:
        Unified diff string.
    """
    original_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
    )
    return "".join(diff)
