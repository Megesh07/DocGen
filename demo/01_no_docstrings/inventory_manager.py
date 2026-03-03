"""
DEMO SCENARIO 1 – Zero-docstring file.

Inventory management system with classes and business logic.
No docstrings exist. Run the scanner and observe full coverage
transform from 0 % → 100 % after generation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Product:
    sku: str
    name: str
    price: float
    quantity: int = 0
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def is_in_stock(self) -> bool:
        return self.quantity > 0

    def total_value(self) -> float:
        return round(self.price * self.quantity, 2)

    def apply_discount(self, percent: float) -> float:
        if not 0 <= percent <= 100:
            raise ValueError(f"Discount percent must be 0–100, got {percent}.")
        discounted = self.price * (1 - percent / 100)
        return round(discounted, 2)


class Inventory:
    def __init__(self):
        self._products: dict[str, Product] = {}

    def add_product(self, product: Product) -> None:
        if product.sku in self._products:
            raise KeyError(f"SKU '{product.sku}' already exists.")
        self._products[product.sku] = product

    def remove_product(self, sku: str) -> Product:
        if sku not in self._products:
            raise KeyError(f"SKU '{sku}' not found.")
        return self._products.pop(sku)

    def get_product(self, sku: str) -> Optional[Product]:
        return self._products.get(sku)

    def restock(self, sku: str, quantity: int) -> None:
        product = self._products.get(sku)
        if product is None:
            raise KeyError(f"SKU '{sku}' not found.")
        if quantity <= 0:
            raise ValueError("Restock quantity must be positive.")
        product.quantity += quantity

    def sell(self, sku: str, quantity: int) -> float:
        product = self._products.get(sku)
        if product is None:
            raise KeyError(f"SKU '{sku}' not found.")
        if product.quantity < quantity:
            raise ValueError(f"Insufficient stock: need {quantity}, have {product.quantity}.")
        product.quantity -= quantity
        return round(product.price * quantity, 2)

    def total_inventory_value(self) -> float:
        return round(sum(p.total_value() for p in self._products.values()), 2)

    def low_stock_alert(self, threshold: int = 5) -> list[Product]:
        return [p for p in self._products.values() if p.quantity <= threshold]

    def search_by_category(self, category: str) -> list[Product]:
        return [p for p in self._products.values() if p.category.lower() == category.lower()]

    def most_valuable_products(self, top_n: int = 5) -> list[Product]:
        return sorted(self._products.values(), key=lambda p: p.total_value(), reverse=True)[:top_n]

    def __len__(self) -> int:
        return len(self._products)

    def __contains__(self, sku: str) -> bool:
        return sku in self._products
