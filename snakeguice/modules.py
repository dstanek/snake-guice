from typing import Any

from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.interfaces import Interface
from snakeguice.interfaces import Module as ModuleI


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


class _PrivateModuleWrapper(Module):
    """Exists solely to remove the infinite recursion in Private Modules
    caused by the child injector calling run_configure.
    """

    def __init__(self, module: ModuleI) -> None:
        self._module = module
        super(_PrivateModuleWrapper, self).__init__()

    def configure(self, binder: BinderI) -> None:
        self._module.configure(binder)


class PrivateModule(Module):
    """Module that uses a child injector to isolate bindings."""

    def expose(
        self,
        binder: BinderI,
        interface: Interface,
        annotation: AnnotationLike = UNANNOTATED,
    ) -> None:
        """Expose the child injector to the parent inject for a binding."""
        private_module = self

        class Provider:
            def get(self) -> Any:
                return private_module.private_injector.get_instance(
                    interface, annotation
                )

        self.original_binder.bind(
            interface, annotated_with=annotation, to_provider=Provider
        )

    def run_configure(self, binder: BinderI) -> None:
        self.original_binder = binder
        private_module = _PrivateModuleWrapper(self)
        assert self._injector is not None
        self.private_injector = self._injector.create_child(private_module)
