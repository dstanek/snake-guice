from snakeguice import Injector as ConcreteInjector
from snakeguice import create_injector, inject
from snakeguice.interfaces import Binder, Injector


class ISomething:
    """An interface."""


class Something(ISomething):
    """Something a little more concrete."""


class SomethingProvider:
    @inject
    def __init__(self, injector: Injector) -> None:
        self.injector = injector

    def get(self) -> ISomething:
        return self.injector.get_instance(Something)


class Module:
    def configure(self, binder: Binder) -> None:
        binder.bind(ISomething, to_provider=SomethingProvider)


def test() -> None:
    injector = create_injector([Module()])
    something = injector.get_instance(ISomething)
    assert isinstance(something, Something)

    provider = injector.get_instance(SomethingProvider)
    assert provider.injector is injector


class NeedsConcreteInjector:
    @inject
    def __init__(self, injector: ConcreteInjector) -> None:
        self.injector = injector


class ConcreteInjectorProvider:
    @inject
    def __init__(self, injector: ConcreteInjector) -> None:
        self.injector = injector

    def get(self) -> ISomething:
        return self.injector.get_instance(Something)


class ConcreteModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(ISomething, to_provider=ConcreteInjectorProvider)


def test_concrete_injector_class() -> None:
    injector = create_injector([])
    obj = injector.get_instance(NeedsConcreteInjector)
    assert obj.injector is injector


def test_concrete_injector_class_via_provider() -> None:
    injector = create_injector([ConcreteModule()])
    provider = injector.get_instance(ConcreteInjectorProvider)
    assert provider.injector is injector
