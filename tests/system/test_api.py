#!/usr/bin/env python

"""
Examples of using the snakeguice API.
"""

# TODO: add a test proving call throughs work

from typing import Any, Optional, Type, cast

import pytest

from snakeguice import Injector, ParameterInterceptor, annotate, inject, provides
from snakeguice.interfaces import Binder

from .. import cls_heirarchy as ch


def test_unbound_class_is_implicitly_instantiated() -> None:
    injector = Injector([])
    person = injector.get_instance(ch.Person)
    assert isinstance(person, ch.Person)


def test_injector_simple() -> None:
    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to=ch.EvilPerson)

    injector = Injector(MyModule())
    person = injector.get_instance(ch.Person)
    assert isinstance(person, ch.EvilPerson)


def test_annotated_injector() -> None:
    class DomainObject:
        @inject
        @annotate(person0="good", person1="evil")
        def __init__(
            self, person0: ch.Person, person1: ch.Person, person2: ch.Person
        ) -> None:
            self.person0 = person0
            self.person1 = person1
            self.person2 = person2

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(DomainObject, to=DomainObject)
            binder.bind(ch.Person, annotated_with="evil", to=ch.EvilPerson)
            binder.bind(ch.Person, annotated_with="good", to=ch.GoodPerson)

    injector = Injector(MyModule())
    obj = injector.get_instance(DomainObject)
    assert isinstance(obj.person0, ch.GoodPerson)
    assert isinstance(obj.person1, ch.EvilPerson)
    assert isinstance(obj.person2, ch.Person)


def test_annotations() -> None:
    class DomainObject:
        @inject
        @annotate(hero="good", villian="evil")
        def __init__(
            self, hero: ch.Person, villian: ch.Person, victim: ch.Person
        ) -> None:
            self.hero = hero
            self.villian = villian
            self.victim = victim

    class ByStander(ch.Person):
        pass

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, annotated_with="evil", to=ch.EvilPerson)
            binder.bind(ch.Person, annotated_with="good", to=ch.GoodPerson)
            binder.bind(ch.Person, to=ByStander)

    injector = Injector(MyModule())
    obj = injector.get_instance(DomainObject)
    assert isinstance(obj.hero, ch.GoodPerson)
    assert isinstance(obj.villian, ch.EvilPerson)
    assert isinstance(obj.victim, ByStander)


def test_injector_injecting_a_provider() -> None:
    class SimpleProvider:
        def get(self) -> ch.Person:
            return ch.GoodPerson()

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to=SimpleProvider)

    injector = Injector(MyModule())
    person_provider = cast(SimpleProvider, injector.get_instance(ch.Person))
    assert isinstance(person_provider.get(), ch.GoodPerson)


def test_injector_injecting_from_a_provider() -> None:
    class SimpleProvider:
        def get(self) -> ch.Person:
            return ch.GoodPerson()

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to_provider=SimpleProvider)

    injector = Injector(MyModule())
    person = injector.get_instance(ch.Person)
    assert isinstance(person, ch.GoodPerson)


def Xtest_collision() -> None:
    """TODO: figure out what to do with this"""


def test_inject_provider_with_args() -> None:
    class PersonProvider:
        def get(self, typ: str) -> Optional[Type[ch.Person]]:
            if typ == "good":
                return ch.GoodPerson
            elif typ == "evil":
                return ch.EvilPerson
            else:
                return None

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to=PersonProvider)

    injector = Injector(MyModule())
    person_provider = cast(PersonProvider, injector.get_instance(ch.Person))
    assert person_provider.get("good") == ch.GoodPerson
    assert person_provider.get("evil") == ch.EvilPerson
    assert person_provider.get("clueless") is None


def test_inject_decorator() -> None:
    class DomainObject:
        @inject
        def __init__(self, logger: ch.Logger) -> None:
            assert isinstance(logger, ch.ConcreteLogger)

        @inject
        def do_something(self, person: ch.Person) -> None:
            assert isinstance(person, ch.EvilPerson)

        @inject
        def multiple(self, logger: ch.Logger, person: ch.Person) -> None:
            assert isinstance(person, ch.EvilPerson)
            assert isinstance(logger, ch.ConcreteLogger)

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to=ch.EvilPerson)
            binder.bind(ch.Logger, to=ch.ConcreteLogger)

    injector = Injector(MyModule())
    injector.get_instance(DomainObject)


class TestMethodInterceptors:
    def setup_method(self) -> None:
        class MyModule:
            def configure(self, binder: Binder) -> None:
                binder.bind(ch.Person, to=ch.EvilPerson)
                binder.bind(ch.Logger, to_instance=ch.ConcreteLogger())
                binder.bind(ch.Person, annotated_with="good", to=ch.GoodPerson)
                binder.bind(ch.Person, annotated_with="evil", to=ch.EvilPerson)

        self.injector = Injector(MyModule())
        self.interceptor = ParameterInterceptor(self.injector)

    def test_noargs(self) -> None:
        class DomainObject:
            @self.interceptor(person=ch.Person, annotation="evil")
            def intercept_me(self, person: Any) -> None:
                assert isinstance(person, ch.EvilPerson)

        obj = self.injector.get_instance(DomainObject)
        obj.intercept_me()

    def test_args(self) -> None:
        class DomainObject:
            @self.interceptor(person=ch.Person, annotation="evil")
            def intercept_me(
                self,
                arg0: Any,
                kwarg0: Any = None,
                kwarg1: Any = None,
                person: Any = None,
            ) -> None:
                assert arg0 == 0
                assert kwarg0 == 1
                assert kwarg1 is None
                assert isinstance(person, ch.EvilPerson)

        obj = self.injector.get_instance(DomainObject)
        obj.intercept_me(0, kwarg0=1)

    def test_stacking(self) -> None:
        class DomainObject:
            @self.interceptor(person0=ch.Person, annotation="good")
            @self.interceptor(person1=ch.Person, annotation="evil")
            def intercept_me(self, person0: Any, person1: Any) -> None:
                assert isinstance(person0, ch.GoodPerson)
                assert isinstance(person1, ch.EvilPerson)

        obj = self.injector.get_instance(DomainObject)
        obj.intercept_me()

    def test_more_than_one_kwarg_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            self.interceptor(a=ch.Person, b=ch.Logger)

    def test_default_annotation_resolves_the_unannotated_binding(self) -> None:
        class DomainObject:
            @self.interceptor(person=ch.Person)
            def intercept_me(self, person: Any) -> None:
                assert isinstance(person, ch.EvilPerson)

        obj = self.injector.get_instance(DomainObject)
        obj.intercept_me()


class TestProvidesDecorator:
    def setup_method(self) -> None:
        class Person:
            def get_home_location(self) -> ch.Place:
                raise NotImplementedError

        class HappyPerson(Person):
            def get_home_location(self) -> ch.Place:
                return ch.Beach()

        class PeopleModule:
            def configure(self, binder: Binder) -> None:
                binder.bind(Person, to=HappyPerson)

            @provides(ch.Place)
            @inject
            def provide_a_persons_home_location(self, person: Person) -> ch.Place:
                return person.get_home_location()

        self.injector = Injector(PeopleModule())
        self.location = self.injector.get_instance(ch.Place)

    def test_the_location_was_injected(self) -> None:
        assert isinstance(self.location, ch.Beach)


# TODO: constant injection

# TODO: provider injection
