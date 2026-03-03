"""
DEMO SCENARIO 5 – Edge Cases.

Python generator functions and context managers.
The tool detects ``is_generator=True`` and ``is_async=True`` from the AST
and generates appropriate docstring headers mentioning "Yields" or
"Async generator" automatically.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Iterator


def count_up(start: int, stop: int, step: int = 1) -> Generator[int, None, None]:
    if step == 0:
        raise ValueError("Step cannot be zero.")
    current = start
    while (step > 0 and current < stop) or (step < 0 and current > stop):
        yield current
        current += step


def fibonacci() -> Generator[int, None, None]:
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b


def read_chunks(filepath: str | Path, chunk_size: int = 4096) -> Generator[bytes, None, None]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            yield chunk


def windowed(iterable: list, size: int) -> Generator[tuple, None, None]:
    if size <= 0:
        raise ValueError("Window size must be positive.")
    for i in range(len(iterable) - size + 1):
        yield tuple(iterable[i : i + size])


def take(n: int, gen: Iterator) -> list:
    result = []
    for _ in range(n):
        try:
            result.append(next(gen))
        except StopIteration:
            break
    return result


@contextmanager
def temp_directory() -> Generator[Path, None, None]:
    import shutil
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@contextmanager
def chdir(path: str | Path) -> Generator[None, None, None]:
    import os
    original = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(original)


@contextmanager
def suppress_exceptions(*exception_types: type) -> Generator[None, None, None]:
    try:
        yield
    except tuple(exception_types):
        pass
