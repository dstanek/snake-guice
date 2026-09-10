"""Scopes for the FastAPI snake-guice example.

`FastAPIRequestScope` caches per-request bindings (e.g. database sessions) in
a `ContextVar`-backed dict, since FastAPI has nothing like `cherrypy.request`
to hang state off of. `PerAppSingleton` is a from-scratch, minimal
reimplementation of the same idea behind `scopes.SINGLETON` - a worked example
of the `Scope` protocol (see `docs/source/extending.md`), not a workaround for
anything `SINGLETON` gets wrong.
"""

from contextvars import ContextVar
from typing import Any, TypeVar

from sqlalchemy.orm import Session

from snakeguice.interfaces import Key, Provider
from snakeguice.providers import create_instance_provider

T = TypeVar("T")

_request_cache: ContextVar[dict[Key, Any] | None] = ContextVar(
    "fastapi_request_cache", default=None
)


def reset_request_scope() -> dict[Key, Any]:
    """Start a fresh per-request cache. Call once per incoming request."""
    cache: dict[Key, Any] = {}
    _request_cache.set(cache)
    return cache


def close_request_sessions(cache: dict[Key, Any]) -> None:
    """Commit (or roll back) and close any sessions cached during a request."""
    for value in cache.values():
        if isinstance(value, Session):
            try:
                value.commit()
            except Exception:
                value.rollback()
            finally:
                value.close()


class FastAPIRequestScope:
    """Per-request cache keyed by snake-guice `Key`, backed by a `ContextVar`.

    CherryPy's request scope (`examples/cherrypy/scopes.py`) keys off of
    `cherrypy.request`, which has no FastAPI equivalent. This also returns a
    `Provider[T]` directly, matching `_NoScope`/`_Singleton`'s contract —
    CherryPy's `create_instance_provider(RequestProvider())()` instead
    returns a `Provider[Provider[T]]`, which appears to be an unexercised bug
    in that (untested) example.
    """

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        class RequestProvider:
            def get(self) -> T:
                cache = _request_cache.get()
                if cache is None:
                    return provider.get()
                if key not in cache:
                    cache[key] = provider.get()
                return cache[key]

        return RequestProvider()


FASTAPI_REQUEST_SCOPE = FastAPIRequestScope()


class PerAppSingleton:
    """A minimal from-scratch `scopes.SINGLETON`-alike: caches one instance
    per `Key`, on `self`.

    `scopes.SINGLETON` already does exactly this per-injector, so this isn't
    needed to keep `MetricsModule`'s state from leaking between `create_app()`
    calls - it exists here as a small, self-contained example of the `Scope`
    protocol (see `docs/source/extending.md`), built the same way `SINGLETON`
    itself is. Because the cache lives on `self` rather than on a `Binding`,
    reusing one `PerAppSingleton()` instance across bindings or modules shares
    its cache between them - a lifetime `SINGLETON` can't express, since
    `SINGLETON`'s cache is always tied to a single `Binding`.
    """

    def __init__(self) -> None:
        self._cache: dict[Key, Any] = {}

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        if key not in self._cache:
            self._cache[key] = provider.get()
        return create_instance_provider(self._cache[key])()
