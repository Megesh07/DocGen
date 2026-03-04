"""
Demo file 3 — Confidence Stress Test
=====================================
Functions designed to exercise every penalty rule in ConfidenceScorer.
Expected model behaviour:
  - score >= 0.85 → AUTO_APPLY (generated quietly)
  - 0.60 <= score < 0.85 → REVIEW (generated, flagged for review — yellow indicator)
  - score < 0.60 → SKIP (not generated)

Penalty rules exercised here:
  -0.05 per untyped parameter
  -0.10 for missing return type annotation
  -0.10 for branch count > 8 (if/elif/for/while/try/BoolOp nodes)
  -0.05 for generator function (yield)
  -0.05 for external non-whitelisted call
"""

from __future__ import annotations

from typing import Any, Generator, Iterator


# ── HIGH CONFIDENCE (>=0.85) — fully typed, simple logic ────────────────────

def celsius_to_fahrenheit(celsius: float) -> float:
    return celsius * 9 / 5 + 32


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


# ── REVIEW ZONE (0.60–0.84) — missing type hints ────────────────────────────
# Each missing param type = -0.05, missing return = -0.10

def calculate_discount(price, discount_percent, min_price=0):
    # 3 untyped params (-0.15) + no return type (-0.10) → score ≈ 0.75 → REVIEW
    discounted = price * (1 - discount_percent / 100)
    return max(discounted, min_price)


def merge_dicts(base, override, deep=False):
    # 3 untyped params (-0.15) + no return type (-0.10) → score ≈ 0.75 → REVIEW
    if not deep:
        return {**base, **override}
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value, deep=True)
        else:
            result[key] = value
    return result


# ── HIGH BRANCH COUNT (>8 branches → -0.10) ─────────────────────────────────

def classify_http_status(status_code: int) -> str:
    # 11 branches → branch penalty -0.10 → score ≈ 0.90 (still good with types)
    if status_code == 200:
        return "OK"
    elif status_code == 201:
        return "Created"
    elif status_code == 204:
        return "No Content"
    elif status_code == 301:
        return "Moved Permanently"
    elif status_code == 302:
        return "Found"
    elif status_code == 400:
        return "Bad Request"
    elif status_code == 401:
        return "Unauthorized"
    elif status_code == 403:
        return "Forbidden"
    elif status_code == 404:
        return "Not Found"
    elif status_code == 500:
        return "Internal Server Error"
    elif status_code == 503:
        return "Service Unavailable"
    return "Unknown"


def validate_config(config) -> list[str]:
    # Untyped 'config' (-0.05) + 10 branches (-0.10) → score ≈ 0.85 → border
    errors = []
    if "host" not in config:
        errors.append("missing host")
    if "port" not in config:
        errors.append("missing port")
    elif not isinstance(config["port"], int):
        errors.append("port must be an integer")
    elif config["port"] < 1 or config["port"] > 65535:
        errors.append("port out of range")
    if "timeout" in config:
        if not isinstance(config["timeout"], (int, float)):
            errors.append("timeout must be numeric")
        elif config["timeout"] <= 0:
            errors.append("timeout must be positive")
    if "retries" in config and config["retries"] < 0:
        errors.append("retries must be >= 0")
    return errors


# ── GENERATOR FUNCTIONS (-0.05 penalty) ─────────────────────────────────────

def fibonacci(limit: int) -> Generator[int, None, None]:
    a, b = 0, 1
    while a <= limit:
        yield a
        a, b = b, a + b


def chunk(iterable: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


# ── *args / **kwargs (each untyped = -0.05) ─────────────────────────────────

def log_event(*args, **kwargs) -> None:
    # 2 untyped params (-0.10) → score ≈ 0.90
    parts = [str(a) for a in args]
    parts += [f"{k}={v}" for k, v in kwargs.items()]
    print(" | ".join(parts))


def build_query(table, *conditions, **options):
    # 1 untyped + 2 variadic untyped (-0.15) + no return (-0.10) → score ≈ 0.75 → REVIEW
    where_clause = " AND ".join(conditions)
    limit = options.get("limit", 100)
    order = options.get("order", "id")
    return f"SELECT * FROM {table} WHERE {where_clause} ORDER BY {order} LIMIT {limit}"
