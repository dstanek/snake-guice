import inspect
from dataclasses import dataclass
from typing import Any

from snakeguice import errors, providers, scopes
from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Interface, Provider, Scope

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
    key: Key | None = None
    provider: Provider[Any] | type[Provider[Any]] | None = None
    scope: Scope | None = None


class _EmptyBinder:
    def get_binding(self, key: Key) -> Binding | None:
        return None


class Binder:
    def __init__(self, parent: BinderI | None = None) -> None:
        self._parent = parent or _EmptyBinder()
        self._binding_map: dict[Key, Binding] = {}
        self._errors: list[BinderErrorRecord] = []

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

    def raise_if_errors(self) -> None:
        if not self._errors:
            return

        count = len(self._errors)
        noun = "error" if count == 1 else "errors"
        lines = [f"{count} {noun} while creating an injector:", ""]
        for n, err in enumerate(self._errors, start=1):
            lines.append(f"{n}) {err.message}")
            lines.append(f"  at {err.location}")
            lines.append(f"      {err.source}")
            lines.append("")
        raise errors.CreationError("\n".join(lines))

    def bind(
        self,
        _class: type[Any],
        to: Any = _NOT_SET,
        to_provider: Any = _NOT_SET,
        to_instance: Any = _NOT_SET,
        in_scope: Scope = scopes.NO_SCOPE,
        annotated_with: AnnotationLike = UNANNOTATED,
    ) -> None:
        key = Key(interface=_class, annotation=annotated_with)

        binding = Binding()
        binding.key = key
        binding.scope = in_scope

        if key in self._binding_map:
            self.add_error(f"baseclass {_class!r} already bound")

        if to is not _NOT_SET:
            if not isinstance(to, type):
                self.add_error("'to' requires a new-style class")

            binding.provider = providers.create_simple_provider(to)

        elif to_provider is not _NOT_SET:
            # TODO: add some validation
            provider = to_provider
            binding.provider = provider

        elif to_instance is not _NOT_SET:
            if not isinstance(to_instance, object):
                self.add_error(
                    "'to_instance' requires an instance of a new-style class"
                )

            provider = to_instance
            binding.provider = providers.create_instance_provider(provider)

        self._binding_map[key] = binding

    def get_own_binding(self, key: Key) -> Binding | None:
        return self._binding_map.get(key)

    def get_binding(self, key: Key) -> Binding | None:
        return self._binding_map.get(key) or self._parent.get_binding(key)

    def create_child(self) -> BinderI:
        return Binder(self)
