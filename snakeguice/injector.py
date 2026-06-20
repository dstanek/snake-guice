from typing import Any, TypeVar, overload

from snakeguice._extractor import extract_params
from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import Binder, Key
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as IInjector
from snakeguice.interfaces import Provider
from snakeguice.modules import ModuleAdapter, ProvidesBinderHelper

U = TypeVar("U")


class Injector:
    def __init__(
        self, modules: Any = None, binder: BinderI | None = None, stage: Any = None
    ) -> None:
        if modules is None:
            modules = []
        elif not hasattr(modules, "__iter__"):
            modules = [modules]

        if binder:
            self._binder = binder.create_child()
        else:
            self._binder = Binder()

        self._stage = stage

        self.add_modules(modules)

    def add_modules(self, modules: Any) -> None:
        provides_helper = ProvidesBinderHelper()
        for module in modules:
            ModuleAdapter(module, self).configure(self._binder)
            provides_helper.bind_providers(module, self._binder)
        self._binder.raise_if_errors()

    @overload
    def get_provider(
        self, cls: type[U], annotation: AnnotationLike = UNANNOTATED
    ) -> Provider[U]: ...

    @overload
    def get_provider(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> Provider[Any]: ...

    def get_provider(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> Provider[Any]:
        injector = self

        class DynamicProvider:
            def get(self) -> Any:
                return injector.get_instance(cls, annotation)

        return DynamicProvider()

    @overload
    def get_instance(
        self, cls: type[U], annotation: AnnotationLike = UNANNOTATED
    ) -> U: ...

    @overload
    def get_instance(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> Any: ...

    def get_instance(self, cls: Any, annotation: AnnotationLike = UNANNOTATED) -> Any:
        if cls is IInjector:  # TODO: i don't like this, but it works for now
            return self

        key = Key(cls, annotation)
        binding = self._binder.get_binding(key)
        if binding:
            provider = binding.provider
            if isinstance(provider, type):
                provider = self.get_instance(provider)
            provider = binding.scope.scope(key, provider)
            return provider.get()
        else:
            instance = self.create_object(cls)
            return self.inject_members(instance)

    def create_child(self, modules: Any) -> "Injector":
        """Create a new injector that inherits the state from this injector.

        All bindings are inherited. In the future this may become closer to
        child injectors on google-guice.
        """
        return Injector(modules, binder=self._binder, stage=self._stage)

    def create_object(self, cls: type[Any]) -> Any:
        kwargs = {}
        for param in extract_params(cls.__init__):
            kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
        return cls(**kwargs)

    def inject_members(self, instance: Any) -> Any:
        # this may be a little slow; done twice
        for method_name in getattr(instance.__class__, "__guice_methods__", []):
            kwargs = {}
            method = getattr(instance, method_name)
            for param in extract_params(method):
                kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
            method(**kwargs)
        return instance


def create_injector(modules: Any) -> Injector:
    """Factory for creating Injector instances."""
    return Injector(modules)
