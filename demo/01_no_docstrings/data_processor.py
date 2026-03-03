"""
DEMO SCENARIO 1 – Zero-docstring file.

A realistic data-processing module with type hints but NO docstrings.
Demonstrates how the tool handles modules with plain functions,
list/dict operations, and typed parameters.
"""
from __future__ import annotations

import statistics
from typing import Any, Callable, Iterable


def flatten(nested: list) -> list:
    result: list = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(lst: list, size: int) -> list[list]:
    if size <= 0:
        raise ValueError("Chunk size must be a positive integer.")
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def deduplicate(items: list, key: Callable | None = None) -> list:
    seen: set = set()
    result: list = []
    for item in items:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


def group_by(items: list, key: Callable) -> dict:
    groups: dict = {}
    for item in items:
        k = key(item)
        groups.setdefault(k, []).append(item)
    return groups


def safe_get(d: dict, *keys: str, default: Any = None) -> Any:
    current = d
    for k in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(k, default)
        if current is default:
            return default
    return current


def normalize_list(values: list[float]) -> list[float]:
    min_val = min(values)
    max_val = max(values)
    if max_val == min_val:
        return [0.0] * len(values)
    return [(v - min_val) / (max_val - min_val) for v in values]


def moving_average(data: list[float], window: int) -> list[float]:
    if window <= 0:
        raise ValueError("Window size must be positive.")
    if window > len(data):
        raise ValueError("Window size cannot exceed data length.")
    return [
        statistics.mean(data[i : i + window])
        for i in range(len(data) - window + 1)
    ]


def zscore(values: list[float]) -> list[float]:
    if len(values) < 2:
        raise ValueError("Z-score requires at least 2 data points.")
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    if std == 0:
        return [0.0] * len(values)
    return [(v - mean) / std for v in values]


def merge_dicts(*dicts: dict) -> dict:
    result: dict = {}
    for d in dicts:
        result.update(d)
    return result


def pivot(records: list[dict], index_key: str, value_key: str) -> dict:
    return {row[index_key]: row[value_key] for row in records if index_key in row and value_key in row}


def filter_none(items: Iterable) -> list:
    return [item for item in items if item is not None]
