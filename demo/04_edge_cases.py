"""
Demo file 4 — Parser Edge Cases
================================
Exercises every structural pattern the AST parser and SafeApplier must handle.
Expected model behaviour: docstrings generated for all un-documented items;
parser correctly extracts metadata from every pattern.

Covers:
  - @dataclass (class-level field annotations, no explicit __init__)
  - @property getter and setter
  - @abstractmethod
  - Context manager (__enter__ / __exit__)
  - async def + async generator (yield inside async def)
  - Nested / inner functions
  - __dunder__ methods (__repr__, __eq__, __len__)
  - Union / Optional type hints
  - Functions with only 'pass' or 'raise' body
  - @staticmethod + @classmethod on same class
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Union


# ── @dataclass ───────────────────────────────────────────────────────────────

@dataclass
class Point:
    x: float
    y: float
    label: str = ""
    tags: list[str] = field(default_factory=list)

    def distance_to(self, other: Point) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def translate(self, dx: float, dy: float) -> Point:
        return Point(self.x + dx, self.y + dy, self.label, self.tags)

    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return self.x == other.x and self.y == other.y


# ── Abstract base class ───────────────────────────────────────────────────────

class Serializer(ABC):

    @abstractmethod
    def serialize(self, data: dict) -> str:
        pass

    @abstractmethod
    def deserialize(self, raw: str) -> dict:
        pass

    def round_trip(self, data: dict) -> dict:
        return self.deserialize(self.serialize(data))


class JsonSerializer(Serializer):

    def serialize(self, data: dict) -> str:
        import json
        return json.dumps(data)

    def deserialize(self, raw: str) -> dict:
        import json
        return json.loads(raw)


# ── @property getter + setter ─────────────────────────────────────────────────

class Temperature:

    def __init__(self, celsius: float = 0.0) -> None:
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("temperature below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9 / 5 + 32

    @property
    def kelvin(self) -> float:
        return self._celsius + 273.15


# ── Context manager (__enter__ / __exit__) ────────────────────────────────────

class Timer:

    def __init__(self, name: str = "timer") -> None:
        self.name = name
        self.elapsed: float = 0.0

    def __enter__(self) -> Timer:
        import time
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        import time
        self.elapsed = time.perf_counter() - self._start
        return False  # do not suppress exceptions

    def __repr__(self) -> str:
        return f"Timer(name={self.name!r}, elapsed={self.elapsed:.4f}s)"


# ── async def + async generator ───────────────────────────────────────────────

async def fetch_pages(base_url: str, max_pages: int = 5) -> AsyncIterator[dict]:
    for page in range(1, max_pages + 1):
        await asyncio.sleep(0)            # simulated I/O yield
        yield {"url": f"{base_url}?page={page}", "page": page}


async def gather_results(urls: list[str], timeout: float = 10.0) -> list[dict]:
    async def _fetch_one(url: str) -> dict:
        await asyncio.sleep(0)
        return {"url": url, "status": 200}

    tasks = [asyncio.create_task(_fetch_one(u)) for u in urls]
    return await asyncio.gather(*tasks)


# ── Nested / inner functions ──────────────────────────────────────────────────

def memoize(func):
    cache: dict = {}

    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]

    return wrapper


def make_multiplier(factor: float):
    def multiplier(value: float) -> float:
        return value * factor
    return multiplier


# ── Union / Optional in signatures ───────────────────────────────────────────

def parse_int(value: Union[str, int, float]) -> Optional[int]:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def coerce_to_list(value: Union[str, list, None]) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# ── pass-only and raise-only bodies ──────────────────────────────────────────

def not_implemented_yet(data: dict) -> dict:
    pass


def must_override(x: int, y: int) -> int:
    raise NotImplementedError("subclass must implement this method")


# ── __len__ + __contains__ ────────────────────────────────────────────────────

class TagRegistry:

    def __init__(self) -> None:
        self._tags: set[str] = set()

    def add(self, tag: str) -> None:
        self._tags.add(tag.lower())

    def remove(self, tag: str) -> None:
        self._tags.discard(tag.lower())

    def __len__(self) -> int:
        return len(self._tags)

    def __contains__(self, tag: str) -> bool:
        return tag.lower() in self._tags

    def __iter__(self):
        return iter(sorted(self._tags))
