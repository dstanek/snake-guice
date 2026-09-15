import inspect
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, overload

from snakeguice import errors, providers, scopes
from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Interface, Provider, Scope

if TYPE_CHECKING:
    from snakeguice.injector import Injector

_NOT_SET = object()


@dataclass
class BinderErrorRecord:
    message: str
    location: str
    source: str


@dataclass(frozen=True, slots=True)
class Key:
    interface: Interface
    annotation: AnnotationLike = UNANNOTATED


@dataclass(slots=True)
class Binding:
    key: Key
    provider: Provider[Any] | type[Provider[Any]]
    scope: Scope
    # A Scope's per-binding cache slot, None until a scope writes to it.
    # Living here ties the cache's lifetime to the binding's injector rather
    # than to a process-global scope object like `scopes.SINGLETON`.
    scope_cache: Any = None
    # A Scope's per-binding construction lock. Living here means unrelated
    # singletons never wait on each other, and a `create_child()` chain
    # shares it along with the cache.
    scope_lock: threading.RLock = field(
        default_factory=threading.RLock, repr=False, compare=False
    )


class _EmptyBinder:
    def get_binding(self, key: Key) -> Binding | None:
        return None


class Binder:
    def __init__(self, parent: BinderI | None = None) -> None:
        self._parent = parent or _EmptyBinder()
        self._binding_map: dict[Key, Binding] = {}
        self._errors: list[BinderErrorRecord] = []
        self._private_children: list["PrivateBinder"] = []

    def add_error(self, msg: str) -> None:
        frame_rec = inspect.stack()[2]

        location = f"File {frame_rec[1]}, line {frame_rec[2]}, in {frame_rec[3]}"
        code_context, index = frame_rec.code_context, frame_rec.index
        if code_context is not None and index is not None:
            source = code_context[index].strip()
        else:
            source = "<source unavailable>"
        self._errors.append(
            BinderErrorRecord(message=msg, location=location, source=source)
        )

    @property
    def errors(self) -> list[BinderErrorRecord]:
        return self._errors

    def _collect_errors(self) -> list[BinderErrorRecord]:
        collected = list(self._errors)
        for child in self._private_children:
            collected.extend(child._collect_errors())
        return collected

    def raise_if_errors(self) -> None:
        all_errors = self._collect_errors()
        if not all_errors:
            return

        count = len(all_errors)
        noun = "error" if count == 1 else "errors"
        lines = [f"{count} {noun} while creating an injector:", ""]
        for n, err in enumerate(all_errors, start=1):
            lines.append(f"{n}) {err.message}")
            lines.append(f"  at {err.location}")
            lines.append(f"      {err.source}")
            lines.append("")
        raise errors.CreationError("\n".join(lines))

    @overload
    def bind(
        self,
        _class: type[Any],
        *,
        to: type[Any],
        in_scope: Scope = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    # `to_instance=`/`to_provider=` accept a duck-typed stand-in for
    # `_class` at runtime (see
    # tests/test_binder.py::test_to_instance_accepts_a_duck_typed_stand_in),
    # so there's no real type relationship between `_class` and the target
    # to enforce here; `_class` is left as `type[Any]` like the `to=`
    # overload above.
    @overload
    def bind(
        self,
        _class: type[Any],
        *,
        to_provider: type[Provider[Any]] | Provider[Any],
        in_scope: Scope = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    @overload
    def bind(
        self,
        _class: type[Any],
        *,
        to_instance: Any,
        in_scope: Scope = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    @overload
    def bind(
        self,
        _class: AnnotationLike,
        *,
        to_instance: Any,
        in_scope: Scope = ...,
        annotated_with: AnnotationLike = ...,
    ) -> None: ...

    def bind(
        self,
        _class: Any,
        *,
        to: Any = _NOT_SET,
        to_provider: Any = _NOT_SET,
        to_instance: Any = _NOT_SET,
        in_scope: Scope = scopes.NO_SCOPE,
        annotated_with: AnnotationLike = UNANNOTATED,
    ) -> None:
        key = Key(interface=_class, annotation=annotated_with)
        provider: Provider[Any] | type[Provider[Any]]

        if key in self._binding_map:
            self.add_error(f"baseclass {_class!r} already bound")
            return

        supplied = sum(x is not _NOT_SET for x in (to, to_provider, to_instance))
        if supplied > 1:
            self.add_error(
                f"multiple binding targets supplied for {_class!r}; "
                "use exactly one of to=, to_provider=, or to_instance="
            )
            return
        elif to is not _NOT_SET:
            if not isinstance(to, type):
                self.add_error("'to' requires a new-style class")
                return

            provider = providers.create_simple_provider(to)

        elif to_provider is not _NOT_SET:
            if not callable(getattr(to_provider, "get", None)):
                self.add_error(
                    "'to_provider' requires a class or instance with a 'get' method"
                )
                return
            provider = to_provider

        elif to_instance is not _NOT_SET:
            # An instance, not the provider class: `Binding.provider` accepts
            # either, and resolving an instance binding this way skips a full
            # get_instance() round trip (cycle-detection frame, create_object)
            # on every access.
            provider = providers.create_instance_provider(to_instance)()

        else:
            self.add_error(
                f"no binding target supplied for {_class!r}; "
                "use to=, to_provider=, or to_instance="
            )
            return

        binding = Binding(key=key, provider=provider, scope=in_scope)
        self._binding_map[key] = binding

    def get_own_binding(self, key: Key) -> Binding | None:
        return self._binding_map.get(key)

    def get_binding(self, key: Key) -> Binding | None:
        return self._binding_map.get(key) or self._parent.get_binding(key)

    def create_child(self) -> "Binder":
        return Binder(self)

    def create_private(self) -> "PrivateBinder":
        """Create a `PrivateBinder` child, to be configured now and turned
        into its own child `Injector` once the enclosing injector has
        finished configuring (see `Injector._build_private_injectors`).
        """
        child = PrivateBinder(self)
        self._private_children.append(child)
        return child


class PrivateBinder(Binder):
    """A `Binder` whose bindings are configured against it directly but,
    once configuration finishes, become their own child `Injector` rather
    than joining the parent binder's own bindings. `expose()` re-binds
    selected keys on the parent binder with providers that resolve through
    that private injector - see `PrivateModule`.
    """

    def __init__(self, parent: Binder) -> None:
        super().__init__(parent)
        self._parent_binder = parent
        self._exposed: list[Key] = []
        # Set by `Injector._build_private_injectors` after this binder (and
        # any of its own private children) have finished configuring.
        self.injector: "Injector | None" = None

    def expose(
        self, interface: Interface, annotation: AnnotationLike = UNANNOTATED
    ) -> None:
        key = Key(interface, annotation)
        self._exposed.append(key)

        private_binder = self

        class ExposedProvider:
            def get(self) -> Any:
                if private_binder.injector is None:
                    raise errors.BindingError(
                        "exposed binding resolved before its private injector was built"
                    )
                return private_binder.injector.get_instance(interface, annotation)

        self._parent_binder.bind(
            interface, annotated_with=annotation, to_provider=ExposedProvider
        )

    def validate_exposures(self) -> None:
        for key in self._exposed:
            if self.get_own_binding(key) is None:
                self._parent_binder.add_error(
                    f"{key.interface!r} (annotation={key.annotation!r}) is "
                    "exposed but has no matching private binding"
                )
