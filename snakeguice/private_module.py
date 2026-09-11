from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import PrivateBinder
from snakeguice.errors import BindingError
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Interface
from snakeguice.modules import Module, _configure


class PrivateModule(Module):
    """Module that configures a private binder, turned into its own child
    injector once configuration finishes, to isolate bindings."""

    def expose(
        self,
        binder: BinderI,
        interface: Interface,
        annotation: AnnotationLike = UNANNOTATED,
    ) -> None:
        """Expose a private binding to the parent binder. `binder` must be
        the (private) binder this module's `configure()` was called with.
        """
        if not isinstance(binder, PrivateBinder):
            raise BindingError(
                "expose() must be called from configure() with the binder it was given"
            )
        binder.expose(interface, annotation)

    def run_configure(self, binder: BinderI) -> None:
        private = binder.create_private()
        _configure(self, private)
        private.validate_exposures()
