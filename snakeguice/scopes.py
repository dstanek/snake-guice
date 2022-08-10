"""Scopes that can be used in the binding process."""

# pylint: disable-msg=C0111

from typing import Dict

from snakeguice import providers
from snakeguice.interfaces import Key, Provider


class _NoScope:
    """A default scope returns the same provider that gets passed in.

    This is internally used and will probably never be directly used in
    a module.
    """

    def scope(
        self, key: Key, unscoped_provider: Provider
    ):  # pylint: disable-msg=R0201,
        return unscoped_provider


class _Singleton:
    """A singleton scope only allows a single instance to be created for a
    given key.
    """

    def __init__(self) -> None:
        self._cached_provider_map: Dict[Key, Provider] = {}

    def scope(self, key: Key, provider: Provider):
        cached_provider = self._cached_provider_map.get(key)
        if not cached_provider:
            instance = provider.get()
            cached_provider = self._cached_provider_map[
                key
            ] = providers.create_instance_provider(instance)()
        return cached_provider


NO_SCOPE = _NoScope()
SINGLETON = _Singleton()
