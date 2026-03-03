"""
Async pipeline: async generators, async context managers, async functions with
complex await patterns. No docstrings on any of these — maximum pain for generators.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Callable


# ── ASYNC GENERATOR ────────────────────────────────────────────────────────────

async def stream_records(
    source: AsyncIterator[bytes],
    *,
    delimiter: bytes = b"\n",
    max_size: int = 65536,
) -> AsyncGenerator[dict, None]:
    buf = b""
    async for chunk in source:
        buf += chunk
        while delimiter in buf:
            line, buf = buf.split(delimiter, 1)
            if len(line) > max_size:
                continue
            try:
                import json
                yield json.loads(line)
            except Exception:
                pass
    if buf.strip():
        try:
            import json
            yield json.loads(buf)
        except Exception:
            pass


# ── ASYNC CONTEXT MANAGER (class-based) ───────────────────────────────────────

class ManagedSession:
    """Async context manager that opens and closes a logical processing session.

    On entry, acquires a semaphore slot and records the start time.
    On exit, releases the slot and logs total elapsed time.

    Attributes:
        name: Human-readable session label.
        timeout: Maximum hold time in seconds.
    """

    _global_sem: asyncio.Semaphore | None = None

    def __init__(self, name: str, *, timeout: float = 30.0, max_concurrent: int = 10) -> None:
        self.name = name
        self.timeout = timeout
        if ManagedSession._global_sem is None:
            ManagedSession._global_sem = asyncio.Semaphore(max_concurrent)
        self._start: float | None = None

    async def __aenter__(self) -> ManagedSession:
        assert ManagedSession._global_sem is not None
        await asyncio.wait_for(
            ManagedSession._global_sem.acquire(), timeout=self.timeout
        )
        self._start = asyncio.get_event_loop().time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> bool:
        assert ManagedSession._global_sem is not None
        ManagedSession._global_sem.release()
        return False


# ── @asynccontextmanager VARIANT ───────────────────────────────────────────────

@asynccontextmanager
async def rate_window(bucket: str, limit: int, window: float):
    _counters: dict[str, list[float]] = {}
    now = asyncio.get_event_loop().time()
    hits = _counters.setdefault(bucket, [])
    hits[:] = [t for t in hits if now - t < window]
    if len(hits) >= limit:
        raise PermissionError(f"Rate limit exceeded for '{bucket}'")
    hits.append(now)
    yield len(hits)


# ── ASYNC FUNCTION: multiple awaits + conditional error ───────────────────────

async def fetch_and_merge(
    primary_url: str,
    fallback_url: str,
    fetch_fn: Callable[[str], Any],
    *,
    merge_key: str = "id",
) -> dict[str, Any]:
    try:
        primary_data = await fetch_fn(primary_url)
    except Exception:
        primary_data = {}

    try:
        fallback_data = await fetch_fn(fallback_url)
    except Exception:
        fallback_data = {}

    merged: dict[str, Any] = {}
    for record in (primary_data if isinstance(primary_data, list) else []):
        k = record.get(merge_key)
        if k is not None:
            merged[k] = record

    for record in (fallback_data if isinstance(fallback_data, list) else []):
        k = record.get(merge_key)
        if k is not None and k not in merged:
            merged[k] = record

    return merged


# ── ASYNC FUNCTION: implicit None return ──────────────────────────────────────

async def drain(queue: asyncio.Queue, handler: Callable[[Any], Any]) -> None:
    while not queue.empty():
        item = await queue.get()
        try:
            await handler(item) if asyncio.iscoroutinefunction(handler) else handler(item)
        finally:
            queue.task_done()


# ── NESTED ASYNC + CLOSURE ─────────────────────────────────────────────────────

def make_retry_fetch(fetch_fn: Callable, retries: int = 3):
    async def _inner(url: str) -> Any:
        last: Exception | None = None
        for attempt in range(retries):
            try:
                return await fetch_fn(url)
            except Exception as exc:
                last = exc
                await asyncio.sleep(0.1 * (attempt + 1))
        raise RuntimeError(f"All {retries} attempts failed for {url!r}") from last
    return _inner
