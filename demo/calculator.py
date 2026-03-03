"""
Demo file 1 – NO DOCSTRINGS at all.

Scan this file to see coverage jump from 0% → 100% after generation.
All functions and methods have type hints but zero documentation.
"""
from __future__ import annotations


class Calculator:
    def __init__(self, precision: int = 2):
        self.precision = precision
        self._history: list[tuple] = []

    def add(self, a: float, b: float) -> float:
        result = round(a + b, self.precision)
        self._history.append(("add", a, b, result))
        return result

    def subtract(self, a: float, b: float) -> float:
        result = round(a - b, self.precision)
        self._history.append(("subtract", a, b, result))
        return result

    def multiply(self, a: float, b: float) -> float:
        result = round(a * b, self.precision)
        self._history.append(("multiply", a, b, result))
        return result

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        result = round(a / b, self.precision)
        self._history.append(("divide", a, b, result))
        return result

    def power(self, base: float, exponent: float) -> float:
        result = round(base ** exponent, self.precision)
        return result

    def get_history(self) -> list[tuple]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()


def percentage(value: float, total: float) -> float:
    if total == 0:
        raise ZeroDivisionError("Total cannot be zero.")
    return round((value / total) * 100, 2)


def compound_interest(principal: float, rate: float, times: int, years: int) -> float:
    return round(principal * (1 + rate / times) ** (times * years), 2)


def celsius_to_fahrenheit(celsius: float) -> float:
    return round((celsius * 9 / 5) + 32, 2)


def bmi(weight_kg: float, height_m: float) -> float:
    if height_m <= 0:
        raise ValueError("Height must be positive.")
    return round(weight_kg / height_m ** 2, 1)
