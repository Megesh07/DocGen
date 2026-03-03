"""
DEMO SCENARIO 5 – Edge Cases.

Python decorators and the tricky NodeType detection they require.
  - @property / @<prop>.setter
  - @staticmethod
  - @classmethod
  - @functools.wraps  (meta-decorator – inner function should be documented)
  - @lru_cache
  - Custom class-based decorator

The tool correctly identifies each node type and adjusts the
generated docstring header (e.g., "property", "Static method.").
"""
from __future__ import annotations

import functools
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def retry(times: int = 3, exceptions: tuple = (Exception,)):
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


def log_calls(func: F) -> F:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"Calling {func.__name__} with args={args} kwargs={kwargs}")
        result = func(*args, **kwargs)
        print(f"{func.__name__} returned {result!r}")
        return result
    return wrapper  # type: ignore[return-value]


class Timer:
    def __call__(self, func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            import time
            start = time.perf_counter()
            result = func(*args, **kwargs)
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} took {elapsed:.4f}s")
            return result
        return wrapper  # type: ignore[return-value]


timer = Timer()


class Temperature:
    def __init__(self, celsius: float = 0.0) -> None:
        self._celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Temperature cannot go below absolute zero.")
        self._celsius = value

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        self.celsius = (value - 32) * 5 / 9

    @property
    def kelvin(self) -> float:
        return self._celsius + 273.15

    @staticmethod
    def from_kelvin(k: float) -> "Temperature":
        return Temperature(k - 273.15)

    @classmethod
    def absolute_zero(cls) -> "Temperature":
        return cls(-273.15)

    def __repr__(self) -> str:
        return f"Temperature({self._celsius}°C)"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Temperature):
            return NotImplemented
        return abs(self._celsius - other._celsius) < 1e-9
