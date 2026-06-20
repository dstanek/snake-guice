#!/usr/bin/env python

"""
injector module unit tests
"""

import pytest

from snakeguice import binder, create_injector, inject, injector
from snakeguice.errors import CreationError
from snakeguice.interfaces import Binder

from . import cls_heirarchy as ch


class FakeModule:
    def __init__(self) -> None:
        self.binder = None
        self.num_calls = 0

    def configure(self, binder: Binder) -> None:
        self.binder = binder
        self.num_calls += 1

    def was_called(self) -> bool:
        return bool(self.num_calls)


def test_injector_single_module_init() -> None:
    """Create an Injector that accepts a single Module instance."""

    module = FakeModule()
    inj = injector.Injector(module)
    assert isinstance(inj, injector.Injector)
    assert isinstance(module.binder, binder.Binder)


def test_injector_multi_module_init() -> None:
    """Create an Injector that accepts any number of Module instances."""

    modules = [FakeModule(), FakeModule(), FakeModule()]
    inj = injector.Injector(modules)
    assert isinstance(inj, injector.Injector)
    for module in modules:
        assert isinstance(module.binder, binder.Binder)


def test_create_child_binder_is_direct_child_of_parent_binder() -> None:
    """create_child() must not insert an extra intermediate binder layer."""
    parent = injector.Injector([])
    child = parent.create_child([])
    assert child._binder._parent is parent._binder


def test_create_child() -> None:
    """Create an injector child."""

    class ParentModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, to=ch.EvilPerson)

    class ChildModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Person, annotated_with="good", to=ch.GoodPerson)

    inj = injector.Injector(ParentModule())
    person = inj.get_instance(ch.Person)
    assert isinstance(person, ch.EvilPerson)

    child_inj = inj.create_child(ChildModule())
    person = child_inj.get_instance(ch.Person)
    assert isinstance(person, ch.EvilPerson)
    person = child_inj.get_instance(ch.Person, "good")
    assert isinstance(person, ch.GoodPerson)


def test_create_child_does_not_leak_overrides_back_to_parent() -> None:
    """Resolving an inherited binding via a child must not affect the parent.

    A child injector resolving an unscoped binding inherited from its parent
    used to cache a provider tied to the child, so the parent's later
    resolution of that same binding would incorrectly use the child's
    overridden dependencies.
    """

    class Wearer:
        @inject
        def __init__(self, place: ch.Place) -> None:
            self.place = place

    class ParentModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(Wearer, to=Wearer)
            binder.bind(ch.Place, to=ch.Beach)

    class ChildModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(ch.Place, to=ch.Glacier)

    parent = create_injector([ParentModule()])
    child = parent.create_child(ChildModule())

    child_wearer = child.get_instance(Wearer)
    parent_wearer = parent.get_instance(Wearer)

    assert isinstance(child_wearer.place, ch.Glacier)
    assert isinstance(parent_wearer.place, ch.Beach)


class Test_using_create_injector_factory:
    def setup_method(self) -> None:
        class PeopleModule:
            def configure(self, binder: Binder) -> None:
                binder.bind(ch.Person, to=ch.EvilPerson)

        self.injector = create_injector([PeopleModule()])
        self.instance = self.injector.get_instance(ch.Person)

    def test_an_injector_was_returned(self) -> None:
        assert isinstance(self.injector, injector.Injector)

    def test_correct_instance_was_created(self) -> None:
        assert isinstance(self.instance, ch.EvilPerson)


# TODO: implement this test
# def test_create_an_injector_without_any_modules():
#     modules = [FakeModule(), FakeModule(), FakeModule()]


def test_add_modules_raises_creation_error_on_duplicate_binding() -> None:
    """add_modules() must raise CreationError just like the constructor does."""

    class IThing:
        pass

    class Thing(IThing):
        pass

    class DuplicateModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(IThing, to=Thing)
            binder.bind(IThing, to=Thing)

    inj = create_injector([])
    with pytest.raises(CreationError):
        inj.add_modules([DuplicateModule()])


class Test_using_get_provider:
    def setup_method(self) -> None:
        class PeopleModule:
            def configure(self, binder: Binder) -> None:
                binder.bind(ch.Person, to=ch.EvilPerson)

        self.injector = create_injector([PeopleModule()])
        self.provider = self.injector.get_provider(ch.Person)
        self.instance = self.provider.get()

    def test_provider_provides_an_instance(self) -> None:
        assert isinstance(self.instance, ch.EvilPerson)
