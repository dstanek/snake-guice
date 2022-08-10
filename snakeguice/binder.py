from snakeguice import errors, providers, scopes

_NOT_SET = object()


class Key:
    def __init__(self, interface, annotation=None):
        self._interface = interface
        self._annotation = annotation

    def __hash__(self):
        return hash((self._interface, self._annotation))

    def __eq__(self, other):
        return (
            self._interface == other._interface
            and self._annotation == other._annotation
        )

    def __ne__(self, other):
        return not self == other


class _EmptyBinder:
    def get_binding(self, key):
        return None


class Binder:
    def __init__(self, parent=None):
        self._parent = parent or _EmptyBinder()
        self._binding_map = {}

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

    def get_binding(self, key):
        return self._binding_map.get(key) or self._parent.get_binding(key)

    def create_child(self):
        return Binder(self)


class LazyBinder:
    def __init__(self, parent=None):
        self._parent = parent or _EmptyBinder()
        self._binding_map = {}
        self._errors = []

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


class Binding:
    def __init__(self, key=None, provider=None, scope=None):
        self.key = key
        self.provider = provider
        self.scope = scope


class BinderErrorRecord:
    def __init__(self, message, location, source):
        self.message = message
        self.location = location
        self.source = source
