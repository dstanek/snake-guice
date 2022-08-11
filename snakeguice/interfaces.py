"""Interfaces used by snake-guice directly"""

from typing import Any, Optional, Protocol, Type, TypeVar

T = TypeVar("T", covariant=True)

Binder = Any
Key = Any
Interface = Type[Any]
Module = Any


class Injector:
    """An interface automatically bound to the current Injector instance."""

    def get_instance(self, cls: Any, annotation: Optional[Any] = None):
        ...


class Factory(Protocol[T]):
    def create(self, **kwargs: Any):
        ...


class Provider(Protocol[T]):
    def get(self) -> T:
        ...


class ProviderFactory(Protocol[T]):  # TODO: name sucks!
    def get(self) -> Factory[T]:
        ...


class Scope(Protocol):
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        ...
