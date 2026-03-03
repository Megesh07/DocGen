"""
Demo file 3 – STYLE MISMATCH (NumPy-style in a Google-style project).

All functions are documented in NumPy style. When scanned with
the default Google mode, the tool flags every function as a style
mismatch and queues them for regeneration in the correct format.
"""
from __future__ import annotations


def flatten(nested: list) -> list:
    """
    Recursively flatten a nested list.

    Parameters
    ----------
    nested : list
        A list that may contain sub-lists at any depth.

    Returns
    -------
    list
        A single flat list containing all leaf elements.
    """
    result: list = []
    for item in nested:
        if isinstance(item, list):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def chunk(lst: list, size: int) -> list[list]:
    """
    Split a list into fixed-size chunks.

    Parameters
    ----------
    lst : list
        The input list to split.
    size : int
        Maximum number of elements per chunk.

    Returns
    -------
    list[list]
        List of sublists each of length *size* (last may be shorter).

    Raises
    ------
    ValueError
        If *size* is not a positive integer.
    """
    if size <= 0:
        raise ValueError("Chunk size must be a positive integer.")
    return [lst[i : i + size] for i in range(0, len(lst), size)]


def group_by(items: list, key) -> dict:
    """
    Group list items by a key function.

    Parameters
    ----------
    items : list
        Items to group.
    key : callable
        Function that returns the group key for each item.

    Returns
    -------
    dict
        Mapping of key → list of items sharing that key.
    """
    groups: dict = {}
    for item in items:
        groups.setdefault(key(item), []).append(item)
    return groups


def moving_average(data: list[float], window: int) -> list[float]:
    """
    Compute a simple moving average over a sliding window.

    Parameters
    ----------
    data : list[float]
        Numeric data series.
    window : int
        Number of data points per window.

    Returns
    -------
    list[float]
        Averaged values; length is ``len(data) - window + 1``.

    Raises
    ------
    ValueError
        If *window* is non-positive or exceeds the data length.
    """
    import statistics
    if window <= 0:
        raise ValueError("Window size must be positive.")
    if window > len(data):
        raise ValueError("Window size cannot exceed data length.")
    return [statistics.mean(data[i : i + window]) for i in range(len(data) - window + 1)]
