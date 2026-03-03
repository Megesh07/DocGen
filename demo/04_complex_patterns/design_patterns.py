"""
DEMO SCENARIO 4 – Complex Patterns.

OOP design patterns. Demonstrates how the tool documents
abstract base classes, class methods, static methods, properties,
and the ``__dunder__`` protocol methods correctly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any, ClassVar, Optional


class Singleton:
    _instance: ClassVar[Optional["Singleton"]] = None

    def __new__(cls) -> "Singleton":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None


class Observable(ABC):
    def __init__(self) -> None:
        self._listeners: dict[str, list] = {}

    def on(self, event: str, callback: Any) -> None:
        self._listeners.setdefault(event, []).append(callback)

    def off(self, event: str, callback: Any) -> None:
        listeners = self._listeners.get(event, [])
        if callback in listeners:
            listeners.remove(callback)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        for listener in self._listeners.get(event, []):
            listener(*args, **kwargs)

    @abstractmethod
    def validate(self) -> bool:
        ...


class Repository(ABC):
    @abstractmethod
    def find_by_id(self, entity_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def save(self, entity: dict) -> dict:
        ...

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        ...

    def find_or_raise(self, entity_id: int) -> dict:
        entity = self.find_by_id(entity_id)
        if entity is None:
            raise KeyError(f"Entity with id={entity_id} not found.")
        return entity


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._store: dict[int, dict] = {}
        self._counter: int = 0

    def find_by_id(self, entity_id: int) -> Optional[dict]:
        return self._store.get(entity_id)

    def save(self, entity: dict) -> dict:
        if "id" not in entity:
            self._counter += 1
            entity = {**entity, "id": self._counter}
        self._store[entity["id"]] = entity
        return entity

    def delete(self, entity_id: int) -> bool:
        return bool(self._store.pop(entity_id, None))

    @staticmethod
    def from_list(records: list[dict]) -> "InMemoryRepository":
        repo = InMemoryRepository()
        for record in records:
            repo.save(record)
        return repo

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(count={len(self._store)})"
