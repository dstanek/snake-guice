import inspect
from typing import Any, Callable

from snakeguice._extractor import extract_params
from snakeguice.decorators import inject
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Module as ModuleI


class ProvidesBinderHelper:
    def bind_providers(self, module: ModuleI, binder: BinderI) -> None:
        # Walk the MRO's own __dict__s instead of inspect.getmembers(module):
        # getmembers() calls getattr() for every attribute, which would run
        # any @property on the module as a side effect at configuration time.
        seen: set[str] = set()
        for cls in type(module).__mro__:
            for name, member in cls.__dict__.items():
                if name in seen:
                    continue
                seen.add(name)
                if isinstance(member, classmethod):
                    member = member.__func__
                if inspect.isfunction(member) and hasattr(member, "__guice_provides__"):
                    method = getattr(module, name)
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


def _configure(module: ModuleI, binder: BinderI) -> None:
    """Configure a module against a binder, including its `@provides`
    bindings, as one operation on the same binder.
    """
    module.configure(binder)
    ProvidesBinderHelper().bind_providers(module, binder)


class ModuleAdapter:
    """Adapts the simple and standard module interfaces to a common one."""

    def __init__(self, module: ModuleI) -> None:
        self._module = module

    def configure(self, binder: BinderI) -> None:
        # run_configure is a Module-subclass hook, not part of the protocol.
        run_configure = getattr(self._module, "run_configure", None)
        if run_configure is not None:
            run_configure(binder)
        else:
            _configure(self._module, binder)


class Module:
    """Base class for all standard modules."""

    def install(self, binder: BinderI, module: ModuleI) -> None:
        """Add another module's bindings to a binder."""
        ModuleAdapter(module).configure(binder)

    def run_configure(self, binder: BinderI) -> None:
        """A hook for intercepting the configure method. Allows different
        module implementations to change the binder passed to configure.

        By default this also binds the module's `@provides` methods onto
        the same binder as `configure()`. A subclass that overrides this
        (e.g. to route configure() to a different binder) is responsible
        for deciding where its `@provides` bindings land.
        """
        _configure(self, binder)

    def configure(self, binder: BinderI) -> None:
        """A subclass should override this to configure a binder."""
        raise NotImplementedError
