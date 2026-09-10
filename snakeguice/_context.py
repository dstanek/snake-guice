"""Ambient state shared by the injector and scopes.

Resolution re-enters the public API through user code -- a `to_provider=`, an
`@provides` method, a custom `Scope` -- so there is no parameter to thread
this through. `ContextVar` rather than `threading.local` to stay correct per
asyncio task as well as per thread.
"""

from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from snakeguice.binder import Binding, Key
    from snakeguice.injector import Injector

resolving: "ContextVar[tuple[tuple[Injector, Key], ...]]" = ContextVar(
    "snakeguice_resolving", default=()
)
"""In-flight resolution chain, as `(injector, key)` frames.

The injector is part of the frame because the same `Key` legitimately nests
across a `PrivateModule.expose()` boundary (robot legs); keying on `Key`
alone would flag that as a cycle.
"""

current_binding: "ContextVar[Binding | None]" = ContextVar(
    "snakeguice_current_binding", default=None
)
"""The `Binding` being handed to `Scope.scope()`.

`scope(key, provider)` is a public extension point and cannot grow a
parameter, so scopes that cache per injector read the binding here. Bindings
are created once per `bind()` and shared down a `create_child()` chain, which
is what makes a parent and child share a singleton while unrelated injectors
do not.
"""
