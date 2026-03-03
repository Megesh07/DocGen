"""
DEMO SCENARIO 4 – Complex Patterns.

Async I/O patterns. The tool's AST parser correctly detects
``async def`` and flags the NodeType as ASYNC_FUNCTION, generating
an ``Async function.`` note in the summary and a proper Coroutine
return hint in the docstring.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Callable


async def fetch_url(url: str, timeout: float = 10.0) -> dict:
    await asyncio.sleep(0)   # stub: represents real HTTP call
    return {"url": url, "status": 200, "body": ""}


async def fetch_all(urls: list[str], concurrency: int = 5) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _bounded_fetch(u: str) -> dict:
        async with semaphore:
            return await fetch_url(u)

    return await asyncio.gather(*[_bounded_fetch(u) for u in urls])


async def retry(
    coro_fn: Callable[..., Any],
    *args: Any,
    attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    **kwargs: Any,
) -> Any:
    current_delay = delay
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return await coro_fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < attempts:
                await asyncio.sleep(current_delay)
                current_delay *= backoff
    raise RuntimeError(f"All {attempts} attempts failed.") from last_exc


async def stream_lines(filepath: str) -> AsyncIterator[str]:
    with open(filepath, encoding="utf-8") as fh:
        for line in fh:
            yield line.rstrip("\n")
            await asyncio.sleep(0)


async def timeout_guard(coro: Any, seconds: float) -> Any:
    try:
        return await asyncio.wait_for(coro, timeout=seconds)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation exceeded {seconds}s timeout.")


async def rate_limited_tasks(
    tasks: list[Callable],
    max_per_second: int = 10,
) -> list[Any]:
    results: list[Any] = []
    interval = 1.0 / max_per_second
    for task in tasks:
        results.append(await task())
        await asyncio.sleep(interval)
    return results
