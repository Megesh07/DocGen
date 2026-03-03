"""Data models: dataclasses, TypedDict, Generics, forward references."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Generic, Literal, Optional, TypedDict, TypeVar

T = TypeVar("T")


# ── TYPED DICT ─────────────────────────────────────────────────────────────────

class RawRecord(TypedDict):
    """Raw API payload as returned from upstream services."""

    id: str
    kind: str
    payload: dict[str, Any]
    timestamp: float
    tags: list[str]


class PartialRecord(TypedDict, total=False):
    """A record where all fields are optional."""

    id: str
    kind: str
    meta: dict[str, str]


# ── DATACLASS WITH FIELD DEFAULTS ─────────────────────────────────────────────

@dataclass
class DocumentMeta:
    """Metadata attached to every processed document.

    Attributes:
        doc_id: Unique document identifier.
        source: Origin label for the document (e.g. ``"api"``, ``"upload"``).
        created_at: Unix timestamp of creation. Auto-set to ``time.time()``
            when not supplied.
        tags: Mutable list of string labels. Defaults to an empty list.
        extra: Arbitrary supplementary data. Defaults to empty dict.
    """

    doc_id: str
    source: str
    created_at: float = field(default_factory=time.time)
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def age_seconds(self) -> float:
        return time.time() - self.created_at

    def tag(self, *labels: str) -> None:
        for lbl in labels:
            if lbl not in self.tags:
                self.tags.append(lbl)


# ── DATACLASS: no docstring, deliberately misleading name ─────────────────────

@dataclass
class Node:
    v: Any          # "v" — what does this mean?
    nxt: Optional[Node] = None  # forward reference
    _weight: float = 0.0
    visited: bool = False

    def link(self, other: Node) -> Node:
        self.nxt = other
        return self

    def traverse(self) -> list[Any]:
        out, cur = [], self
        while cur is not None:
            out.append(cur.v)
            cur = cur.nxt
        return out


# ── GENERIC WRAPPER ────────────────────────────────────────────────────────────

class Envelope(Generic[T]):
    """A typed envelope wrapping any payload with optional error state.

    Type Parameters:
        T: The type of the wrapped payload.
    """

    def __init__(self, payload: T, *, error: str | None = None) -> None:
        self._payload = payload
        self._error = error
        self._opened = False

    def open(self) -> T:
        """Return the wrapped payload and mark the envelope as opened.

        Returns:
            T: The enclosed payload.

        Raises:
            RuntimeError: If the envelope carries an error state.
            ValueError: If the envelope has already been opened.
        """
        if self._error:
            raise RuntimeError(f"Envelope carries error: {self._error}")
        if self._opened:
            raise ValueError("Envelope already opened")
        self._opened = True
        return self._payload

    @classmethod
    def error(cls, msg: str) -> Envelope[None]:
        return cls(None, error=msg)  # type: ignore[arg-type]

    @property
    def is_ok(self) -> bool:
        return self._error is None

    def __repr__(self) -> str:
        status = "ok" if self.is_ok else f"err={self._error!r}"
        return f"Envelope<{status}>"


# ── FUNCTION WITH FORWARD REFERENCE ───────────────────────────────────────────

def link_nodes(values: list[Any]) -> Node | None:
    if not values:
        return None
    head = Node(values[0])
    cur = head
    for v in values[1:]:
        nxt = Node(v)
        cur.nxt = nxt
        cur = nxt
    return head


# ── FUNCTION: overloaded behaviour on input type, no type hints ───────────────

def flatten(obj, depth=0, _max=3):
    if depth > _max:
        return [obj]
    if isinstance(obj, dict):
        out = []
        for v in obj.values():
            out.extend(flatten(v, depth + 1, _max))
        return out
    if isinstance(obj, (list, tuple, set)):
        out = []
        for item in obj:
            out.extend(flatten(item, depth + 1, _max))
        return out
    return [obj]
