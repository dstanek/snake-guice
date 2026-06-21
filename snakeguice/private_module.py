from typing import Any, cast

from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import Key
from snakeguice.injector import Injector
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Interface
from snakeguice.modules import Module


class PrivateModule(Module):
    """Module that uses a child injector to isolate bindings."""

    def __init__(self) -> None:
        super().__init__()
        self._exposed_keys: list[tuple[Interface, AnnotationLike]] = []

    def expose(
        self,
        binder: BinderI,
        interface: Interface,
        annotation: AnnotationLike = UNANNOTATED,
    ) -> None:
        """Expose the child injector to the parent inject for a binding."""
        self._exposed_keys.append((interface, annotation))
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
        self._exposed_keys = []
        wrapper = _PrivateModuleWrapper(self)
        assert self._injector is not None
        self.private_injector = cast(Injector, self._injector.create_child(wrapper))

        for interface, annotation in self._exposed_keys:
            key = Key(interface, annotation)
            if self.private_injector._binder.get_own_binding(key) is None:
                binder.add_error(
                    f"{interface!r} (annotation={annotation!r}) is exposed "
                    "but has no matching private binding"
                )


class _PrivateModuleWrapper(Module):
    """Exists solely to remove the infinite recursion in Private Modules
    caused by the child injector calling run_configure.
    """

    def __init__(self, module: PrivateModule) -> None:
        self._module = module
        super().__init__()

    def configure(self, binder: BinderI) -> None:
        self._module.configure(binder)
