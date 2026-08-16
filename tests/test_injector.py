#!/usr/bin/env python

"""
injector module unit tests
"""

import pytest

from snakeguice import (
    annotate,
    binder,
    create_injector,
    inject,
    injector,
    provides,
    scopes,
)
from snakeguice.assist import AssistProvider, assisted_inject
from snakeguice.errors import CircularDependencyError, CreationError
from snakeguice.interfaces import Binder
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.modules import Module

from . import cls_heirarchy as ch


class _SelfCycle:
    @inject
    def __init__(self, other: "_SelfCycle") -> None:
        self.other = other


class _CycleA:
    @inject
    def __init__(self, b: "_CycleB") -> None:
        self.b = b


class _CycleB:
    @inject
    def __init__(self, a: _CycleA) -> None:
        self.a = a


class _TransA:
    @inject
    def __init__(self, b: "_TransB") -> None:
        self.b = b


class _TransB:
    @inject
    def __init__(self, c: "_TransC") -> None:
        self.c = c


class _TransC:
    @inject
    def __init__(self, a: _TransA) -> None:
        self.a = a


class _AnnCycle:
    @inject
    @annotate(other="left")
    def __init__(self, other: "_AnnCycle") -> None:
        self.other = other


class _OffsetRoot:
    @inject
    def __init__(self, mid: "_OffsetMid") -> None:
        self.mid = mid


class _OffsetMid:
    @inject
    def __init__(self, loop1: "_OffsetLoop1") -> None:
        self.loop1 = loop1


class _OffsetLoop1:
    @inject
    def __init__(self, loop2: "_OffsetLoop2") -> None:
        self.loop2 = loop2


class _OffsetLoop2:
    @inject
    def __init__(self, loop1: _OffsetLoop1) -> None:
        self.loop1 = loop1


class _ProvidesX:
    pass


class _ProvidesY:
    @inject
    def __init__(self, x: _ProvidesX) -> None:
        self.x = x


class _ProvidesModule(Module):
    def configure(self, binder: Binder) -> None:
        pass

    @provides(_ProvidesX)
    def provide_x(self, y: _ProvidesY) -> _ProvidesX:
        return _ProvidesX()


class _MethodCycleA:
    other: "_MethodCycleB"

    @inject
    def set_other(self, other: "_MethodCycleB") -> None:
        self.other = other


class _MethodCycleB:
    @inject
    def __init__(self, a: _MethodCycleA) -> None:
        self.a = a


class _ToProviderTarget:
    pass


class _ToProviderCycle:
    @inject
    def __init__(self, target_injector: InjectorI) -> None:
        self._injector = target_injector

    def get(self) -> "_ToProviderTarget":
        return self._injector.get_instance(_ToProviderTarget)


class _ToProviderModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(_ToProviderTarget, to_provider=_ToProviderCycle)


class _AssistedFactory:
    pass


class _AssistedB:
    @inject
    @assisted_inject("name")
    def __init__(self, a: "_AssistedA", name: str) -> None:
        self.a = a
        self.name = name


class _AssistedA:
    @inject
    def __init__(self, factory: _AssistedFactory) -> None:
        # Calls create() synchronously, while _AssistedA's own key is still
        # on the resolving stack.
        self.b = factory.create(name="x")  # type: ignore[attr-defined]


class _AssistedModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(_AssistedFactory, to_provider=AssistProvider(_AssistedB))


_MULTI_SINGLETON = scopes.Singleton()


class _MultiOk:
    pass


class _MultiCycleX:
    @inject
    def __init__(self, y: "_MultiCycleY") -> None:
        self.y = y


class _MultiCycleY:
    @inject
    def __init__(self, x: _MultiCycleX) -> None:
        self.x = x


class _Multi:
    @inject
    def __init__(self, ok: _MultiOk, bad: _MultiCycleX) -> None:
        self.ok = ok
        self.bad = bad


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


def test_self_cycle_raises_circular_dependency_error() -> None:
    """A class that depends on itself must be detected, not blow the stack."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError, match=r"_SelfCycle -> _SelfCycle"):
        inj.get_instance(_SelfCycle)


def test_direct_cycle_raises_circular_dependency_error() -> None:
    """A -> B -> A must be detected, not blow the stack."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError) as exc_info:
        inj.get_instance(_CycleA)

    message = str(exc_info.value)
    assert "_CycleA" in message
    assert "_CycleB" in message
    assert "->" in message


def test_transitive_cycle_raises_circular_dependency_error() -> None:
    """A -> B -> C -> A must be detected, not blow the stack."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError) as exc_info:
        inj.get_instance(_TransA)

    message = str(exc_info.value)
    for name in ("_TransA", "_TransB", "_TransC"):
        assert name in message


def test_annotated_cycle_message_includes_the_annotation() -> None:
    """The chain must remain readable when an annotation is involved."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError, match=r"_AnnCycle\['left'\]"):
        inj.get_instance(_AnnCycle)


def test_circular_dependency_error_does_not_break_later_resolutions() -> None:
    """The resolving stack must be popped on failure, not leak across calls."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_SelfCycle)

    # A later, unrelated resolution must not be spuriously flagged.
    person = inj.get_instance(ch.Person)
    assert isinstance(person, ch.Person)


def test_diamond_dependency_with_singleton_is_not_flagged_as_circular() -> None:
    """A -> B, C and B, C -> S (singleton) is legitimate, not circular.

    The two resolutions of S happen sequentially (B unwinds fully before C
    starts), never nested, so they must not trip the cycle detector.
    """

    SINGLETON = scopes.Singleton()

    class S:
        pass

    class B:
        @inject
        def __init__(self, s: S) -> None:
            self.s = s

    class C:
        @inject
        def __init__(self, s: S) -> None:
            self.s = s

    class A:
        @inject
        def __init__(self, b: B, c: C) -> None:
            self.b = b
            self.c = c

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(S, to=S, in_scope=SINGLETON)

    inj = injector.Injector(MyModule())
    a = inj.get_instance(A)
    assert a.b.s is a.c.s


def test_cycle_message_shows_full_path_when_cycle_starts_below_the_root() -> None:
    """Root -> Mid -> Loop1 -> Loop2 -> Loop1: the whole path to the repeat
    must appear, in order, not just the repeated segment."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError) as exc_info:
        inj.get_instance(_OffsetRoot)

    message = str(exc_info.value)
    assert "_OffsetRoot" in message
    assert "_OffsetMid" in message
    first = message.index("_OffsetLoop1")
    middle = message.index("_OffsetLoop2")
    last = message.rindex("_OffsetLoop1")
    assert first < middle < last


def test_cycle_through_provides_method_is_detected() -> None:
    """A @provides factory that (transitively) needs its own product must be
    detected, not blow the stack."""

    inj = injector.Injector(_ProvidesModule())
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_ProvidesX)


def test_cycle_through_method_injection_is_detected() -> None:
    """A cycle realized via @inject method injection (inject_members), not
    just constructor injection, must still be detected."""

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_MethodCycleA)


def test_cycle_through_to_provider_binding_is_detected() -> None:
    """A hand-written to_provider= provider that re-enters the injector for
    its own key must be detected."""

    inj = injector.Injector(_ToProviderModule())
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_ToProviderTarget)


def test_cycle_through_assisted_injection_create_is_detected() -> None:
    """A synchronous, nested call to an assisted factory's .create() that
    loops back to a class still under construction must be detected."""

    inj = injector.Injector(_AssistedModule())
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_AssistedA)


def test_cycle_in_singleton_scoped_binding_is_detected_and_does_not_cache() -> None:
    """A cycle between two SINGLETON-scoped bindings must be detected, and
    must not poison the singleton cache for unrelated keys."""

    class MyModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(_MultiCycleX, to=_MultiCycleX, in_scope=_MULTI_SINGLETON)
            binder.bind(_MultiCycleY, to=_MultiCycleY, in_scope=_MULTI_SINGLETON)
            binder.bind(_MultiOk, to=_MultiOk, in_scope=_MULTI_SINGLETON)

    inj = injector.Injector(MyModule())
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_MultiCycleX)

    ok = inj.get_instance(_MultiOk)
    assert isinstance(ok, _MultiOk)


def test_stack_is_clean_after_a_cycle_nested_under_a_partial_success() -> None:
    """A class with two constructor params where the first resolves fine and
    the second triggers a cycle: after the failure propagates, the resolving
    stack must be empty, an unrelated key must resolve, and re-resolving the
    same failing key must still raise (not silently succeed on stale state).
    """

    inj = injector.Injector([])
    with pytest.raises(CircularDependencyError):
        inj.get_instance(_Multi)

    assert inj._resolving == []

    ok = inj.get_instance(_MultiOk)
    assert isinstance(ok, _MultiOk)

    with pytest.raises(CircularDependencyError):
        inj.get_instance(_MultiCycleX)

    assert inj._resolving == []


def test_cycle_in_a_child_injector_is_detected() -> None:
    """A cycle confined entirely to a child injector must be detected."""

    parent = injector.Injector([])
    child = parent.create_child([])
    with pytest.raises(CircularDependencyError):
        child.get_instance(_SelfCycle)


def test_resolving_the_same_key_in_child_then_parent_is_not_flagged() -> None:
    """Parent and child injectors keep independent resolving stacks, so
    sequentially resolving the same key on each is not a false positive."""

    class Widget:
        pass

    parent = injector.Injector([])
    child = parent.create_child([])

    child.get_instance(Widget)
    parent.get_instance(Widget)
