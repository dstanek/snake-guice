from snakeguice import create_injector, inject
from snakeguice.interfaces import Binder, Injector


class ISomething:
    """An interface."""


class Something:
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

    something = injector.get_instance(SomethingProvider)
    assert something.injector is injector
