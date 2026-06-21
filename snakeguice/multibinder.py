from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar, cast

from snakeguice import providers
from snakeguice.binder import Key
from snakeguice.decorators import inject
from snakeguice.errors import MultiBindingError
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Key as KeyI
from snakeguice.interfaces import Provider as ProviderI


class _NotSet:
    """Typed sentinel for parameters that were not provided."""

    __slots__ = ()


_NOT_SET = _NotSet()

E = TypeVar("E")  # element type bound by ListBinder / DictBinder
C = TypeVar("C")  # collection type (list[E] or dict[str, E])


class MultiProviderI(ProviderI[C]):
    @staticmethod
    def add_provider(*args: Any) -> None: ...

    @staticmethod
    def get_providers() -> Any: ...


class _MultiBinder(ABC, Generic[C]):
    def __init__(self, binder: BinderI, interface: Any) -> None:
        self._binder = binder
        self._interface = interface
        self._provider = self._get_or_create_provider()

    @abstractmethod
    def _create_provider(self, initial: Any = None) -> type[ProviderI[C]]: ...

    def _get_or_create_provider(self) -> MultiProviderI[C]:
        key = Key(self._interface)
        own_binding = self._binder.get_own_binding(key)
        if own_binding:
            return cast(MultiProviderI[C], own_binding.provider)

        parent_binding = self._binder.get_binding(key)
        if parent_binding:
            parent_provider = cast(MultiProviderI[C], parent_binding.provider)
            initial = parent_provider.get_providers()
        else:
            initial = None

        self._binder.bind(self._interface, to_provider=self._create_provider(initial))
        own_binding = self._binder.get_own_binding(key)
        assert own_binding is not None
        return cast(MultiProviderI[C], own_binding.provider)

    def _dsl_to_provider(
        self,
        to: Any,
        to_provider: type[ProviderI[Any]] | ProviderI[Any] | None,
        to_instance: Any,
    ) -> Any:
        if not isinstance(to, _NotSet):
            return providers.create_simple_provider(to)
        elif to_provider is not None:
            if not isinstance(to_provider, type):
                _instance = to_provider

                class _ProviderInstanceWrapper:
                    def get(self) -> Any:
                        return _instance.get()

                return _ProviderInstanceWrapper
            return to_provider
        elif not isinstance(to_instance, _NotSet):
            return providers.create_instance_provider(to_instance)
        else:
            raise MultiBindingError(
                f"incorrect arguments to {self.__class__.__name__}.add_binding"
            )


class ListBinder(_MultiBinder[list[E]]):
    def __init__(self, binder: BinderI, interface: type[list[E]]) -> None:
        super().__init__(binder, interface)

    def add_binding(
        self,
        to: type[E] | _NotSet = _NOT_SET,
        to_provider: type[ProviderI[E]] | ProviderI[E] | None = None,
        to_instance: E | _NotSet = _NOT_SET,
    ) -> None:
        provider = self._dsl_to_provider(to, to_provider, to_instance)
        self._provider.add_provider(provider)

    def _create_provider(
        self, initial: list[ProviderI[E]] | None = None
    ) -> type[ProviderI[list[E]]]:
        _providers: list[ProviderI[E]] = list(initial or [])

        class DynamicMultiBindingProvider:
            @inject
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            @staticmethod
            def add_provider(provider: ProviderI[E]) -> None:
                _providers.append(provider)

            @staticmethod
            def get_providers() -> list[ProviderI[E]]:
                return _providers

            def get(self) -> list[E]:
                return [self._injector.get_instance(p).get() for p in _providers]

        return DynamicMultiBindingProvider


class DictBinder(_MultiBinder[dict[str, E]]):
    def __init__(self, binder: BinderI, interface: type[dict[str, E]]) -> None:
        super().__init__(binder, interface)

    def add_binding(
        self,
        key: KeyI,
        to: type[E] | _NotSet = _NOT_SET,
        to_provider: type[ProviderI[E]] | ProviderI[E] | None = None,
        to_instance: E | _NotSet = _NOT_SET,
    ) -> None:
        provider = self._dsl_to_provider(to, to_provider, to_instance)
        self._provider.add_provider(key, provider)

    def _create_provider(
        self, initial: dict[str, ProviderI[E]] | None = None
    ) -> type[ProviderI[dict[str, E]]]:
        binder_self = self
        _providers: dict[str, ProviderI[E]] = dict(initial or {})

        class DynamicMultiBindingProvider:
            @inject
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            @staticmethod
            def add_provider(key: str, provider: ProviderI[E]) -> None:
                if key in _providers:
                    raise MultiBindingError(
                        f"duplicate binding for {key!r} in "
                        f"{binder_self._interface} found"
                    )
                _providers[key] = provider

            @staticmethod
            def get_providers() -> dict[str, ProviderI[E]]:
                return _providers

            def get(self) -> dict[str, Any]:
                return {
                    k: self._injector.get_instance(p).get()
                    for k, p in _providers.items()
                }

        return DynamicMultiBindingProvider
