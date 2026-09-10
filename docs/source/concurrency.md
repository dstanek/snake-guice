# Threads and Async

An `Injector` is safe to call from multiple threads, or from multiple
concurrent `asyncio` tasks: `get_instance()`'s in-progress resolution state -
cycle detection, and which binding a scope is currently caching against - is
tracked per-thread and per-task, not on the `Injector` itself, so unrelated
resolutions running at the same time can't corrupt each other's bookkeeping.
That covers snake-guice's own bookkeeping only. The objects it builds, and any
provider or `@provides` method that does I/O or touches shared mutable state,
are still yours to make safe. This page is about how to structure a threaded
or `asyncio` application around that guarantee, and where it stops.

## Threaded applications

Build the `Injector` once, at startup, and share it across worker threads - a
`ThreadPoolExecutor`, a threaded WSGI server's worker pool - resolving
instances per request on whichever thread handles it:

```python
from concurrent.futures import ThreadPoolExecutor

from snakeguice import create_injector
from snakeguice.interfaces import Binder


class IEngine:
    """Interface for an engine."""


class SmallBlockEngine(IEngine):
    pass


class AutoModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)


injector = create_injector([AutoModule()])


def handle_request(_: int) -> None:
    engine = injector.get_instance(IEngine)
    assert isinstance(engine, SmallBlockEngine)


with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(handle_request, range(50)))
```

Which `in_scope=` to reach for depends on what should be shared across those
threads:

| Scope | Lifetime | Use it for |
| --- | --- | --- |
| `scopes.NO_SCOPE` (default) | fresh instance every resolution | stateless or cheap-to-build collaborators |
| `scopes.SINGLETON` | one instance per binding, per injector | shared services that are safe to use from any thread |
| `scopes.THREAD_LOCAL` | one instance per binding, per thread | non-thread-safe clients/sessions reused on one thread |
| a `ContextVar`-backed custom scope | one instance per binding, per request/task | per-request state, in threads or `asyncio` alike (see [below](#per-request-or-per-task-scope)) |

Only a binding's *first* resolution takes a lock: `scopes.SINGLETON`
guarantees exactly one construction however many threads race to resolve it,
and every later call returns the cached instance without locking. Keep
singleton constructors cheap, or resolve the expensive ones eagerly right
after `create_injector()`, so construction never lands on a request's critical
path. And never block inside a singleton constructor waiting on another thread
that itself resolves singletons: that can deadlock on the construction lock
rather than merely run slowly.

```{warning}
`scopes.THREAD_LOCAL` never resets itself. Threads in a pool are reused
across many requests, so a `THREAD_LOCAL` instance outlives whatever request
first built it and gets handed to the next request that lands on the same
thread. It's the right tool for "must not cross threads," not for "one per
request" - see [Per-request or per-task scope](#per-request-or-per-task-scope)
below for that.
```

## Async applications

Calling `get_instance()` from an `async def` handler is fine, and just as
safe across concurrently running tasks as across threads: it's a plain
synchronous call, so it blocks the event loop only for as long as
construction takes - the same as any other sync call in a handler would.

There's no async provider: `Provider.get()`, `to_provider=` classes, and
`@provides` methods are all synchronous, and nothing inside `get_instance()`
ever awaits. An async resource that needs `await` to build - an async
database pool, an `httpx.AsyncClient` - can't be constructed by a provider;
build it during the application's startup (FastAPI's `lifespan`, or
equivalent) and bind the already-built object with `to_instance=`:

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request

from snakeguice import create_injector
from snakeguice.interfaces import Binder


class ClientModule:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def configure(self, binder: Binder) -> None:
        binder.bind(httpx.AsyncClient, to_instance=self._client)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient() as client:
        app.state.injector = create_injector([ClientModule(client)])
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/ping")
async def ping(request: Request) -> bool:
    client = request.app.state.injector.get_instance(httpx.AsyncClient)
    return isinstance(client, httpx.AsyncClient)
```

The injector has no shutdown hooks of its own. Close what you opened in
`lifespan` during that same `lifespan`'s shutdown half, or in middleware - see
`request_scope_middleware` in
`examples/fastapi_tasks/fastapi_snakeguice/main.py`, which closes each
request's database sessions via `close_request_sessions` after the response
is sent.

### Per-request or per-task scope

```{warning}
`scopes.THREAD_LOCAL` is per **thread**, not per task. Every task on an event
loop runs on the same thread, so a `THREAD_LOCAL` binding hands *every*
concurrently running task the same instance - rarely what an async
application actually wants.
```

For one instance per request or per task, cache in a `ContextVar` instead. A
`ContextVar` is scoped to the current task on the loop thread rather than to
the OS thread, so the cache is stable within one request and distinct across
concurrently running ones - and the same scope works unchanged under a
threaded server, since each thread has its own context too:

```python
import asyncio
from contextvars import ContextVar
from typing import Any

from snakeguice import create_injector, providers
from snakeguice.interfaces import Binder, Key, Provider, T

_cache: ContextVar[dict[Key, Any] | None] = ContextVar("request_cache", default=None)


class ContextScope:
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        cache = _cache.get()
        if cache is None:
            raise RuntimeError("no active request")
        if key not in cache:
            cache[key] = provider.get()
        return providers.create_instance_provider(cache[key])()


class IEngine:
    """Interface for an engine."""


class SmallBlockEngine(IEngine):
    pass


class AutoModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine, in_scope=ContextScope())


injector = create_injector([AutoModule()])


async def handle_request() -> IEngine:
    token = _cache.set({})  # one cache per request; middleware is the usual home
    try:
        engine = injector.get_instance(IEngine)
        await asyncio.sleep(0)  # let another request run in between
        assert injector.get_instance(IEngine) is engine  # stable within the request
        return engine
    finally:
        _cache.reset(token)


async def main() -> None:
    first, second = await asyncio.gather(handle_request(), handle_request())
    assert first is not second  # distinct across concurrent requests


asyncio.run(main())
```

`FastAPIRequestScope` in `examples/fastapi_tasks/fastapi_snakeguice/scopes.py`
is the fuller version this is adapted from; its `main.py` middleware is where
the cache is set and reset around each request, and where that request's
sessions are closed.

### Resolving off the event loop

For a constructor that does blocking I/O, run the resolution in a worker
thread with `asyncio.to_thread`. It copies the calling task's context, so a
`ContextVar`-backed scope set on the loop thread is still visible from inside
the worker. `loop.run_in_executor` does not copy the context, so the same
scope looks unset there:

```python
engine = await asyncio.to_thread(injector.get_instance, IEngine)  # sees the request cache
await loop.run_in_executor(None, injector.get_instance, IEngine)  # RuntimeError
```

## Limitations

Two edge cases pre-date this thread/async safety work and aren't specific to
concurrency:

- A provider that re-enters `get_instance()` for the *same* singleton binding
  it's currently constructing, through a `create_child()` injector, still
  constructs it twice - the child's `(injector, key)` frame is different from
  the parent's, so it isn't recognized as the same in-flight resolution. The
  same re-entry on the *same* injector raises `CircularDependencyError`
  instead, since there the frame does match. No lock can prevent a thread from
  re-entering itself, so this is a reentrancy limitation, not a race.
- A dependency cycle that crosses a fresh `create_child()` on every hop isn't
  detected as `CircularDependencyError`, for the same reason: each hop is
  recorded against a different injector, so the chain never repeats an
  `(injector, key)` pair. It surfaces as Python's own `RecursionError`
  instead.
