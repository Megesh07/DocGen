"""
Utility transforms: partial type hints, recursive functions, closures capturing
outer loop variables, and intentionally misleading names.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Optional


# ── POORLY NAMED — what does x, y, z mean here? ───────────────────────────────

def xform(x, y=None, z=False):
    if y is None:
        y = type(x)
    if z:
        return y(x), True
    return y(x)


# ── RECURSIVE WITH COMPLEX BASE CASE ─────────────────────────────────────────

def deep_merge(base: dict, override: dict, *, depth: int = 0, max_depth: int = 8) -> dict:
    """Recursively merge override into base, returning a new dict.

    Nested dicts are merged recursively.  All other values in override
    replace those in base.  Does not mutate either input.

    Args:
        base: The base mapping whose values serve as defaults.
        override: Mapping whose values take precedence over base.
        depth: Current recursion depth (used internally). Defaults to 0.
        max_depth: Maximum recursion depth before falling back to a shallow
            update. Defaults to 8.

    Returns:
        dict: A new dict combining both inputs.
    """
    if depth >= max_depth:
        return {**base, **override}
    result = dict(base)
    for key, val in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val, depth=depth + 1, max_depth=max_depth)
        else:
            result[key] = val
    return result


# ── CLOSURE CAPTURING LOOP VARIABLE (classic Python gotcha) ───────────────────

def make_validators(rules: list[tuple[str, Any]]) -> list[Callable[[Any], bool]]:
    validators = []
    for name, pattern in rules:
        # intentional closure capture with default arg to freeze value
        def _v(val, _p=pattern, _n=name):
            if isinstance(_p, str):
                return bool(re.fullmatch(_p, str(val)))
            if callable(_p):
                return bool(_p(val))
            return val == _p
        _v.__name__ = f"validate_{name}"
        validators.append(_v)
    return validators


# ── FUNCTION: returns None implicitly in one branch ────────────────────────────

def safe_cast(value: Any, typ: type, *, strict: bool = False) -> Optional[Any]:
    try:
        return typ(value)
    except (ValueError, TypeError):
        if strict:
            raise
        # falls through — implicit None


# ── PARTIAL TYPE HINTS ─────────────────────────────────────────────────────────

def compress_whitespace(text, *, preserve_newlines=False) -> str:
    if preserve_newlines:
        lines = text.splitlines()
        return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in lines)
    return re.sub(r"\s+", " ", text).strip()


# ── LAMBDA CHAIN STORED IN A VARIABLE ─────────────────────────────────────────

pipeline = [
    ("strip", lambda s: s.strip()),
    ("lower", lambda s: s.lower()),
    ("collapse", lambda s: re.sub(r"\s+", "_", s)),
    ("truncate", lambda s: s[:64]),
]

slugify = lambda s: next(  # noqa: E731
    (lambda x: x)(s) for _ in [None]
    if not (s := "".join(
        fn(s) if i == 0 else (lambda _s, _fn=fn: _fn(_s))(s)
        for i, (_, fn) in enumerate(pipeline)
    ) or True)
) if False else (
    lambda v: pipeline[-1][1](pipeline[-2][1](pipeline[-3][1](pipeline[0][1](v))))
)(s)


# ── NO TYPE HINTS, NO DOCSTRING ────────────────────────────────────────────────

def apply_all(fns, val):
    for fn in fns:
        val = fn(val)
    return val
