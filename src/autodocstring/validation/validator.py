"""Docstring validator with PEP 257 and pydocstyle integration."""
from typing import List, Dict, Optional
import subprocess
import json
from pathlib import Path

from autodocstring.validation.rules import (
    PEP257Rules,
    AutofixRules,
    STANDARD_RULES,
    Severity,
)


class ValidationIssue:
    """Represents a validation issue.

    Attributes:
        code: Issue code (e.g., D100).
        message: Issue description.
        severity: Issue severity level.
        line: Line number where issue occurs.
        column: Column number where issue occurs.
        context: Additional context information.
    """

    def __init__(
        self,
        code: str,
        message: str,
        severity: Severity,
        line: int = 0,
        column: int = 0,
        context: Optional[dict] = None,
    ):
        """Initialize validation issue.

        Args:
            code: Issue code.
            message: Issue description.
            severity: Issue severity level.
            line: Line number. Defaults to 0.
            column: Column number. Defaults to 0.
            context: Additional context. Defaults to None.
        """
        self.code = code
        self.message = message
        self.severity = severity
        self.line = line
        self.column = column
        self.context = context or {}

    def __repr__(self) -> str:
        """String representation of issue.

        Returns:
            String representation.
        """
        return f"{self.code}:{self.line}:{self.column}: {self.message} [{self.severity.value}]"


class DocstringValidator:
    """Validator for docstring quality and compliance.

    Validates docstrings against PEP 257 and optionally pydocstyle.

    Attributes:
        autofix: Whether to automatically fix issues.
        use_pydocstyle: Whether to use pydocstyle for validation.
    """

    def __init__(self, autofix: bool = True, use_pydocstyle: bool = True):
        """Initialize validator.

        Args:
            autofix: Enable automatic fixing. Defaults to True.
            use_pydocstyle: Use pydocstyle for validation. Defaults to True.
        """
        self.autofix = autofix
        self.use_pydocstyle = use_pydocstyle
        self.rules = STANDARD_RULES

    def validate_docstring(
        self, docstring: str, context: dict
    ) -> List[ValidationIssue]:
        """Validate a single docstring.

        Args:
            docstring: Docstring text to validate.
            context: Context information (name, type, etc.).

        Returns:
            List of validation issues found.
        """
        issues = []

        # Check for missing docstring
        if PEP257Rules.missing_docstring(docstring, context):
            issues.append(
                ValidationIssue(
                    "D100",
                    f"Missing docstring for {context.get('type', 'item')}",
                    Severity.ERROR,
                    context=context,
                )
            )
            return issues

        # Check for missing period
        if PEP257Rules.missing_period(docstring, context):
            issues.append(
                ValidationIssue(
                    "D400",
                    "First line should end with a period",
                    Severity.WARNING,
                    context=context,
                )
            )

        # Check for blank line after summary
        if PEP257Rules.blank_line_after_summary(docstring, context):
            issues.append(
                ValidationIssue(
                    "D205",
                    "1 blank line required between summary and description",
                    Severity.WARNING,
                    context=context,
                )
            )

        return issues

    def validate_file(self, filepath: str) -> List[ValidationIssue]:
        """Validate all docstrings in a file.

        Args:
            filepath: Path to Python file.

        Returns:
            List of validation issues found.
        """
        issues = []

        # Use pydocstyle if available and enabled
        if self.use_pydocstyle:
            pydocstyle_issues = self._run_pydocstyle(filepath)
            issues.extend(pydocstyle_issues)

        return issues

    def _run_pydocstyle(self, filepath: str) -> List[ValidationIssue]:
        """Run pydocstyle on a file.

        Args:
            filepath: Path to Python file.

        Returns:
            List of validation issues from pydocstyle.
        """
        try:
            result = subprocess.run(
                ["pydocstyle", "--format=json", filepath],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return []

            # Parse pydocstyle output
            issues = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    # pydocstyle output format: filename:line:column: CODE message
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        line_no = int(parts[1])
                        col_no = int(parts[2]) if parts[2].isdigit() else 0
                        msg_parts = parts[3].strip().split(" ", 1)
                        code = msg_parts[0]
                        message = msg_parts[1] if len(msg_parts) > 1 else ""

                        issues.append(
                            ValidationIssue(
                                code=code,
                                message=message,
                                severity=Severity.WARNING,
                                line=line_no,
                                column=col_no,
                            )
                        )
                except (ValueError, IndexError):
                    continue

            return issues

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # pydocstyle not available or timeout
            return []

    def fix_docstring(self, docstring: str) -> str:
        """Automatically fix common docstring issues.

        Args:
            docstring: Original docstring.

        Returns:
            Fixed docstring.
        """
        if not self.autofix or not docstring:
            return docstring

        fixed = docstring

        # Apply autofixes
        fixed = AutofixRules.fix_spacing(fixed)
        fixed = AutofixRules.add_period(fixed)
        fixed = AutofixRules.add_blank_line_after_summary(fixed)

        return fixed

    def get_summary(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Get summary of validation issues by severity.

        Args:
            issues: List of validation issues.

        Returns:
            Dictionary with counts by severity.
        """
        summary = {"error": 0, "warning": 0, "info": 0}

        for issue in issues:
            summary[issue.severity.value] += 1

        return summary
