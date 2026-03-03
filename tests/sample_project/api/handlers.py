"""
API handlers: conditional imports, runtime evaluation, overloaded signatures,
very long parameter lists. Quality deliberately mixed.
"""
from __future__ import annotations

import os
import sys
from typing import Any

# ── CONDITIONAL IMPORT ─────────────────────────────────────────────────────────
try:
    import ujson as _json
except ImportError:
    import json as _json  # type: ignore[no-redef]


# ── RUNTIME EVAL ───────────────────────────────────────────────────────────────

def _build_filter(expr: str) -> Any:
    """Compile and return a filter callable from a Python expression string.

    The expression is evaluated with ``eval`` against an empty globals dict
    plus ``__builtins__``.  The result must be callable.

    Args:
        expr: A Python expression that evaluates to a callable, e.g.
            ``"lambda x: x.get('active')"``

    Returns:
        Callable: The compiled filter function.

    Raises:
        ValueError: If the evaluated expression is not callable.
        SyntaxError: If expr contains invalid Python syntax.
    """
    result = eval(expr, {"__builtins__": __builtins__})  # noqa: S307
    if not callable(result):
        raise ValueError(f"Expression did not produce a callable: {expr!r}")
    return result


# ── VERY LONG PARAMETER LIST ───────────────────────────────────────────────────

def create_response(
    status: int,
    body: Any = None,
    headers: dict | None = None,
    content_type: str = "application/json",
    encoding: str = "utf-8",
    cache_control: str = "no-store",
    x_request_id: str | None = None,
    x_correlation_id: str | None = None,
    retry_after: int | None = None,
    vary: list[str] | None = None,
    allow_origin: str = "*",
    expose_headers: list[str] | None = None,
    compress: bool = False,
    *,
    strict: bool = False,
    _internal_trace: str | None = None,
) -> dict:
    h = dict(headers or {})
    h["Content-Type"] = f"{content_type}; charset={encoding}"
    h["Cache-Control"] = cache_control
    h["Access-Control-Allow-Origin"] = allow_origin
    if x_request_id:
        h["X-Request-Id"] = x_request_id
    if x_correlation_id:
        h["X-Correlation-Id"] = x_correlation_id
    if retry_after is not None:
        h["Retry-After"] = str(retry_after)
    if vary:
        h["Vary"] = ", ".join(vary)
    if expose_headers:
        h["Access-Control-Expose-Headers"] = ", ".join(expose_headers)

    serialized = _json.dumps(body) if body is not None else None
    if compress and serialized:
        import zlib
        serialized = zlib.compress(serialized.encode(encoding))

    record = {"status": status, "headers": h, "body": serialized}
    if _internal_trace and os.getenv("DEBUG_TRACE"):
        record["_trace"] = _internal_trace
    return record


# ── HANDLER: returns different response shapes per branch ─────────────────────

def handle_request(method: str, path: str, data: Any = None, **ctx) -> dict | list | None:
    method = method.upper()
    if method == "GET":
        return {"method": "GET", "path": path, "ctx": ctx}
    if method == "POST":
        if data is None:
            return create_response(400, {"error": "body required"})
        return create_response(201, data)
    if method == "DELETE":
        return []
    if method == "OPTIONS":
        return None  # implicit None
    return create_response(405, {"error": f"Method {method} not allowed"})


# ── HANDLER WITH NESTED FUNCTION ───────────────────────────────────────────────

def paginate(items: list, page: int = 1, per_page: int = 20) -> dict:
    def _slice(lst, p, pp):
        start = (p - 1) * pp
        return lst[start : start + pp]

    def _meta(total, p, pp):
        import math
        return {
            "total": total,
            "page": p,
            "per_page": pp,
            "pages": math.ceil(total / pp) if pp else 0,
        }

    if page < 1:
        raise ValueError("page must be >= 1")
    if per_page < 1:
        raise ValueError("per_page must be >= 1")

    return {"items": _slice(items, page, per_page), "meta": _meta(len(items), page, per_page)}


# ── PRIVATE: internal validation, no docstring ────────────────────────────────

def _validate_schema(data: dict, schema: dict) -> list[str]:
    errors = []
    for field, rules in schema.items():
        if rules.get("required") and field not in data:
            errors.append(f"Missing required field: {field!r}")
            continue
        if field in data:
            expected_type = rules.get("type")
            if expected_type and not isinstance(data[field], expected_type):
                errors.append(
                    f"Field {field!r}: expected {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )
    return errors
