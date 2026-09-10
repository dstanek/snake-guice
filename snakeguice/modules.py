import inspect
from contextvars import ContextVar
from typing import Any, Callable

from snakeguice._extractor import extract_params
from snakeguice.decorators import inject
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Module as ModuleI

_configuring: "ContextVar[tuple[tuple[ModuleI, InjectorI | None], ...]]" = ContextVar(
    "snakeguice_configuring", default=()
)
"""A stack of `(module, injector)` frames, one per in-flight
`ModuleAdapter.configure()` call, ambient rather than stored on the module
instance so one module instance can safely configure more than one injector
- see `Module._injector`.

A flat "last write wins" var isn't enough: `PrivateModule.run_configure()`
runs the module's own `configure()` *nested* one layer inside
`_PrivateModuleWrapper`'s own `ModuleAdapter.configure()` call (for its
private child injector), so by the time the module's `configure()` body
runs, the innermost frame belongs to the wrapper, not to it. `Module._injector`
therefore searches the stack for the frame pushed for `self` specifically,
rather than trusting whichever frame is innermost.
"""


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


def _configure(module: ModuleI, binder: BinderI) -> None:
    """Configure a module against a binder, including its `@provides`
    bindings, as one operation on the same binder.
    """
    module.configure(binder)
    ProvidesBinderHelper().bind_providers(module, binder)


class ModuleAdapter:
    """Adapts the simple and standard module interfaces to a common one."""

    def __init__(self, module: ModuleI, injector: InjectorI | None) -> None:
        self._module = module
        self._injector = injector

    def configure(self, binder: BinderI) -> None:
        # Modules opt in via `set_injector`; the injector is tracked only
        # for the duration of this configure() call.
        token = None
        if hasattr(self._module, "set_injector"):
            stack = _configuring.get()
            token = _configuring.set((*stack, (self._module, self._injector)))
        try:
            if hasattr(self._module, "run_configure"):
                self._module.run_configure(binder)
            else:
                _configure(self._module, binder)
        finally:
            if token is not None:
                _configuring.reset(token)


class Module:
    """Base class for all standard modules."""

    def install(self, binder: BinderI, module: ModuleI) -> None:
        """Add another module's bindings to a binder."""
        ModuleAdapter(module, self._injector).configure(binder)

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

    def set_injector(self, injector: InjectorI) -> None:
        """Marks this module as wanting `self._injector` tracked; see
        `ModuleAdapter.configure` and `_configuring` for where the value
        actually lives.
        """

    @property
    def _injector(self) -> InjectorI | None:
        for module, injector in reversed(_configuring.get()):
            if module is self:
                return injector
        return None
