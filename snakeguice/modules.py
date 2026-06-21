import inspect
from typing import Any, Callable

from snakeguice._extractor import extract_params
from snakeguice.decorators import inject
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Module as ModuleI


class ProvidesBinderHelper:
    def bind_providers(self, module: ModuleI, binder: BinderI) -> None:
        members = [m for m in inspect.getmembers(module) if inspect.ismethod(m[1])]
        for _name, method in members:
            if hasattr(method, "__guice_provides__"):
                provided_type = method.__guice_provides__
                provider = self._build_provider(method)
                binder.bind(provided_type, to_provider=provider)

    def _build_provider(self, method: Callable[..., Any]) -> type[Any]:
        class GenericProvider:
            @inject
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            def get(self) -> Any:
                kwargs = {}
                for param in extract_params(method):
                    kwargs[param.name] = self._injector.get_instance(
                        param.dtype, param.annotation
                    )
                return method(**kwargs)

        return GenericProvider


class ModuleAdapter:
    """Adapts the simple and standard module interfaces to a common one."""

    def __init__(self, module: ModuleI, injector: InjectorI | None) -> None:
        if hasattr(module, "set_injector"):
            module.set_injector(injector)
        self._module = module

    def configure(self, binder: BinderI) -> None:
        if hasattr(self._module, "run_configure"):
            self._module.run_configure(binder)
        else:
            self._module.configure(binder)


class Module:
    """Base class for all standard modules."""

    def __init__(self) -> None:
        self._injector: InjectorI | None = None

    def install(self, binder: BinderI, module: ModuleI) -> None:
        """Add another module's bindings to a binder."""
        ModuleAdapter(module, self._injector).configure(binder)
        ProvidesBinderHelper().bind_providers(module, binder)

    def run_configure(self, binder: BinderI) -> None:
        """A hook for intercepting the configure method. Allows different
        module implementations to change the binder passed to configure.
        """
        self.configure(binder)

    def configure(self, binder: BinderI) -> None:
        """A subclass should override this to configure a binder."""
        raise NotImplementedError

    def set_injector(self, injector: InjectorI) -> None:
        self._injector = injector
