"""
DEMO SCENARIO 1 – Zero-docstring file.

This file intentionally has NO docstrings anywhere.
Point the tool at this file and watch it auto-generate
Google-style docstrings for every function and method.
"""


class Calculator:
    def __init__(self, precision: int = 2):
        self.precision = precision
        self._history: list = []

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
            raise ZeroDivisionError("Division by zero is not allowed.")
        result = round(a / b, self.precision)
        self._history.append(("divide", a, b, result))
        return result

    def power(self, base: float, exponent: float) -> float:
        result = round(base ** exponent, self.precision)
        self._history.append(("power", base, exponent, result))
        return result

    def sqrt(self, value: float) -> float:
        if value < 0:
            raise ValueError("Cannot take square root of a negative number.")
        result = round(value ** 0.5, self.precision)
        return result

    def get_history(self) -> list:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    def last_result(self) -> float | None:
        if not self._history:
            return None
        return self._history[-1][-1]


def percentage(value: float, total: float) -> float:
    if total == 0:
        raise ZeroDivisionError("Total cannot be zero when computing percentage.")
    return round((value / total) * 100, 2)


def compound_interest(principal: float, rate: float, times: int, years: int) -> float:
    return round(principal * (1 + rate / times) ** (times * years), 2)


def celsius_to_fahrenheit(celsius: float) -> float:
    return round((celsius * 9 / 5) + 32, 2)


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    return round((fahrenheit - 32) * 5 / 9, 2)


def bmi(weight_kg: float, height_m: float) -> float:
    if height_m <= 0:
        raise ValueError("Height must be positive.")
    return round(weight_kg / (height_m ** 2), 1)
