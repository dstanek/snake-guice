"""
Regression tests for injection when from __future__ import annotations is active.

Under PEP 563 (from __future__ import annotations) all annotations in the module
are stored as strings rather than evaluated types.  inject() must still resolve
them to real types so the injector can look up bindings.
"""
from __future__ import annotations

from snakeguice import create_injector, inject
from snakeguice.interfaces import Binder


class Engine:
    pass


class V8Engine(Engine):
    pass


class Car:
    @inject
    def __init__(self, engine: Engine) -> None:
        self.engine = engine


class EngineModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(Engine, to=V8Engine)


def test_inject_works_with_future_annotations() -> None:
    injector = create_injector([EngineModule()])
    car = injector.get_instance(Car)
    assert isinstance(car.engine, V8Engine)
