"""
DEMO SCENARIO 5 – Edge Cases.

Dataclasses, NamedTuples, and TypedDicts — modern Python data
modelling patterns. Demonstrates that the tool correctly documents
``__init__``, ``__post_init__``, class variables, and field defaults
without breaking the ``@dataclass`` decorator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple, Optional, TypedDict


@dataclass
class Point:
    x: float
    y: float

    def distance_to(self, other: "Point") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5

    def translate(self, dx: float, dy: float) -> "Point":
        return Point(self.x + dx, self.y + dy)

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)


@dataclass(order=True)
class Version:
    major: int
    minor: int
    patch: int = 0

    def __post_init__(self) -> None:
        for attr in ("major", "minor", "patch"):
            if getattr(self, attr) < 0:
                raise ValueError(f"{attr} cannot be negative.")

    def bump_major(self) -> "Version":
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> "Version":
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "Version":
        return Version(self.major, self.minor, self.patch + 1)

    def is_compatible_with(self, other: "Version") -> bool:
        return self.major == other.major

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


@dataclass
class Address:
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "US"
    apartment: Optional[str] = None
    _normalized: bool = field(default=False, repr=False, init=False)

    def __post_init__(self) -> None:
        self.postal_code = self.postal_code.strip()
        self.city = self.city.strip().title()
        self._normalized = True

    def one_liner(self) -> str:
        parts = [self.street]
        if self.apartment:
            parts.append(f"Apt {self.apartment}")
        parts.append(f"{self.city}, {self.state} {self.postal_code}")
        if self.country != "US":
            parts.append(self.country)
        return ", ".join(parts)


class Coordinate(NamedTuple):
    latitude: float
    longitude: float
    altitude: float = 0.0

    def is_valid(self) -> bool:
        return -90 <= self.latitude <= 90 and -180 <= self.longitude <= 180

    def to_dms(self) -> tuple[str, str]:
        def _fmt(deg: float, pos: str, neg: str) -> str:
            d = int(abs(deg))
            m = int((abs(deg) - d) * 60)
            s = round(((abs(deg) - d) * 60 - m) * 60, 2)
            direction = pos if deg >= 0 else neg
            return f"{d}°{m}'{s}\"{direction}"
        return _fmt(self.latitude, "N", "S"), _fmt(self.longitude, "E", "W")


class UserConfig(TypedDict, total=False):
    theme: str
    language: str
    notifications_enabled: bool
    items_per_page: int
