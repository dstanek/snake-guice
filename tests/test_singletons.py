#!/usr/bin/env python

"""
Tests for the singleton scope.py
"""

from snakeguice import Injector, annotate, inject, scopes
from snakeguice.interfaces import Injector as InjectorI

from . import cls_heirarchy as ch


class TestSingletonScope:
    class DomainObject:
        @inject
        def set_loggers(
            self, logger_a: ch.Logger, logger_b: ch.Logger, logger_c: ch.Logger
        ) -> None:
            self.logger_a = logger_a
            self.logger_b = logger_b
            self.logger_c = logger_c

        @inject
        @annotate(place_a="hot")
        def set_place_a(self, place_a: ch.Place) -> None:
            self.place_a = place_a

        @inject
        @annotate(place_b="hot")
        def set_place_b(self, place_b: ch.Place) -> None:
            self.place_b = place_b

        @inject
        @annotate(place_c="cold")
        def set_place_c(self, place_c: ch.Place) -> None:
            self.place_c = place_c

        @inject
        @annotate(place_d="cold")
        def set_place_d(self, place_d: ch.Place) -> None:
            self.place_d = place_d

    class SimpleClass:
        @inject
        def __init__(self, place: ch.Place) -> None:
            self.place = place

    def assert_obj(self, obj) -> None:
        assert obj.logger_a is obj.logger_b
        assert obj.logger_b is obj.logger_c
        assert obj.place_a is obj.place_b
        assert obj.place_c is obj.place_d
        assert obj.place_a is not obj.place_d

    def test_to_instance(self) -> None:
        class MyModule:
            def configure(self, binder):
                binder.bind(ch.Logger, to_instance=ch.ConcreteLogger())
                binder.bind(ch.Place, annotated_with="hot", to_instance=ch.Beach())
                binder.bind(ch.Place, annotated_with="cold", to_instance=ch.Glacier())

        obj = Injector(MyModule()).get_instance(self.DomainObject)
        self.assert_obj(obj)

    def _test_inject_into_singleton(self):
        class MyLogger:
            hot_place = inject(ch.Place, annotation="hot")
            cold_place = inject(ch.Place, annotation="cold")

        class MyModule:
            def configure(self, binder):
                binder.bind(ch.Logger, to=MyLogger, in_scope=scopes.SINGLETON)
                binder.bind(
                    ch.Place,
                    annotated_with="hot",
                    to=ch.Beach,
                    to_scope=scopes.SINGLETON,
                )
                binder.bind(
                    ch.Place,
                    annotated_with="cold",
                    to=ch.Glacier,
                    to_scope=scopes.SINGLETON,
                )

        obj = Injector(MyModule()).get_instance(self.DomainObject)
        self.assert_obj(obj)
        assert obj.logger_a.hot_place is obj.place_a
        assert obj.logger_a.cold_place is obj.place_c


class TestSingetonScope:
    class SimpleClass:
        @inject
        def __init__(self, place: ch.Place) -> None:
            self.place = place

    def test_simple_singleton_to(self) -> None:
        SINGLETON = scopes._Singleton()

        class MyModule:
            def configure(self, binder) -> None:
                binder.bind(ch.Place, to=ch.Beach, in_scope=SINGLETON)

        injector = Injector([MyModule()])
        obj0 = injector.get_instance(self.SimpleClass)
        obj1 = injector.get_instance(self.SimpleClass)
        assert obj0.place is obj1.place

    def test_simple_singleton_to_provider(self) -> None:
        SINGLETON = scopes._Singleton()

        class PlaceProvider:
            def get(self) -> ch.Place:
                return ch.Beach()

        class MyModule:
            def configure(self, binder) -> None:
                binder.bind(ch.Place, to_provider=PlaceProvider, in_scope=SINGLETON)

        injector = Injector([MyModule()])
        obj0 = injector.get_instance(self.SimpleClass)
        obj1 = injector.get_instance(self.SimpleClass)
        assert obj0.place is obj1.place

    def test_simple_singleton_to_injectable_provider(self) -> None:
        SINGLETON = scopes._Singleton()

        class PlaceProvider:
            def __init__(self, injector: InjectorI) -> None:
                self._injector = injector

            def get(self) -> ch.Place:
                return self._injector.get_instance(ch.Beach)

        class MyModule:
            def configure(self, binder) -> None:
                binder.bind(ch.Place, to_provider=PlaceProvider, in_scope=SINGLETON)

        injector = Injector([MyModule()])
        obj0 = injector.get_instance(self.SimpleClass)
        obj1 = injector.get_instance(self.SimpleClass)
        assert obj0.place is obj1.place
