"""
Decorators with parameters, stacked usage, async wrapping, and return-type mutation.
Some have good docstrings, some bad, some none.
"""
import asyncio
import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])
logger = logging.getLogger(__name__)


# ── GOOD DOCSTRING ─────────────────────────────────────────────────────────────

def retry(times: int = 3, delay: float = 0.5, exceptions: tuple = (Exception,)):
    """Return a decorator that retries the wrapped callable on specified exceptions.

    Args:
        times: Maximum number of invocation attempts. Defaults to 3.
        delay: Seconds to sleep between attempts. Defaults to 0.5.
        exceptions: Tuple of exception types that trigger a retry.
            Defaults to ``(Exception,)``.

    Returns:
        Callable: A decorator that wraps a function with retry logic.

    Raises:
        Exception: Re-raises the last caught exception after all attempts
            are exhausted.
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(times):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    if attempt < times - 1:
                        time.sleep(delay)
            raise last_exc  # type: ignore[misc]
        return wrapper  # type: ignore[return-value]
    return decorator


# ── BAD DOCSTRING (vague / wrong) ─────────────────────────────────────────────

def deprecated(msg: str = ""):
    """Marks something as old.

    Do not use this.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            import warnings
            warnings.warn(
                f"{fn.__name__} is deprecated. {msg}",
                DeprecationWarning,
                stacklevel=2,
            )
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ── NO DOCSTRING ───────────────────────────────────────────────────────────────

def rate_limit(calls: int, period: float):
    _state: dict[str, Any] = {"count": 0, "window_start": time.monotonic()}

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            if now - _state["window_start"] >= period:
                _state["count"] = 0
                _state["window_start"] = now
            if _state["count"] >= calls:
                raise RuntimeError(
                    f"Rate limit exceeded: {calls} calls per {period}s"
                )
            _state["count"] += 1
            return fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


def timed(label: str | None = None):
    """Times a function call.

    Wrong: always returns None.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            t0 = time.perf_counter()
            result = fn(*a, **kw)
            elapsed = time.perf_counter() - t0
            tag = label or fn.__name__
            logger.debug("%s took %.4fs", tag, elapsed)
            return result
        return wrapper
    return decorator


# ── ASYNC WRAPPING DECORATOR ───────────────────────────────────────────────────

def log_calls(fn: F) -> F:
    if asyncio.iscoroutinefunction(fn):
        @functools.wraps(fn)
        async def async_wrapper(*args, **kwargs):
            logger.info("CALL %s args=%s kwargs=%s", fn.__name__, args, kwargs)
            result = await fn(*args, **kwargs)
            logger.info("RETURN %s -> %r", fn.__name__, result)
            return result
        return async_wrapper  # type: ignore[return-value]

    @functools.wraps(fn)
    def sync_wrapper(*args, **kwargs):
        logger.info("CALL %s args=%s kwargs=%s", fn.__name__, args, kwargs)
        result = fn(*args, **kwargs)
        logger.info("RETURN %s -> %r", fn.__name__, result)
        return result
    return sync_wrapper  # type: ignore[return-value]


# ── STACKED-DECORATOR TARGET (no docstring, tricky to analyse) ────────────────

@timed("batch_op")
@retry(times=2, delay=0.0)
@log_calls
def batch_transform(items: list, /, *, key: str, reverse: bool = False) -> list:
    if not isinstance(items, list):
        raise TypeError(f"Expected list, got {type(items).__name__}")
    return sorted(
        (i.get(key) for i in items if isinstance(i, dict) and key in i),
        reverse=reverse,
    )


# ── DECORATOR THAT MUTATES RETURN TYPE (return is always stringified) ──────────

def stringify_result(fn):
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        v = fn(*a, **kw)
        if v is None:
            return "null"
        return str(v)
    return wrapper


@stringify_result
def divide(a: float, b: float) -> float:  # actual runtime return is str
    if b == 0:
        return None  # type: ignore[return-value]
    return a / b
