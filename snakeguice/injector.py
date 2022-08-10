import inspect

from snakeguice._extractor import extract_params
from snakeguice.binder import Binder, Key
from snakeguice.decorators import inject
from snakeguice.interfaces import Injector as IInjector
from snakeguice.modules import ModuleAdapter


class ProvidesBinderHelper:
    def bind_providers(self, module, binder):
        members = [m for m in inspect.getmembers(module) if inspect.ismethod(m[1])]
        for name, method in members:
            if hasattr(method, "__guice_provides__"):
                type = method.__guice_provides__
                provider = self._build_provider(module, type, method)
                binder.bind(type, to_provider=provider)

    def _build_provider(self, module, type, method):
        class GenericProvider:
            @inject
            def __init__(self, injector: IInjector):
                self._injector = injector

            def get(self):
                kwargs = {}
                for param in extract_params(method):
                    kwargs[param.name] = self._injector.get_instance(
                        param.dtype, param.annotation
                    )
                return method(**kwargs)

        return GenericProvider


class Injector:
    def __init__(self, modules=None, binder=None, stage=None):
        if modules is None:
            modules = []
        elif not hasattr(modules, "__iter__"):
            modules = [modules]

        if binder:
            self._binder = binder.create_child()
        else:
            self._binder = Binder()

        self._stage = stage

        self.add_modules(modules)

    def add_modules(self, modules):
        provides_helper = ProvidesBinderHelper()
        for module in modules:
            ModuleAdapter(module, self).configure(self._binder)
            provides_helper.bind_providers(module, self._binder)

    def get_provider(self, cls, annotation=None):
        injector = self

        class DynamicProvider:
            def get(self):
                return injector.get_instance(cls, annotation)

        return DynamicProvider()

    def get_instance(self, cls, annotation=None):
        if cls is IInjector:  # TODO: i don't like this, but it works for now
            return self

        key = Key(cls, annotation)
        binding = self._binder.get_binding(key)
        if binding:
            if isinstance(binding.provider, type):
                binding.provider = self.get_instance(binding.provider)
            provider = binding.scope.scope(key, binding.provider)
            return provider.get()
        else:
            instance = self.create_object(cls)
            return self.inject_members(instance)

    def create_child(self, modules):
        """Create a new injector that inherits the state from this injector.

        All bindings are inherited. In the future this may become closer to
        child injectors on google-guice.
        """
        binder = self._binder.create_child()
        return Injector(modules, binder=binder, stage=self._stage)

    def create_object(self, cls):
        kwargs = {}
        for param in extract_params(cls.__init__):
            kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
        return cls(**kwargs)

    def inject_members(self, instance):
        # this may be a little slow; done twice
        for method_name in getattr(instance.__class__, "__guice_methods__", []):
            kwargs = {}
            method = getattr(instance, method_name)
            for param in extract_params(method):
                kwargs[param.name] = self.get_instance(param.dtype, param.annotation)
            method(**kwargs)
        return instance


def create_injector(modules):
    """Factory for creating Injector instances."""
    return Injector(modules)
