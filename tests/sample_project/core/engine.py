"""
DocumentEngine: runtime-conditional returns, closures, lambdas, generators,
dead code, and monkey-patched methods.
"""
from __future__ import annotations

import hashlib
import inspect
import types
from collections.abc import Generator
from typing import Any, Callable, Union

# forward reference used in type hint
_PluginType = Union["DocumentEngine", Callable[..., Any]]


# ── NO DOCSTRING — closure returning a closure ─────────────────────────────────

def make_pipeline(*steps: Callable) -> Callable[[Any], Any]:
    def _run(data):
        result = data
        for step in steps:
            result = step(result)
        return result

    _run.__doc__ = f"Pipeline of {len(steps)} step(s)."  # dynamic docstring
    return _run


# ── GENERATOR FUNCTION — bad docstring ────────────────────────────────────────

def chunk_iter(seq: list, size: int) -> Generator:
    """Yields chunks.

    Does chunking stuff.
    """
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


# ── LAMBDA ASSIGNED TO VARIABLE ───────────────────────────────────────────────

normalize = lambda s: s.strip().lower().replace(" ", "_")  # noqa: E731
_hash_fn = lambda x: hashlib.md5(str(x).encode()).hexdigest()[:8]  # noqa: E731


# ── FUNCTION: many types of parameters ────────────────────────────────────────

def build_record(
    kind: str,
    /,
    payload: dict,
    *tags: str,
    priority: int = 0,
    metadata: dict | None = None,
    **extra: Any,
) -> dict:
    """Build a normalised record dict from heterogeneous inputs.

    Args:
        kind: The record category (positional-only).
        payload: Core data for the record.
        *tags: Arbitrary string labels attached to the record.
        priority: Processing priority level; higher is more urgent.
            Defaults to 0.
        metadata: Optional supplemental mapping merged into the record.
            Defaults to None.
        **extra: Additional key-value pairs merged after metadata.

    Returns:
        dict: A unified record with keys ``kind``, ``payload``, ``tags``,
            ``priority``, and any merged metadata or extra fields.
    """
    base = {"kind": kind, "payload": payload, "tags": list(tags), "priority": priority}
    if metadata:
        base.update(metadata)
    base.update(extra)
    return base


# ── FUNCTION: mutable default argument (classic footgun) ─────────────────────

def append_log(message: str, log: list = []) -> list:  # noqa: B006
    log.append(message)
    return log


# ── FUNCTION: returns multiple types depending on runtime ─────────────────────

def coerce(value: Any, target_type: str) -> int | float | str | bool | None:
    _map = {
        "int": int,
        "float": float,
        "str": str,
        "bool": lambda v: v not in (False, 0, "0", "false", "False", "no", ""),
    }
    fn = _map.get(target_type)
    if fn is None:
        return None
    try:
        return fn(value)
    except (ValueError, TypeError):
        return None


# ── FUNCTION: raises different exceptions in different branches ───────────────

def strict_get(mapping: dict, key: str, *, cast=None):
    if not isinstance(mapping, dict):
        raise TypeError(f"Expected dict, received {type(mapping).__name__}")
    if key not in mapping:
        raise KeyError(f"Key '{key}' not found in mapping")
    val = mapping[key]
    if cast is not None:
        try:
            return cast(val)
        except Exception as exc:
            raise ValueError(f"Cannot cast {val!r} to {cast}") from exc
    return val


# ── FUNCTION: dead code path that is never reachable ─────────────────────────

def _internal_score(data: dict) -> float:
    score = sum(v for v in data.values() if isinstance(v, (int, float)))
    if False:  # dead branch
        score *= 999  # pragma: no cover
    return round(score, 4)


# ── CLASS: DocumentEngine with __call__, generics, monkey patching ────────────

class DocumentEngine:
    """Central document processing engine.

    Supports plugin registration, pipeline execution, and content hashing.
    Can be called directly as a shortcut to :meth:`execute`.

    Attributes:
        plugins: Ordered list of registered plugin callables.
        _cache: Internal result cache keyed by content hash.
    """

    def __init__(self, *, strict: bool = False, cache: bool = True) -> None:
        self.strict = strict
        self.plugins: list[Callable] = []
        self._cache: dict[str, Any] = {} if cache else {}
        self._cache_enabled = cache
        # dynamically assigned attribute at runtime – hard to document
        self.last_result = None  # type: ignore[assignment]

    def register(self, fn: Callable, /, position: int = -1) -> None:
        """Register a plugin function into the processing pipeline.

        Args:
            fn: A callable accepting a single document argument (positional-only).
            position: Index at which to insert the plugin. ``-1`` appends
                to the end. Defaults to -1.
        """
        if position == -1:
            self.plugins.append(fn)
        else:
            self.plugins.insert(position, fn)

    def execute(self, doc: Any) -> Any:
        h = _hash_fn(doc)
        if self._cache_enabled and h in self._cache:
            return self._cache[h]

        result = doc
        for plugin in self.plugins:
            if inspect.iscoroutinefunction(plugin):
                raise RuntimeError(
                    f"Async plugin '{plugin.__name__}' requires execute_async()"
                )
            result = plugin(result)

        self.last_result = result
        if self._cache_enabled:
            self._cache[h] = result
        return result

    async def execute_async(self, doc: Any) -> Any:
        result = doc
        for plugin in self.plugins:
            if inspect.iscoroutinefunction(plugin):
                result = await plugin(result)
            else:
                result = plugin(result)
        self.last_result = result
        return result

    def __call__(self, doc: Any) -> Any:
        return self.execute(doc)

    def __repr__(self) -> str:
        return f"<DocumentEngine plugins={len(self.plugins)} strict={self.strict}>"

    def __len__(self) -> int:
        return len(self.plugins)


# ── MONKEY PATCHING ────────────────────────────────────────────────────────────

def _patched_execute(self, doc):
    """Monkey-patched execute: uppercases string output."""
    result = DocumentEngine.execute(self, doc)
    if isinstance(result, str):
        return result.upper()
    return result


def enable_uppercase_mode(engine: DocumentEngine) -> None:
    engine.execute = types.MethodType(_patched_execute, engine)  # type: ignore[method-assign]
