import functools
import inspect
import sys
from typing import Any, Iterable, TypeVar, overload

from snakeguice import _context
from snakeguice._extractor import Param, extract_params
from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.binder import Binder, Key
from snakeguice.errors import (
    CircularDependencyError,
    ImplicitConstructionError,
    MissingBindingError,
)
from snakeguice.interfaces import Injector as IInjector
from snakeguice.interfaces import Module, Provider
from snakeguice.modules import ModuleAdapter

U = TypeVar("U")


class _DynamicProvider:
    __slots__ = ("_injector", "_cls", "_annotation")

    def __init__(
        self, injector: "Injector", cls: Any, annotation: AnnotationLike
    ) -> None:
        self._injector = injector
        self._cls = cls
        self._annotation = annotation

    def get(self) -> Any:
        return self._injector.get_instance(self._cls, self._annotation)


@functools.lru_cache(maxsize=None)
def _guice_method_order(cls: type) -> tuple[str, ...]:
    # Base classes first, declaration order within each class; a method
    # overridden in a subclass runs once, at the overriding class's position.
    ordered: list[str] = []
    for klass in reversed(cls.__mro__):
        ordered.extend(klass.__dict__.get("__guice_methods__", []))
    return tuple(n for i, n in enumerate(ordered) if n not in ordered[i + 1 :])


def _type_name(dtype: Any) -> str:
    # `dtype` isn't always a `type` -- e.g. `Foo | None` is a `types.
    # UnionType` instance -- so `__name__` isn't guaranteed; fall back to
    # `str()`, which renders a union as "module.Foo | None".
    return getattr(dtype, "__name__", None) or str(dtype)


def _refuses_implicit_construction(dtype: Any) -> bool:
    # A zero-arg str()/int()/list()/pathlib.Path() is a vacuous *value* --
    # never the specific one a forgotten binding should have produced --
    # whereas a zero-arg HWController() is a working object, so builtin and
    # standard-library types are refused and everything else (third-party
    # or in-app classes alike) is still built as before. `dtype` also isn't
    # always a real type (e.g. `Foo | None` is a `types.UnionType`
    # instance, which create_object() would otherwise try to call and fail
    # on with a confusing `TypeError: ... not callable`), so anything that
    # isn't a `type` is refused too.
    if not isinstance(dtype, type):
        return True
    top_level_module = dtype.__module__.partition(".")[0]
    return top_level_module == "builtins" or top_level_module in sys.stdlib_module_names


def _why_refused(dtype: Any) -> str:
    if not isinstance(dtype, type):
        return "isn't a constructible type"
    return "is a builtin or standard-library type"


def _format_key(key: Key) -> str:
    name = _type_name(key.interface)
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
    def __init__(
        self,
        modules: Module | Iterable[Module] | None = None,
        binder: Binder | None = None,
    ) -> None:
        resolved_modules: Iterable[Module]
        if modules is None:
            resolved_modules = []
        elif isinstance(modules, str):
            # str is iterable; without this it fails per character, later.
            raise TypeError(
                f"modules must be a Module, an iterable of Module, or None, "
                f"not a str: {modules!r}"
            )
        elif isinstance(modules, Iterable):
            resolved_modules = modules
        else:
            resolved_modules = [modules]

        self._binder = binder if binder is not None else Binder()

        self._add_modules(resolved_modules)

    def _add_modules(self, modules: Iterable[Module]) -> None:
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
        return _DynamicProvider(self, cls, annotation)

    @overload
    def get_instance(
        self, cls: type[U], annotation: AnnotationLike = UNANNOTATED
    ) -> U: ...

    @overload
    def get_instance(
        self, cls: Any, annotation: AnnotationLike = UNANNOTATED
    ) -> Any: ...

    def get_instance(self, cls: Any, annotation: AnnotationLike = UNANNOTATED) -> Any:
        if cls is IInjector or (cls is not object and cls in type(self).__mro__):
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
                if _refuses_implicit_construction(cls):
                    name = _type_name(cls)
                    raise ImplicitConstructionError(
                        f"no binding for {name}; {name} {_why_refused(cls)}, "
                        "so it is never implicitly constructed - add a "
                        "binding"
                    )
                instance = self.create_object(cls)
                return self.inject_members(instance)
        finally:
            _context.resolving.reset(resolving_token)

    def create_child(self, modules: Module | Iterable[Module] | None) -> "Injector":
        """Create a new injector that inherits the state from this injector.

        All bindings are inherited. In the future this may become closer to
        child injectors on google-guice.
        """
        return Injector(modules, binder=self._binder.create_child())

    def _has_binding(self, param: Any) -> bool:
        key = Key(param.dtype, param.annotation)
        return bool(self._binder.get_binding(key))

    def _require_constructible(
        self, owner: type, member: str, param: Param, has_binding: bool
    ) -> None:
        # get_instance(dtype, annotation) is what would actually attempt the
        # implicit construction, but by then it no longer knows which class
        # and parameter asked for it -- only the type. Checking here, where
        # `owner`/`member`/`param` are all in hand, is what lets the error
        # name the parameter instead of just the type. An annotated param
        # skips this: it already raises MissingBindingError inside
        # get_instance() regardless, since an annotation names one specific
        # binding and is never implicitly constructed.
        if has_binding or param.annotation != UNANNOTATED:
            return
        if not _refuses_implicit_construction(param.dtype):
            return
        name = _type_name(param.dtype)
        raise ImplicitConstructionError(
            f"no binding for '{param.name}: {name}' required by "
            f"{owner.__name__}.{member}; {name} {_why_refused(param.dtype)}, "
            "so it is never implicitly constructed - add a binding"
        )

    def create_object(self, cls: type[Any]) -> Any:
        kwargs = {}
        for param in extract_params(cls.__init__):
            has_binding = self._has_binding(param)
            if param.default is not inspect.Parameter.empty and not has_binding:
                continue  # no explicit binding — let Python use its own default
            self._require_constructible(cls, "__init__", param, has_binding)
            kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
        return cls(**kwargs)

    def inject_members(self, instance: Any) -> Any:
        for method_name in _guice_method_order(instance.__class__):
            kwargs = {}
            method = getattr(instance, method_name)
            for param in extract_params(method):
                has_binding = self._has_binding(param)
                if param.default is not inspect.Parameter.empty and not has_binding:
                    continue  # no explicit binding — let Python use its own default
                self._require_constructible(
                    instance.__class__, method_name, param, has_binding
                )
                kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
            method(**kwargs)
        return instance


def create_injector(modules: Module | Iterable[Module] | None) -> Injector:
    """Factory for creating Injector instances."""
    return Injector(modules)
