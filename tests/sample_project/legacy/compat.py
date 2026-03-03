"""
Legacy compatibility layer: Python 2-style patterns, monkey patching,
conditional imports, runtime class modification, and dynamic attributes.
Quality: deliberately undocumented.
"""
from __future__ import annotations

import sys
import warnings
from typing import Any


# ── CONDITIONAL IMPORT ─────────────────────────────────────────────────────────

if sys.version_info >= (3, 11):
    from tomllib import loads as _toml_loads
else:
    try:
        from tomllib import loads as _toml_loads  # type: ignore[no-redef]
    except ImportError:
        try:
            from tomli import loads as _toml_loads  # type: ignore[no-redef]
        except ImportError:
            def _toml_loads(s: str) -> dict:  # type: ignore[misc]
                raise ImportError("No TOML parser available. pip install tomli")


def load_config(raw: str) -> dict:
    return _toml_loads(raw)


# ── PYTHON 2-STYLE CLASS ───────────────────────────────────────────────────────

class OldStyleMapper(object):
    """Maps keys. Legacy.

    Args:
        d: dict.
    """
    def __init__(self, d=None):
        self.d = d or {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v
        return self

    def keys(self):
        return self.d.keys()

    def __contains__(self, k):
        return k in self.d

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __repr__(self):
        return f"OldStyleMapper({self.d!r})"


# ── DYNAMIC ATTRIBUTE ASSIGNMENT ───────────────────────────────────────────────

class DynamicRecord:
    ALLOWED: frozenset[str] = frozenset()  # subclasses override

    def __setattr__(self, name: str, value: Any) -> None:
        if self.ALLOWED and name not in self.ALLOWED and not name.startswith("_"):
            raise AttributeError(f"Dynamic attribute {name!r} not allowed on {type(self).__name__}")
        object.__setattr__(self, name, value)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class FlexRecord(DynamicRecord):
    ALLOWED = frozenset()  # accepts anything

    @classmethod
    def from_dict(cls, d: dict) -> FlexRecord:
        obj = cls()
        for k, v in d.items():
            object.__setattr__(obj, k, v)
        return obj


# ── MONKEY PATCHING AT MODULE LEVEL ───────────────────────────────────────────

def _compat_loads(s: str | bytes) -> dict:
    import json
    if isinstance(s, bytes):
        s = s.decode("utf-8", errors="replace")
    return json.loads(s)


# Patch OldStyleMapper to also support JSON loading
OldStyleMapper.from_json = classmethod(  # type: ignore[attr-defined]
    lambda cls, s: cls(_compat_loads(s))
)


# ── RUNTIME CLASS MODIFICATION ─────────────────────────────────────────────────

def add_audit_trail(klass: type) -> type:
    _orig_setattr = klass.__setattr__ if hasattr(klass, "__setattr__") else object.__setattr__
    _log: list[tuple[str, Any, Any]] = []

    def _audited_setattr(self, name, value):
        old = getattr(self, name, "<unset>")
        _orig_setattr(self, name, value)
        _log.append((name, old, value))

    klass.__setattr__ = _audited_setattr  # type: ignore[method-assign]
    klass._audit_log = _log  # type: ignore[attr-defined]
    return klass


@add_audit_trail
class AuditedConfig:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)

    def snapshot(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


# ── GENERATOR WITH SEND / THROW ────────────────────────────────────────────────

def accumulate_gen(start: float = 0.0):
    total = start
    while True:
        delta = yield total
        if delta is None:
            return
        if delta < 0:
            raise ValueError(f"Delta must be non-negative, got {delta}")
        total += delta


# ── FUNCTION USING EXEC AT RUNTIME ────────────────────────────────────────────

def build_class_from_spec(name: str, fields: list[str]) -> type:
    lines = [f"class {name}:"]
    lines.append("    def __init__(self, " + ", ".join(fields) + "):")
    for f in fields:
        lines.append(f"        self.{f} = {f}")
    lines.append("    def __repr__(self):")
    repr_parts = " + ', '.join".join([])
    lines.append(
        f"        return f\"{name}("
        + ", ".join(f"{f}={{self.{f}!r}}" for f in fields)
        + ")\""
    )
    src = "\n".join(lines)
    ns: dict[str, Any] = {}
    exec(src, ns)  # noqa: S102
    return ns[name]
