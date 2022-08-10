from typing import Dict, List, Optional

from snakeguice import errors, providers, scopes
from snakeguice.annotation import UNANNOTATED, Annotation
from snakeguice.interfaces import Interface, Provider, Scope

_NOT_SET = object()


class BinderErrorRecord:
    def __init__(self, message: str, location: str, source: str) -> None:
        self.message = message
        self.location = location
        self.source = source


class Key:
    def __init__(
        self, interface: Interface, annotation: Annotation = UNANNOTATED
    ) -> None:
        self._interface = interface
        self._annotation = annotation

    def __hash__(self) -> int:
        return hash((self._interface, self._annotation))

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)

    def __ne__(self, other: object) -> bool:
        return not self == other


class Binding:
    def __init__(
        self, key: Key = None, provider: Provider = None, scope: Scope = None
    ) -> None:
        self.key = key
        self.provider = provider
        self.scope = scope


class _EmptyBinder:
    def get_binding(self, key: Key) -> Optional[Binding]:
        return None


class Binder:
    def __init__(self, parent=None) -> None:
        self._parent = parent or _EmptyBinder()
        self._binding_map: Dict[Key, Binding] = {}

    def bind(
        self,
        _class,
        to=_NOT_SET,
        to_provider=_NOT_SET,
        to_instance=_NOT_SET,
        in_scope=scopes.NO_SCOPE,
        annotated_with=UNANNOTATED,
    ):
        key = Key(interface=_class, annotation=annotated_with)

        binding = Binding()
        binding.key = key
        binding.scope = in_scope

        if key in self._binding_map:
            raise errors.BindingError("baseclass %r already bound" % _class)

        if to is not _NOT_SET:
            if not isinstance(to, type):
                raise errors.BindingError("'to' requires a new-style class")

            binding.provider = providers.create_simple_provider(to)

        elif to_provider is not _NOT_SET:
            # TODO: add some validation
            provider = to_provider
            binding.provider = provider

        elif to_instance is not _NOT_SET:
            if not isinstance(to_instance, object):
                raise errors.BindingError(
                    "'to_instance' requires an instance of a new-style class"
                )

            provider = to_instance
            binding.provider = providers.create_instance_provider(provider)

        self._binding_map[key] = binding

    def get_binding(self, key: Key) -> Optional[Binding]:
        return self._binding_map.get(key) or self._parent.get_binding(key)

    def create_child(self):
        return Binder(self)


class LazyBinder:
    def __init__(self, parent=None) -> None:
        self._parent = parent or _EmptyBinder()
        self._binding_map: Dict[Key, Binding] = {}
        self._errors: List[BinderErrorRecord] = []

    def add_error(self, msg):
        import inspect

        frame_rec = inspect.stack()[2]

        location = "File {0}, line {1}, in {2}".format(
            frame_rec[1], frame_rec[2], frame_rec[3]
        )
        source = frame_rec[4][frame_rec[5]].strip()
        self._errors.append(
            BinderErrorRecord(message=msg, location=location, source=source)
        )

    @property
    def errors(self):
        return self._errors

    def bind(
        self,
        _class,
        to=_NOT_SET,
        to_provider=_NOT_SET,
        to_instance=_NOT_SET,
        in_scope=scopes.NO_SCOPE,
        annotated_with=None,
    ):
        key = Key(interface=_class, annotation=annotated_with)

        binding = Binding()
        binding.key = key
        binding.scope = in_scope

        if key in self._binding_map:
            self.add_error("baseclass %r already bound" % _class)

        if to is not _NOT_SET:
            if not isinstance(to, type):
                self.add_error("to requires a new-style class")

            binding.provider = providers.create_simple_provider(to)

        elif to_provider is not _NOT_SET:
            # TODO: add some validation
            provider = to_provider
            binding.provider = provider

        elif to_instance is not _NOT_SET:
            if not isinstance(to_instance, object):
                self.add_error(
                    "to_instance requires an instance of a " "new-style class"
                )

            provider = to_instance
            binding.provider = providers.create_instance_provider(provider)

        self._binding_map[key] = binding

    def get_binding(self, key):
        return self._binding_map.get(key) or self._parent.get_binding(key)

    def create_child(self):
        return Binder(self)
