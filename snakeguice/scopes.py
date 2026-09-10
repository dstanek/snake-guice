"""Scopes that can be used in the binding process."""

# pylint: disable-msg=C0111

import threading
from typing import Any, Dict, cast

from snakeguice import providers
from snakeguice._context import current_binding
from snakeguice.interfaces import Key, Provider, T


class _NoScope:
    """A default scope returns the same provider that gets passed in.

    This is internally used and will probably never be directly used in
    a module.
    """

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        return provider


class Singleton:
    """Caches one instance per binding.

    The cache lives on the ``Binding`` being resolved, found via
    ``_context.current_binding``. Bindings are shared down a
    ``create_child()`` chain, so a parent and its children share an instance
    while unrelated injectors -- even both using the exported ``SINGLETON``
    -- do not, and the cache is reclaimed with its injector rather than
    accumulating on a process-global scope object. Construction is likewise
    guarded by a lock on the ``Binding``, so building one singleton never
    waits on another, unrelated one.

    Falls back to a ``key``-keyed dict when called outside
    ``Injector.get_instance()``, where there is no ambient binding.
    """

    def __init__(self) -> None:
        self._cached_provider_map: Dict[Key, Provider[Any]] = {}
        self._lock = threading.RLock()

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        binding = current_binding.get()

        def get_cached() -> Provider[Any] | None:
            if binding is not None:
                return cast("Provider[Any] | None", binding.scope_cache)
            return self._cached_provider_map.get(key)

        def set_cached(instance_provider: Provider[Any]) -> None:
            if binding is not None:
                binding.scope_cache = instance_provider
            else:
                self._cached_provider_map[key] = instance_provider

        cached_provider = get_cached()
        if cached_provider is None:
            # RLock, not Lock: with a per-binding lock, the only same-thread
            # re-entry is a provider re-entering get_instance() for this same
            # binding through a child injector (which inherits it). An RLock
            # turns that into the double construction the user guide documents
            # instead of a deadlock.
            lock = binding.scope_lock if binding is not None else self._lock
            with lock:
                cached_provider = get_cached()
                if cached_provider is None:
                    instance = provider.get()
                    cached_provider = providers.create_instance_provider(instance)()
                    set_cached(cached_provider)
        return cached_provider


class ThreadLocalScope:
    """Like ``Singleton``, but one instance per thread.

    For state that must not cross threads -- a non-thread-safe client, a
    session -- but should survive repeated resolutions on one thread. Each
    binding's cache is a ``threading.local()`` stored on the ``Binding``, for
    the same lifetime reason as ``Singleton``.

    Only the owning thread touches its own slot, so the cached values need no
    lock; creating a binding's ``threading.local()`` is a shared first write
    and does, guarded by that binding's ``scope_lock``.
    """

    def __init__(self) -> None:
        # Only used when called directly, without an ambient Binding.
        self._local = threading.local()

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        binding = current_binding.get()
        if binding is None:
            return self._scope_in(self._local, key, provider)

        local = cast("threading.local | None", binding.scope_cache)
        if local is None:
            with binding.scope_lock:
                local = cast("threading.local | None", binding.scope_cache)
                if local is None:
                    local = binding.scope_cache = threading.local()
        return self._scope_in(local, key, provider)

    def _scope_in(
        self, local: threading.local, key: Key, provider: Provider[T]
    ) -> Provider[T]:
        cache: Dict[Key, Provider[Any]] | None = getattr(local, "cache", None)
        if cache is None:
            cache = local.cache = {}
        cached_provider = cache.get(key)
        if cached_provider is None:
            instance = provider.get()
            cached_provider = cache[key] = providers.create_instance_provider(
                instance
            )()
        return cached_provider


NO_SCOPE = _NoScope()
SINGLETON = Singleton()
THREAD_LOCAL = ThreadLocalScope()
