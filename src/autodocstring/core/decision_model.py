"""Shared decision model used by CLI, API, and session manager.

This is the single source of truth for how a reviewer decision is
represented and serialised.  All layers must import from here – never
define a separate DecisionRecord elsewhere.

Usage
-----
From CLI review file::

    records = [DecisionRecord.from_dict(d) for d in json_list]

From session manager::

    record = DecisionRecord(file="...", function="...")
    session.decisions[(record.file, record.function)] = record
    payload = record.to_dict()

From API schema (FunctionDecision → DecisionRecord)::

    record = DecisionRecord.from_api_decision(api_decision)
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class DecisionRecord:
    """Canonical representation of a reviewer's decision for one function.

    Attributes:
        file: Absolute path to the source file.
        function: Fully qualified function name (e.g. ``MyClass.my_method``).
        lineno: 1-based line number of the function definition.
        docstring: The generated docstring text (empty if not yet generated).
        confidence: Confidence score from 0 to 1.
        risk: Risk level string (``LOW`` | ``MEDIUM`` | ``HIGH``).
        approved: True = apply, False = skip, None = not yet reviewed.
        created_at: ISO-8601 timestamp when the record was created.
    """

    file: str
    function: str
    lineno: int = 0
    docstring: str = ""
    confidence: float = 1.0
    risk: str = "LOW"
    approved: Optional[bool] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a JSON-compatible dictionary.

        Returns:
            Plain dict representation of this record.
        """
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DecisionRecord":
        """Deserialise from a dictionary (e.g. loaded from JSON).

        Unknown keys are silently ignored for forward compatibility.

        Args:
            data: Dictionary containing at minimum ``file`` and ``function``.

        Returns:
            DecisionRecord instance.
        """
        return cls(
            file=data.get("file", ""),
            function=data.get("function", ""),
            lineno=data.get("lineno", 0),
            docstring=data.get("docstring", ""),
            confidence=float(data.get("confidence", 1.0)),
            risk=data.get("risk", "LOW"),
            approved=data.get("approved"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
        )

    @classmethod
    def from_scan_result(cls, result: Dict[str, Any]) -> "DecisionRecord":
        """Create a record from a scan/generate API result dict.

        Args:
            result: DocstringResultSchema-compatible dict.

        Returns:
            DecisionRecord with approved=None.
        """
        return cls(
            file=result.get("file", ""),
            function=result.get("function", ""),
            lineno=result.get("lineno", 0),
            docstring=result.get("docstring", ""),
            confidence=float(result.get("confidence", 1.0)),
            risk=result.get("risk", "LOW"),
            approved=None,
        )

    # ------------------------------------------------------------------
    # Review file helpers
    # ------------------------------------------------------------------

    @staticmethod
    def list_to_json(records: List["DecisionRecord"]) -> str:
        """Serialise a list of records to a formatted JSON string.

        Args:
            records: List of DecisionRecord instances.

        Returns:
            Pretty-printed JSON string suitable for the review file.
        """
        return json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False)

    @staticmethod
    def list_from_json(text: str) -> List["DecisionRecord"]:
        """Deserialise a list of records from a JSON string.

        Args:
            text: JSON string (e.g. contents of review file).

        Returns:
            List of DecisionRecord instances.

        Raises:
            ValueError: If the JSON is invalid.
        """
        try:
            items = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc
        return [DecisionRecord.from_dict(item) for item in items]
