import inspect

from snakeguice import inject
from snakeguice._extractor import extract_params
from snakeguice.decorators import enclosing_frame
from snakeguice.errors import AssistError
from snakeguice.interfaces import Injector


def assisted_inject(*params):
    def _assisted_inject(method):
        if method.__name__ != "__init__":
            raise AssistError("assisted_inject can only be used on __init__s")

        class_locals = enclosing_frame().f_locals
        class_locals["__guice_assisted__"] = params

        return method

    return _assisted_inject


def AssistProvider(cls):
    if not getattr(cls, "__guice_assisted__", None):
        raise AssistError(
            "AssistProvider can only by used on " "@assisted_inject-ed classes"
        )

    class _AssistProvider:
        @inject(injector=Injector)
        def __init__(self, injector):
            self._injector = injector

        def get(self):
            return build_factory(self._injector, cls)

    return _AssistProvider


def build_factory(injector, cls):
    providers = {}
    for param in extract_params(cls.__init__):
        # if param in cls.__guice_assisted__:
        #    continue
        providers[param.name] = injector.get_provider(param.dtype, param.annotation)

    all_args = inspect.getargspec(cls.__init__).args[1:]
    needed_args = set(all_args) - set(providers.keys())

    class DynamicFactory:
        # TODO: this really should be based on some provided interface to get the
        #       benefits or optional static typing
        def create(self, **kwargs):
            if set(kwargs.keys()) - needed_args:
                raise TypeError("TODO: error message here about too many values")

            for name, provider in providers.items():
                kwargs[name] = provider.get()
            return cls(**kwargs)

    return DynamicFactory()
