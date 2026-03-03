"""Core package: abstract bases, engine, deep inheritance."""
from .base import AbstractProcessor, Configurable
from .engine import DocumentEngine

__all__ = ["AbstractProcessor", "Configurable", "DocumentEngine"]
