"""
Demo file 1 — Clean Slate
=========================
All functions and classes are fully type-annotated but have ZERO docstrings.
Expected model behaviour: maximum coverage, every item AUTO_APPLY.

Covers:
  - Module-level functions with typed params and return
  - Class with __init__, instance methods, @staticmethod, @classmethod
  - async def function
  - Function raising an exception
  - Function with *args / **kwargs (typed via tuple/dict)
"""

from __future__ import annotations

import math
from typing import Optional


# ── Module-level functions ───────────────────────────────────────────────────

def add(a: float, b: float) -> float:
    return a + b


def divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ZeroDivisionError("denominator must not be zero")
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True


def format_currency(amount: float, symbol: str = "$", decimals: int = 2) -> str:
    return f"{symbol}{amount:.{decimals}f}"


def find_median(numbers: list[float]) -> Optional[float]:
    if not numbers:
        return None
    sorted_nums = sorted(numbers)
    mid = len(sorted_nums) // 2
    if len(sorted_nums) % 2 == 0:
        return (sorted_nums[mid - 1] + sorted_nums[mid]) / 2.0
    return sorted_nums[mid]


async def fetch_exchange_rate(base: str, target: str) -> float:
    # Simulated async call; returns a placeholder rate
    rates = {"USD_EUR": 0.92, "EUR_GBP": 0.86, "USD_GBP": 0.79}
    return rates.get(f"{base}_{target}", 1.0)


# ── Class with full variety of methods ──────────────────────────────────────

class BankAccount:

    INTEREST_RATE: float = 0.035  # 3.5 % annual

    def __init__(self, owner: str, initial_balance: float = 0.0) -> None:
        self.owner = owner
        self._balance = initial_balance
        self._transactions: list[float] = []

    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("deposit amount must be positive")
        self._balance += amount
        self._transactions.append(amount)
        return self._balance

    def withdraw(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("withdrawal amount must be positive")
        if amount > self._balance:
            raise ValueError("insufficient funds")
        self._balance -= amount
        self._transactions.append(-amount)
        return self._balance

    def apply_interest(self) -> float:
        interest = self._balance * self.INTEREST_RATE
        self._balance += interest
        return interest

    def get_statement(self) -> list[float]:
        return list(self._transactions)

    @property
    def balance(self) -> float:
        return self._balance

    @staticmethod
    def validate_amount(amount: float) -> bool:
        return isinstance(amount, (int, float)) and amount > 0

    @classmethod
    def from_dict(cls, data: dict) -> BankAccount:
        return cls(owner=data["owner"], initial_balance=data.get("balance", 0.0))
