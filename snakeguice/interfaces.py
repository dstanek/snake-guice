"""Interfaces used by snake-guice directly"""

from typing import TYPE_CHECKING, Any, Protocol, Type, TypeVar, overload

from snakeguice.annotation import UNANNOTATED, AnnotationLike

if TYPE_CHECKING:
    from snakeguice.binder import BinderErrorRecord, Binding, PrivateBinder
    from snakeguice.binder import Key as KeyC

T = TypeVar("T", covariant=True)
U = TypeVar("U")
_T = TypeVar("_T")

Key = Any
Interface = Type[Any]
Module = Any


class Binder(Protocol):
    """The interface `configure(binder)` is called with. The concrete
    `snakeguice.binder.Binder` is the only implementation; this exists so
    `bind()`'s overloads (and the rest of the DSL) are checked at the call
    sites a `Module.configure()` writes, instead of everything typing as
    `Any`.
    """

    @overload
    def bind(
        self,
        _class: type[Any],
        *,
        to: type[Any],
        in_scope: "Scope" = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    @overload
    def bind(
        self,
        _class: type[_T],
        *,
        to_provider: "type[Provider[_T]] | Provider[_T]",
        in_scope: "Scope" = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    @overload
    def bind(
        self,
        _class: type[_T],
        *,
        to_instance: _T,
        in_scope: "Scope" = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    @overload
    def bind(
        self,
        _class: AnnotationLike,
        *,
        to_instance: Any,
        in_scope: "Scope" = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    def bind(
        self,
        _class: Any,
        *,
        to: Any = ...,
        to_provider: Any = ...,
        to_instance: Any = ...,
        in_scope: "Scope" = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    def add_error(self, msg: str) -> None: ...

    @property
    def errors(self) -> "list[BinderErrorRecord]": ...

    def raise_if_errors(self) -> None: ...

    def get_binding(self, key: "KeyC") -> "Binding | None": ...

    def get_own_binding(self, key: "KeyC") -> "Binding | None": ...

    def create_child(self) -> "Binder": ...

    def create_private(self) -> "PrivateBinder": ...


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

    def inject_members(self, instance: Any) -> Any: ...

    def create_child(self, modules: Any) -> "Injector": ...


class Factory(Protocol[T]):
    def create(self, **kwargs: Any) -> T: ...


class Provider(Protocol[T]):
    def get(self) -> T: ...


class ProviderFactory(Protocol[T]):  # TODO: name sucks!
    def get(self) -> Factory[T]: ...


class Scope(Protocol):
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]: ...
