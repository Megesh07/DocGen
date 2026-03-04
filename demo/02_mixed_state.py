"""
Demo file 2 — Mixed State
=========================
Simulates a real-world codebase that is partially documented.
Expected model behaviour:
  - Functions WITH a complete, correct docstring → PRESERVED (blue dot)
  - Functions WITH # autodoc: ignore → SKIPPED entirely (grey dot)
  - Functions WITHOUT docstrings → GENERATED (green dot)

Covers:
  - Pre-existing complete docstring (preserved, not re-written)
  - # autodoc: ignore directive (skipped unconditionally)
  - Missing docstrings on otherwise well-typed functions
  - Class where some methods are documented and some are not
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


# ── Already documented — model should leave these alone ─────────────────────

def read_file(path: str, encoding: str = "utf-8") -> str:
    """Read the entire contents of a text file and return it as a string.

    Args:
        path: Absolute or relative path to the file.
        encoding: Character encoding to use when reading. Defaults to utf-8.

    Returns:
        The full text content of the file.

    Raises:
        FileNotFoundError: If the file does not exist at the given path.
        PermissionError: If the process lacks read permission for the file.
    """
    with open(path, encoding=encoding) as fh:
        return fh.read()


def slugify(text: str) -> str:
    """Convert a human-readable string into a URL-friendly slug.

    Args:
        text: The input string to convert.

    Returns:
        A lowercase string with spaces replaced by hyphens and
        non-alphanumeric characters removed.
    """
    import re
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_]+", "-", text)


# ── Ignored — model must not touch these ────────────────────────────────────

def _internal_checksum(data: bytes) -> int:  # autodoc: ignore
    total = 0
    for byte in data:
        total ^= byte
    return total


class _LegacyAdapter:  # autodoc: ignore
    def run(self, payload: dict) -> dict:
        return payload


# ── Undocumented — model should generate docstrings for these ───────────────

def write_json(obj: dict, path: str, indent: int = 2) -> None:
    import json
    Path(path).write_text(json.dumps(obj, indent=indent), encoding="utf-8")


def paginate(items: list, page: int, page_size: int) -> list:
    start = (page - 1) * page_size
    return items[start : start + page_size]


def retry(func, max_attempts: int = 3, delay: float = 1.0):
    import time
    for attempt in range(max_attempts):
        try:
            return func()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay)


# ── Class with mixed coverage ────────────────────────────────────────────────

class EmailService:
    """Provides utilities for sending and validating email messages."""

    def __init__(self, smtp_host: str, smtp_port: int = 587) -> None:
        """Initialise the service with SMTP connection details.

        Args:
            smtp_host: Hostname of the SMTP server.
            smtp_port: Port number for the SMTP connection. Defaults to 587.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self._sent: int = 0

    # documented — should be preserved
    def validate_address(self, address: str) -> bool:
        """Check whether an email address has a valid format.

        Args:
            address: The email address string to validate.

        Returns:
            True if the address contains exactly one '@' with non-empty
            local and domain parts, False otherwise.
        """
        parts = address.split("@")
        return len(parts) == 2 and all(parts)

    # undocumented — should be generated
    def send(self, to: str, subject: str, body: str) -> bool:
        if not self.validate_address(to):
            return False
        # Simulated send
        self._sent += 1
        return True

    def get_sent_count(self) -> int:
        return self._sent

    def bulk_send(self, recipients: list[str], subject: str, body: str) -> dict[str, bool]:
        return {addr: self.send(addr, subject, body) for addr in recipients}
