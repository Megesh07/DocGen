"""Validation rules for docstrings."""
from typing import List, Tuple
from enum import Enum


class Severity(Enum):
    """Severity levels for validation issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRule:
    """Base class for validation rules.

    Attributes:
        code: Rule code (e.g., D100, D101).
        message: Rule description.
        severity: Issue severity level.
    """

    def __init__(self, code: str, message: str, severity: Severity = Severity.ERROR):
        """Initialize validation rule.

        Args:
            code: Rule code.
            message: Rule description.
            severity: Issue severity. Defaults to ERROR.
        """
        self.code = code
        self.message = message
        self.severity = severity

    def check(self, docstring: str, context: dict) -> bool:
        """Check if rule is violated.

        Args:
            docstring: Docstring text to check.
            context: Context information (function name, type, etc.).

        Returns:
            True if rule is violated.
        """
        raise NotImplementedError


class PEP257Rules:
    """PEP 257 docstring convention rules.

    See: https://peps.python.org/pep-0257/
    """

    @staticmethod
    def missing_docstring(docstring: str, context: dict) -> bool:
        """Check if docstring is missing.

        Args:
            docstring: Docstring text.
            context: Context information.

        Returns:
            True if docstring is missing.
        """
        return not docstring or not docstring.strip()

    @staticmethod
    def missing_period(docstring: str, context: dict) -> bool:
        """Check if one-line docstring is missing ending period.

        Args:
            docstring: Docstring text.
            context: Context information.

        Returns:
            True if period is missing.
        """
        if not docstring:
            return False

        lines = [line.strip() for line in docstring.strip().split("\n") if line.strip()]
        if len(lines) == 1:
            # One-line docstring should end with period
            return not lines[0].endswith(".")

        return False

    @staticmethod
    def blank_line_after_summary(docstring: str, context: dict) -> bool:
        """Check if multi-line docstring has blank line after summary.

        Args:
            docstring: Docstring text.
            context: Context information.

        Returns:
            True if blank line is missing.
        """
        if not docstring:
            return False

        lines = docstring.strip().split("\n")
        if len(lines) <= 2:
            return False

        # Second line should be blank in multi-line docstrings
        return lines[1].strip() != ""

    @staticmethod
    def triple_quotes(docstring: str, context: dict) -> bool:
        """Check if docstring uses triple double quotes.

        Args:
            docstring: Docstring text.
            context: Context information.

        Returns:
            True if not using triple double quotes.
        """
        # This is checked at the source level, not on extracted docstring
        return False

    @staticmethod
    def ends_with_period(docstring: str, context: dict) -> bool:
        """Check if summary line ends with period.

        Args:
            docstring: Docstring text.
            context: Context information.

        Returns:
            True if summary doesn't end with period.
        """
        if not docstring:
            return False

        lines = [line.strip() for line in docstring.strip().split("\n") if line.strip()]
        if lines:
            first_line = lines[0]
            return not first_line.endswith(".")

        return False


class AutofixRules:
    """Rules that can be automatically fixed."""

    @staticmethod
    def add_period(docstring: str) -> str:
        """Add period to end of summary line.

        Args:
            docstring: Original docstring.

        Returns:
            Fixed docstring.
        """
        if not docstring:
            return docstring

        lines = docstring.split("\n")
        if lines:
            first_line = lines[0].strip()
            if first_line and not first_line.endswith("."):
                lines[0] = first_line + "."

        return "\n".join(lines)

    @staticmethod
    def add_blank_line_after_summary(docstring: str) -> str:
        """Add blank line after summary in multi-line docstring.

        Args:
            docstring: Original docstring.

        Returns:
            Fixed docstring.
        """
        if not docstring:
            return docstring

        lines = docstring.split("\n")
        if len(lines) > 2 and lines[1].strip():
            # Insert blank line after first line
            lines.insert(1, "")

        return "\n".join(lines)

    @staticmethod
    def fix_spacing(docstring: str) -> str:
        """Fix spacing issues in docstring.

        Args:
            docstring: Original docstring.

        Returns:
            Fixed docstring.
        """
        if not docstring:
            return docstring

        # Remove trailing whitespace from each line
        lines = [line.rstrip() for line in docstring.split("\n")]

        # Remove excessive blank lines (max 1 consecutive)
        fixed_lines = []
        prev_blank = False
        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue
            fixed_lines.append(line)
            prev_blank = is_blank

        return "\n".join(fixed_lines)


# Define standard PEP 257 rules
STANDARD_RULES = [
    ValidationRule("D100", "Missing docstring in public module", Severity.ERROR),
    ValidationRule("D101", "Missing docstring in public class", Severity.ERROR),
    ValidationRule("D102", "Missing docstring in public method", Severity.ERROR),
    ValidationRule("D103", "Missing docstring in public function", Severity.ERROR),
    ValidationRule("D200", "One-line docstring should fit on one line", Severity.WARNING),
    ValidationRule("D201", "No blank lines allowed before docstring", Severity.WARNING),
    ValidationRule("D202", "No blank lines allowed after docstring", Severity.WARNING),
    ValidationRule("D205", "1 blank line required between summary and description", Severity.WARNING),
    ValidationRule("D400", "First line should end with a period", Severity.WARNING),
    ValidationRule("D401", "First line should be in imperative mood", Severity.INFO),
]
