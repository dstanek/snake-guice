from typing import Any, Generic, TypeVar, cast

from snakeguice import providers
from snakeguice.binder import Key
from snakeguice.decorators import inject
from snakeguice.errors import MultiBindingError
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Key as KeyI
from snakeguice.interfaces import Provider as ProviderI

# TODO: now that we are using standand type annotations we can probably simplify
#       the interface by replacing ListBinder and DictBinder with MultiBinder.
#
#       So using:
#           MultiBinder(binder, list[Thing])
#       instead of:
#           ListBinder(binder, list[Thing])

T = TypeVar("T", bound=type)


class MultiProviderI(ProviderI[T]):
    @staticmethod
    def add_provider(*args: Any) -> None: ...

    @staticmethod
    def get_providers() -> Any: ...


class _MultiBinder(Generic[T]):
    def __init__(self, binder: BinderI, interface: T) -> None:
        self._binder = binder
        self._interface = interface
        self._provider = self._get_or_create_provider()

    def _create_provider(self, initial: Any = None) -> Any:  # TODO: type properly
        pass

    def _get_or_create_provider(self) -> MultiProviderI[T]:
        key = Key(self._interface)
        own_binding = self._binder.get_own_binding(key)
        if own_binding:
            return cast(MultiProviderI[T], own_binding.provider)

        parent_binding = self._binder.get_binding(key)
        if parent_binding:
            parent_provider = cast(MultiProviderI[T], parent_binding.provider)
            initial = parent_provider.get_providers()
        else:
            initial = None

        self._binder.bind(self._interface, to_provider=self._create_provider(initial))
        own_binding = self._binder.get_own_binding(key)
        assert own_binding is not None
        return cast(MultiProviderI[T], own_binding.provider)

    def _dsl_to_provider(
        self,
        to: Any,
        to_provider: ProviderI[T] | type[ProviderI[T]] | None,
        to_instance: Any,
    ) -> Any:
        if to:
            # TODO: add some validation
            return providers.create_simple_provider(to)
        elif to_provider:
            # TODO: add some validation
            return to_provider
        elif to_instance:
            # TODO: add some validation
            return providers.create_instance_provider(to_instance)
        else:
            raise MultiBindingError(
                f"incorrect arguments to {self.__class__.__name__}.add_binding"
            )


class ListBinder(_MultiBinder[T]):
    def add_binding(
        self,
        to: Any = None,
        to_provider: ProviderI[T] | type[ProviderI[T]] | None = None,
        to_instance: Any = None,
    ) -> None:
        provider = self._dsl_to_provider(to, to_provider, to_instance)
        self._provider.add_provider(provider)

    def _create_provider(
        self, initial: list[ProviderI[T]] | None = None
    ) -> type[ProviderI[list[T]]]:
        _providers: list[ProviderI[T]] = list(initial or [])

        class DynamicMultiBindingProvider:
            @inject
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            @staticmethod
            def add_provider(provider: ProviderI[T]) -> None:
                _providers.append(provider)

            @staticmethod
            def get_providers() -> list[ProviderI[T]]:
                return _providers

            def get(self) -> list[T]:
                return [self._injector.get_instance(p).get() for p in _providers]

        return DynamicMultiBindingProvider


class DictBinder(_MultiBinder[T]):
    def add_binding(
        self,
        key: KeyI,
        to: Any = None,
        to_provider: ProviderI[T] | type[ProviderI[T]] | None = None,
        to_instance: Any = None,
    ) -> None:
        provider = self._dsl_to_provider(to, to_provider, to_instance)
        self._provider.add_provider(key, provider)

    def _create_provider(
        self, initial: dict[str, ProviderI[T]] | None = None
    ) -> type[ProviderI[dict[str, T]]]:
        binder_self = self
        _providers: dict[str, ProviderI[T]] = dict(initial or {})

        class DynamicMultiBindingProvider:
            @inject
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            @staticmethod
            def add_provider(key: str, provider: ProviderI[T]) -> None:
                if key in _providers:
                    raise MultiBindingError(
                        f"duplicate binding for {key!r} in "
                        f"{binder_self._interface} found"
                    )
                _providers[key] = provider

            @staticmethod
            def get_providers() -> dict[str, ProviderI[T]]:
                return _providers

            def get(self) -> dict[str, Any]:
                return {
                    k: self._injector.get_instance(p).get()
                    for k, p in _providers.items()
                }

        return DynamicMultiBindingProvider
