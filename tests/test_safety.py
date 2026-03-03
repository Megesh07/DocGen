"""Tests for SafeApplier – idempotency, syntax rollback, and ignore directives."""
import ast
import textwrap
import tempfile
from pathlib import Path

import pytest

from autodocstring.safety.applier import SafeApplier, ApplyResult
from autodocstring.models.metadata import DocstringResult, RiskLevel


def _write_temp(content: str) -> str:
    """Write content to a temporary .py file and return path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
        return f.name


def _make_result(filepath: str, func_name: str, lineno: int, docstring: str) -> DocstringResult:
    return DocstringResult(
        file=filepath,
        function=func_name,
        lineno=lineno,
        docstring=docstring,
        confidence=0.9,
        risk=RiskLevel.LOW,
        reason="test",
    )


class TestSafeApplierIdempotency:
    """SafeApplier must produce identical files on repeated runs."""

    def test_apply_twice_no_change(self):
        """Applying the same docstring twice should not modify the file."""
        code = """\
            def add(a: int, b: int) -> int:
                return a + b
        """
        path = _write_temp(code)
        result = _make_result(path, "add", 1, "Add two integers and return their sum.")

        applier = SafeApplier(dry_run=False)
        applier.apply_to_file(path, [result])
        content_after_first = Path(path).read_text(encoding="utf-8")

        applier.apply_to_file(path, [result])
        content_after_second = Path(path).read_text(encoding="utf-8")

        assert content_after_first == content_after_second, "File changed on second apply (not idempotent)"

    def test_dry_run_does_not_modify_file(self):
        """dry_run=True must never write to disk."""
        code = """\
            def multiply(x: int, y: int) -> int:
                return x * y
        """
        path = _write_temp(code)
        original = Path(path).read_text(encoding="utf-8")
        result = _make_result(path, "multiply", 1, "Multiply x and y.")

        applier = SafeApplier(dry_run=True)
        ar = applier.apply_to_file(path, [result])

        assert Path(path).read_text(encoding="utf-8") == original
        # Diff should be non-empty (something would change)
        assert ar.diff  # There IS a diff

    def test_returns_diff_in_dry_run(self):
        """Dry-run must produce a unified diff string."""
        code = """\
            def subtract(a: int, b: int) -> int:
                return a - b
        """
        path = _write_temp(code)
        result = _make_result(path, "subtract", 1, "Subtract b from a.")

        applier = SafeApplier(dry_run=True)
        ar = applier.apply_to_file(path, [result])

        assert "---" in ar.diff or "+++" in ar.diff


class TestSafeApplierSyntaxRollback:
    """A corrupted file must be rolled back, not written."""

    def test_syntax_error_triggers_rollback(self, monkeypatch):
        """If the generated docstring produces invalid Python, file is not touched."""
        code = """\
            def greet(name: str) -> str:
                return f"Hello, {name}"
        """
        path = _write_temp(code)
        original = Path(path).read_text(encoding="utf-8")

        # Monkey-patch ast.parse to raise SyntaxError after writing
        import autodocstring.safety.applier as applier_module
        real_parse = ast.parse
        call_count = [0]

        def fake_parse(source, **kwargs):
            call_count[0] += 1
            if call_count[0] >= 2:  # second call = after write
                raise SyntaxError("Injected syntax error")
            return real_parse(source, **kwargs)

        monkeypatch.setattr(applier_module.ast, "parse", fake_parse)

        result = _make_result(path, "greet", 1, "Greet the user by name.")
        applier = SafeApplier(dry_run=False)
        ar = applier.apply_to_file(path, [result])

        assert ar.rolled_back, "Should have been rolled back"
        assert Path(path).read_text(encoding="utf-8") == original, "File should be unchanged"


class TestSafeApplierSkipEmpty:
    """Skipped results should not be applied."""

    def test_skipped_results_are_not_written(self):
        """Results with skipped=True must be excluded from file writes."""
        code = """\
            def noop():
                pass
        """
        path = _write_temp(code)
        original = Path(path).read_text(encoding="utf-8")

        skipped = DocstringResult(
            file=path,
            function="noop",
            lineno=1,
            docstring="This would be written if not skipped.",
            confidence=0.9,
            risk=RiskLevel.LOW,
            reason="test",
            skipped=True,
            skip_reason="autodoc: ignore directive present",
        )

        applier = SafeApplier(dry_run=False)
        ar = applier.apply_to_file(path, [skipped])

        assert Path(path).read_text(encoding="utf-8") == original
        assert ar.applied == 0
