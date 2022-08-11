from typing import Any, Callable, Type, TypeVar

from snakeguice import inject
from snakeguice._extractor import extract_params
from snakeguice.errors import AssistError
from snakeguice.interfaces import Factory, Injector, ProviderFactory

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


def assisted_inject(*params: str) -> Callable[[F], F]:
    def _assisted_inject(method: F) -> F:
        if method.__name__ != "__init__":
            raise AssistError("assisted_inject can only be used on __init__s")

        setattr(method, "__guice_assisted__", set(params))

        return method

    return _assisted_inject


def AssistProvider(cls: Type[T]) -> Type[ProviderFactory[T]]:
    if not getattr(cls.__init__, "__guice_assisted__", None):
        raise AssistError(
            "AssistProvider can only by used on " "@assisted_inject-ed classes"
        )

    class _AssistProvider:
        @inject
        def __init__(self, injector: Injector) -> None:
            self._injector = injector

        def get(self) -> Factory[T]:
            return build_factory(self._injector, cls)

    return _AssistProvider


def build_factory(injector, cls):
    assisted_params: set[str] = getattr(cls.__init__, "__guice_assisted__", set())

    providers = {}
    for param in extract_params(cls.__init__):
        if param.name in assisted_params:
            continue
        providers[param.name] = injector.get_provider(param.dtype, param.annotation)

    class DynamicFactory:
        # TODO: this really should be based on some provided interface to get the
        #       benefits or optional static typing
        def create(self, **kwargs):
            if set(kwargs.keys()) - assisted_params:
                raise TypeError(
                    "TODO: error message here about too many values %r %r",
                    kwargs,
                    assisted_params,
                )

            for name, provider in providers.items():
                kwargs[name] = provider.get()
            return cls(**kwargs)

    return DynamicFactory()
