import inspect
from typing import Any, TypeVar, overload

from snakeguice import _context
from snakeguice._extractor import extract_params
from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import Binder, Key
from snakeguice.errors import CircularDependencyError, MissingBindingError
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as IInjector
from snakeguice.interfaces import Provider
from snakeguice.modules import ModuleAdapter

U = TypeVar("U")


def _format_key(key: Key) -> str:
    name = getattr(key.interface, "__name__", None) or repr(key.interface)
    if key.annotation != UNANNOTATED:
        return f"{name}[{key.annotation!r}]"
    return name


def _format_chain(frames: "tuple[tuple[Injector, Key], ...]") -> str:
    # Injector hops are marked: the same Key can legitimately repeat across
    # one (e.g. a PrivateModule.expose()), and an unmarked "->" would read
    # like a false positive. The label is neutral because a frame records
    # only that the injector changed, not why.
    pieces: list[str] = []
    previous_injector: Injector | None = None
    for index, (frame_injector, key) in enumerate(frames):
        if index > 0:
            same_injector = frame_injector is previous_injector
            pieces.append(" -> " if same_injector else " -> [different injector] -> ")
        pieces.append(_format_key(key))
        previous_injector = frame_injector
    return "".join(pieces)


class Injector:
    def __init__(self, modules: Any = None, binder: BinderI | None = None) -> None:
        if modules is None:
            modules = []
        elif not hasattr(modules, "__iter__"):
            modules = [modules]

        self._binder = binder if binder is not None else Binder()

        self._add_modules(modules)

    def _add_modules(self, modules: Any) -> None:
        for module in modules:
            ModuleAdapter(module).configure(self._binder)
        self._binder.raise_if_errors()
        self._build_private_injectors()

    def _build_private_injectors(self) -> None:
        # Two-phase bootstrap: every `PrivateModule` installed while
        # configuring this injector's binder registered a `PrivateBinder`
        # child (see `Binder.create_private`) instead of an injector, so
        # that a private module nested inside another private module's
        # `configure()` parents its `PrivateBinder` to the *enclosing*
        # private binder rather than to the outermost injector. Now that
        # configuration (and error validation) is done, turn each of those
        # binders into its own child `Injector` - recursively, since a
        # private child may itself have private children of its own.
        for child in self._binder._private_children:
            child.injector = Injector(binder=child)

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
        if cls is IInjector or cls is type(self):
            return self

        key = Key(cls, annotation)
        frame = (self, key)
        stack = _context.resolving.get()
        if frame in stack:
            chain = _format_chain((*stack, frame))
            raise CircularDependencyError(f"Circular dependency detected:\n  {chain}")
        resolving_token = _context.resolving.set((*stack, frame))
        try:
            binding = self._binder.get_binding(key)
            if binding:
                provider = binding.provider
                if isinstance(provider, type):
                    provider = self.get_instance(provider)
                binding_token = _context.current_binding.set(binding)
                try:
                    provider = binding.scope.scope(key, provider)
                finally:
                    _context.current_binding.reset(binding_token)
                return provider.get()
            elif key.annotation != UNANNOTATED:
                raise MissingBindingError(
                    f"no binding registered for {_format_key(key)}; "
                    "an annotated key must match an explicit binding, it is "
                    "never implicitly constructed"
                )
            else:
                instance = self.create_object(cls)
                return self.inject_members(instance)
        finally:
            _context.resolving.reset(resolving_token)

    def create_child(self, modules: Any) -> "Injector":
        """Create a new injector that inherits the state from this injector.

        All bindings are inherited. In the future this may become closer to
        child injectors on google-guice.
        """
        return Injector(modules, binder=self._binder.create_child())

    def _has_binding(self, param: Any) -> bool:
        key = Key(param.dtype, param.annotation)
        return bool(self._binder.get_binding(key))

    def create_object(self, cls: type[Any]) -> Any:
        kwargs = {}
        for param in extract_params(cls.__init__):
            if param.default is not inspect.Parameter.empty and not self._has_binding(
                param
            ):
                continue  # no explicit binding — let Python use its own default
            kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
        return cls(**kwargs)

    def inject_members(self, instance: Any) -> Any:
        # Walk MRO from most-derived to base so that if the same method name
        # appears in multiple classes, the most-derived definition wins.
        # Reversing the collected list produces base-first call order.
        seen: set[str] = set()
        ordered: list[str] = []
        for cls in instance.__class__.__mro__:
            for method_name in cls.__dict__.get("__guice_methods__", []):
                if method_name not in seen:
                    seen.add(method_name)
                    ordered.append(method_name)

        for method_name in reversed(ordered):
            kwargs = {}
            method = getattr(instance, method_name)
            for param in extract_params(method):
                if (
                    param.default is not inspect.Parameter.empty
                    and not self._has_binding(param)
                ):
                    continue  # no explicit binding — let Python use its own default
                kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
            method(**kwargs)
        return instance


def create_injector(modules: Any) -> Injector:
    """Factory for creating Injector instances."""
    return Injector(modules)
