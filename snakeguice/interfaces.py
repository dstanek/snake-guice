"""Interfaces used by snake-guice directly"""

from typing import Any, Protocol, Type, TypeVar, overload

from snakeguice.annotation import UNANNOTATED, AnnotationLike

T = TypeVar("T", covariant=True)
U = TypeVar("U")

Binder = Any
Key = Any
Interface = Type[Any]
Module = Any


class Injector(Protocol):
    """An interface automatically bound to the current Injector instance."""

    @overload
    def get_instance(
        self, cls: Type[U], annotation: AnnotationLike = UNANNOTATED
    ) -> U: ...

    @overload
    def get_instance(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> Any: ...

    @overload
    def get_provider(
        self, cls: Type[U], annotation: AnnotationLike = UNANNOTATED
    ) -> "Provider[U]": ...

    @overload
    def get_provider(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> "Provider[Any]": ...

    def create_object(self, cls: Any) -> Any: ...

    def create_child(self, modules: Any) -> "Injector": ...


class Factory(Protocol[T]):
    def create(self, **kwargs: Any) -> T: ...


class Provider(Protocol[T]):
    def get(self) -> T: ...


class ProviderFactory(Protocol[T]):  # TODO: name sucks!
    def get(self) -> Factory[T]: ...


class Scope(Protocol):
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]: ...
