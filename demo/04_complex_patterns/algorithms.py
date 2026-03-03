"""
DEMO SCENARIO 4 – Complex Patterns.

Classic algorithms with no docstrings. This showcases how the
tool generates accurate Args/Returns/Raises for non-trivial logic:
  - Binary search
  - Merge sort
  - BFS / DFS on graphs
  - Dynamic-programming Fibonacci / Knapsack
"""
from __future__ import annotations

from collections import deque
from typing import Any, Optional


def binary_search(arr: list, target: Any, lo: int = 0, hi: int | None = None) -> int:
    if hi is None:
        hi = len(arr) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def merge_sort(arr: list[int]) -> list[int]:
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    return _merge(left, right)


def _merge(left: list[int], right: list[int]) -> list[int]:
    result: list[int] = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result


def bfs(graph: dict[str, list[str]], start: str) -> list[str]:
    visited: list[str] = []
    queue: deque[str] = deque([start])
    seen: set[str] = {start}
    while queue:
        node = queue.popleft()
        visited.append(node)
        for neighbour in graph.get(node, []):
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return visited


def dfs(graph: dict[str, list[str]], start: str, visited: set | None = None) -> list[str]:
    if visited is None:
        visited = set()
    visited.add(start)
    result = [start]
    for neighbour in graph.get(start, []):
        if neighbour not in visited:
            result.extend(dfs(graph, neighbour, visited))
    return result


def fibonacci_dp(n: int) -> int:
    if n < 0:
        raise ValueError("n must be a non-negative integer.")
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]


def knapsack(weights: list[int], values: list[int], capacity: int) -> int:
    n = len(weights)
    if len(values) != n:
        raise ValueError("weights and values must have the same length.")
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for w in range(capacity + 1):
            dp[i][w] = dp[i - 1][w]
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
    return dp[n][capacity]


def longest_common_subsequence(s1: str, s2: str) -> int:
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]
