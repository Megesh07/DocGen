"""
Abstract base classes, mixins, properties, classmethods, context managers.
Intentional quality variation: some blocks documented, some not at all.
"""
from __future__ import annotations

import abc
import time
from typing import Any, ClassVar, Generic, Iterator, TypeVar

T = TypeVar("T")
V = TypeVar("V")


# ── ABSTRACT BASE ──────────────────────────────────────────────────────────────

class AbstractProcessor(abc.ABC, Generic[T, V]):
    """Abstract base for all pipeline processors.

    Subclasses must implement :meth:`process` and :meth:`validate`.
    Provides a default :meth:`run` entry-point that validates then processes.

    Type Parameters:
        T: Input type accepted by :meth:`process`.
        V: Output type produced by :meth:`process`.
    """

    _registry: ClassVar[dict[str, type]] = {}
    _version: ClassVar[str] = "0.0"

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        AbstractProcessor._registry[cls.__name__] = cls

    @abc.abstractmethod
    def process(self, item: T) -> V:
        ...

    @abc.abstractmethod
    def validate(self, item: T) -> bool:
        ...

    def run(self, item: T) -> V | None:
        if not self.validate(item):
            return None
        return self.process(item)

    @classmethod
    def from_name(cls, name: str) -> AbstractProcessor:
        """Instantiate a registered subclass by its class name.

        Args:
            name: The class name as registered in ``_registry``.

        Returns:
            AbstractProcessor: A new instance of the named subclass.

        Raises:
            KeyError: If ``name`` is not in the registry.
        """
        klass = cls._registry[name]
        return klass()

    @staticmethod
    def supported_versions() -> list[str]:
        return ["1.0", "1.1", "2.0"]


# ── CONFIGURABLE MIXIN ─────────────────────────────────────────────────────────

class Configurable:
    """Mixin that adds a key-value configuration store to any class."""

    def __init__(self, **cfg: Any) -> None:
        self._cfg: dict[str, Any] = dict(cfg)

    def configure(self, **kwargs: Any) -> None:
        self._cfg.update(kwargs)

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._cfg.get(key, default)

    @property
    def config_keys(self) -> list[str]:
        return list(self._cfg.keys())


# ── LEVEL-2 CONCRETE (no docstring) ───────────────────────────────────────────

class BaseTransformer(Configurable, AbstractProcessor[Any, Any]):

    _transform_count: int = 0

    def __init__(self, strict: bool = False, **cfg: Any) -> None:
        Configurable.__init__(self, **cfg)
        self.strict = strict
        self._errors: list[str] = []

    def validate(self, item: Any) -> bool:
        if self.strict and item is None:
            self._errors.append("null input rejected in strict mode")
            return False
        return True

    def _internal_reset(self) -> None:
        self._errors.clear()
        BaseTransformer._transform_count = 0

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} strict={self.strict} errors={len(self._errors)}>"

    def __len__(self) -> int:
        return BaseTransformer._transform_count


# ── LEVEL-3 CONCRETE WITH PROPERTY + CONTEXT MANAGER (bad docstring) ──────────

class FieldTransformer(BaseTransformer):
    """Transforms fields. Use set_field to set fields."""

    def __init__(self, field_map: dict[str, str] | None = None, **cfg: Any) -> None:
        super().__init__(**cfg)
        self._field_map: dict[str, str] = field_map or {}
        self.__raw: dict[str, Any] = {}

    @property
    def field_map(self) -> dict[str, str]:
        return dict(self._field_map)

    @field_map.setter
    def field_map(self, new_map: dict[str, str]) -> None:
        if not isinstance(new_map, dict):
            raise TypeError("field_map must be a dict")
        self._field_map = new_map
        self.__raw["_last_set"] = time.time()  # dynamic attribute side-effect

    def process(self, item: Any) -> dict:
        if not isinstance(item, dict):
            if self.strict:
                raise ValueError(f"Expected dict, got {type(item)}")
            return {}
        out = {}
        for src, dst in self._field_map.items():
            if src in item:
                out[dst] = item[src]
        BaseTransformer._transform_count += 1
        return out

    def __enter__(self) -> FieldTransformer:
        self._internal_reset()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None:
            self._errors.append(str(exc_val))
        return False  # do not suppress exceptions

    def __iter__(self) -> Iterator[tuple[str, str]]:
        return iter(self._field_map.items())

    def __call__(self, item: Any) -> dict:
        return self.run(item) or {}


# ── CONFIGURABLE PROPERTY WITH SIDE EFFECTS ────────────────────────────────────

class CachedProcessor(FieldTransformer):

    def __init__(self, ttl: float = 30.0, **cfg: Any) -> None:
        super().__init__(**cfg)
        self._cache: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl

    @property
    def ttl(self) -> float:
        return self._ttl

    @ttl.setter
    def ttl(self, value: float) -> None:
        if value <= 0:
            raise ValueError("ttl must be positive")
        self._ttl = value
        self._cache.clear()

    def process(self, item: Any) -> dict:
        key = str(item)
        now = time.monotonic()
        if key in self._cache:
            val, ts = self._cache[key]
            if now - ts < self._ttl:
                return val
        result = super().process(item)
        self._cache[key] = (result, now)
        return result

    def bust(self, key: str | None = None) -> int:
        if key is None:
            n = len(self._cache)
            self._cache.clear()
            return n
        return int(self._cache.pop(key, (None, None))[0] is not None)
