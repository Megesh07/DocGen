"""
DEMO SCENARIO 3 – Style Mismatch.

This file uses NumPy-style docstrings throughout, but when the
scanner runs in Google mode it detects the mismatch and flags
every function for regeneration. Watch coverage drop to 0 in
"validated google" view, then recover after applying suggestions.
"""
from __future__ import annotations

from typing import Optional


def matrix_multiply(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    """
    Multiply two 2-D matrices.

    Parameters
    ----------
    a : list[list[float]]
        Left matrix of shape M × K.
    b : list[list[float]]
        Right matrix of shape K × N.

    Returns
    -------
    list[list[float]]
        Result matrix of shape M × N.

    Raises
    ------
    ValueError
        If the inner dimensions do not match.
    """
    if not a or not a[0] or not b or not b[0]:
        raise ValueError("Matrices must be non-empty.")
    rows_a, cols_a = len(a), len(a[0])
    rows_b, cols_b = len(b), len(b[0])
    if cols_a != rows_b:
        raise ValueError(f"Incompatible dimensions: ({rows_a}×{cols_a}) × ({rows_b}×{cols_b})")
    result = [[sum(a[i][k] * b[k][j] for k in range(cols_a)) for j in range(cols_b)] for i in range(rows_a)]
    return result


def dot_product(v1: list[float], v2: list[float]) -> float:
    """
    Compute the dot product of two vectors.

    Parameters
    ----------
    v1 : list[float]
        First vector.
    v2 : list[float]
        Second vector.

    Returns
    -------
    float
        Scalar dot product.

    Raises
    ------
    ValueError
        If vectors have different lengths.
    """
    if len(v1) != len(v2):
        raise ValueError("Vectors must have the same length.")
    return sum(x * y for x, y in zip(v1, v2))


def transpose(matrix: list[list[float]]) -> list[list[float]]:
    """
    Transpose a 2-D matrix.

    Parameters
    ----------
    matrix : list[list[float]]
        Input matrix of shape M × N.

    Returns
    -------
    list[list[float]]
        Transposed matrix of shape N × M.
    """
    if not matrix:
        return []
    return [list(row) for row in zip(*matrix)]


def identity_matrix(n: int) -> list[list[float]]:
    """
    Create an n × n identity matrix.

    Parameters
    ----------
    n : int
        Dimension of the square matrix.

    Returns
    -------
    list[list[float]]
        Identity matrix.

    Raises
    ------
    ValueError
        If n is not a positive integer.
    """
    if n <= 0:
        raise ValueError("Dimension must be a positive integer.")
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
