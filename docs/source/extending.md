# Extending snake-guice

Most of snake-guice's behavior is built from two small, swappable pieces:
`Provider`s decide *how* an instance is built, and `Scope`s decide *how long*
it's kept around. Both are plain Python objects, so writing your own is how
you plug new behavior into the same `get_instance`/`get_provider` machinery
everything else uses.

## Custom Providers

A provider is any object with a `get()` method. See [Using
Providers](using_providers.md) for `to_provider=`, the `@provides` decorator,
and how providers interact with scopes - this page focuses on the other half:
writing your own `Scope`.

## Custom Scopes

A scope is any object with a `scope(key, provider)` method. It takes an
*unscoped* provider and returns the provider that's actually used:

```python
class Scope(Protocol):
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]: ...
```

`scopes.NO_SCOPE` (the default) returns `provider` unchanged, so `.get()` runs
on every resolution. `scopes.SINGLETON` calls `provider.get()` once per
injector, caches the result, and returns a provider for the cached instance
from then on - see [Scopes](userguide.md#scopes) in the User Guide for how
that per-injector caching (and `scopes.THREAD_LOCAL`'s per-thread caching)
works and how it interacts with `create_child()`.

Writing your own scope follows the same shape. Here's a `RequestScope` that
caches one instance per `Key` until `reset()` is called - the shape you'd
reach for when a lifetime doesn't fit `SINGLETON`'s per-injector cache or
`THREAD_LOCAL`'s per-thread one:

```python
from typing import Any

from snakeguice import providers
from snakeguice.interfaces import Key, Provider


class RequestScope:
    """Caches one instance per Key until reset() is called."""

    def __init__(self) -> None:
        self._cache: dict[Key, Provider[Any]] = {}

    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        cached = self._cache.get(key)
        if cached is None:
            instance = provider.get()
            cached = self._cache[key] = providers.create_instance_provider(instance)()
        return cached

    def reset(self) -> None:
        self._cache.clear()
```

```{note}
This cache lives on `self`, so it's one cache shared by every caller of this
particular `RequestScope` instance, with no lock guarding it - two threads can
both miss the cache and construct twice. For a per-request (or per-task) cache
that's actually safe under concurrent threads or `asyncio`, see [Per-request
or per-task scope](concurrency.md#per-request-or-per-task-scope).
```

Bind to it with `in_scope=`, just like the built-in scopes:

```python
from snakeguice import create_injector
from snakeguice.interfaces import Binder


class IRequestContext:
    """Interface for per-request state."""


class RequestContext(IRequestContext):
    pass


request_scope = RequestScope()


class WebModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IRequestContext, to=RequestContext, in_scope=request_scope)


injector = create_injector([WebModule()])

ctx = injector.get_instance(IRequestContext)
assert injector.get_instance(IRequestContext) is ctx

request_scope.reset()
assert injector.get_instance(IRequestContext) is not ctx
```

```{note}
Unlike `scopes.SINGLETON`, `request_scope` here is an instance you create and
hold onto yourself. Its cache isn't shared with any other binding or
injector, so `reset()` only affects bindings that use this particular
`RequestScope`.
```

## Custom Module Types

`Module.run_configure(binder)` is the hook `Injector` calls instead of
`configure(binder)` directly - the default implementation calls
`self.configure(binder)` and then binds the module's `@provides` methods on
that same binder. Overriding `run_configure` lets a `Module` subclass
change the binder, or do other setup, before its own `configure()` runs.

`PrivateModule` is the built-in example of this pattern: its `run_configure`
routes `configure()` through a private binder instead of a private injector -
the private injector itself is built later, once the enclosing injector
finishes configuring - and `expose()` re-binds selected interfaces on the
*original* binder so the parent injector can see them. See
[Private Modules](private_modules.md) for the full walkthrough.
