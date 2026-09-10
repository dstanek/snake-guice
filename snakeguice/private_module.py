from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, cast

from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import Key
from snakeguice.injector import Injector
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Interface
from snakeguice.modules import Module


@dataclass
class _Run:
    """Per-`run_configure()`-call state for a `PrivateModule`.

    Held ambiently (see `_current_run`), not on the module instance, so one
    `PrivateModule` instance can safely configure more than one injector:
    each run gets its own `original_binder`/`exposed_keys`/
    `private_injector`, and `expose()`'s provider closure captures this run
    object rather than the module - so an older run's exposed bindings keep
    resolving through that run's private injector even after the module is
    reused for a newer one.
    """

    original_binder: BinderI
    exposed_keys: list[tuple[Interface, AnnotationLike]] = field(default_factory=list)
    private_injector: Injector | None = None


_current_run: "ContextVar[_Run | None]" = ContextVar(
    "snakeguice_private_module_run", default=None
)


class PrivateModule(Module):
    """Module that uses a child injector to isolate bindings."""

    def expose(
        self,
        binder: BinderI,
        interface: Interface,
        annotation: AnnotationLike = UNANNOTATED,
    ) -> None:
        """Expose the child injector to the parent inject for a binding."""
        run = _current_run.get()
        assert run is not None, "expose() may only be called from configure()"
        run.exposed_keys.append((interface, annotation))

        class Provider:
            def get(self) -> Any:
                assert run is not None and run.private_injector is not None
                return run.private_injector.get_instance(interface, annotation)

        run.original_binder.bind(
            interface, annotated_with=annotation, to_provider=Provider
        )

    def run_configure(self, binder: BinderI) -> None:
        run = _Run(original_binder=binder)
        token = _current_run.set(run)
        try:
            wrapper = _PrivateModuleWrapper(self)
            assert self._injector is not None
            private_injector = cast(Injector, self._injector.create_child(wrapper))
            run.private_injector = private_injector
        finally:
            _current_run.reset(token)

        for interface, annotation in run.exposed_keys:
            key = Key(interface, annotation)
            if private_injector._binder.get_own_binding(key) is None:
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

    def configure(self, binder: BinderI) -> None:
        self._module.configure(binder)
