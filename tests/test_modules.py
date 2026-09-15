#!/usr/bin/env python

"""
Unit tests for snakeguice.modules -- ProvidesBinderHelper.bind_providers()'s
scan of @provides methods (must not evaluate module properties as a side
effect) and its interaction with subclassed modules.
"""

from snakeguice import create_injector, inject, provides
from snakeguice.interfaces import Binder


class _Svc:
    pass


class PropertyModule:
    """A module with a @property that must never be evaluated by
    bind_providers() -- only @provides methods are candidates."""

    def __init__(self) -> None:
        self.property_evaluated = False

    def configure(self, binder: Binder) -> None:
        pass

    @property
    def dangerous(self) -> str:
        self.property_evaluated = True
        raise AssertionError(
            "module property must not be evaluated during binding scan"
        )

    @provides(_Svc)
    def provide_svc(self) -> _Svc:
        return _Svc()


def test_bind_providers_does_not_evaluate_module_properties() -> None:
    """Scanning a module for @provides methods must not touch unrelated
    @property attributes -- getattr()-based scans (inspect.getmembers)
    evaluate every property as a side effect, which can raise or have
    effects unrelated to configuration."""

    module = PropertyModule()

    injector = create_injector([module])

    assert module.property_evaluated is False
    assert isinstance(injector.get_instance(_Svc), _Svc)


class _Base:
    pass


class _Sub(_Base):
    pass


class _WidgetModule:
    def configure(self, binder: Binder) -> None:
        pass

    @provides(_Base)
    def provide_base(self) -> _Base:
        return _Base()


def test_provides_method_inherited_from_base_module_class_still_binds() -> None:
    """A @provides method defined on a base module class must still be
    found and bound when a subclass (with no @provides of its own) is
    used to configure the injector."""

    class SubModule(_WidgetModule):
        pass

    injector = create_injector([SubModule()])

    assert isinstance(injector.get_instance(_Base), _Base)


def test_provides_method_overridden_in_subclass_binds_override_exactly_once() -> None:
    """A subclass overriding a @provides method for the same type must bind
    the override -- and only once. Scanning both the base's and the
    subclass's definitions of the same method name would trip the
    "already bound" duplicate-key error."""

    class OverridingModule(_WidgetModule):
        @provides(_Base)
        def provide_base(self) -> _Base:
            return _Sub()

    injector = create_injector([OverridingModule()])

    assert isinstance(injector.get_instance(_Base), _Sub)


class _GrandparentModule:
    def __init__(self) -> None:
        self.calls: list[str] = []

    @inject
    def set_a(self) -> None:
        self.calls.append("grandparent:set_a")


class _ParentModule(_GrandparentModule):
    @inject
    def set_b(self) -> None:
        self.calls.append("parent:set_b")


class _ChildModule(_ParentModule):
    # Overrides set_a -- the grandparent's set_a must not also run.
    @inject
    def set_a(self) -> None:
        self.calls.append("child:set_a")

    @inject
    def set_c(self) -> None:
        self.calls.append("child:set_c")


class _GrandchildModule(_ChildModule):
    pass


def test_method_injection_order_is_stable_across_instances_and_subclass() -> None:
    """The per-class @inject method order (most-derived definition of a
    name wins, every name across the MRO runs exactly once) must be
    identical every time it's computed for a given class, and independent
    of another class's plan -- guarding a per-class cache of the ordered
    method list against mixing up two different classes' plans or reusing
    a stale one.

    This test does not pin the exact sequence set_a/set_b/set_c run in --
    that ordering has a separately tracked issue -- only that whatever
    order is produced is deterministic and consistent between a class and
    an identical subclass.
    """

    injector = create_injector([])

    first = injector.get_instance(_ChildModule)
    second = injector.get_instance(_ChildModule)
    sub_first = injector.get_instance(_GrandchildModule)
    sub_second = injector.get_instance(_GrandchildModule)

    expected_names = {"grandparent:set_a", "child:set_a", "parent:set_b", "child:set_c"}
    for calls in (first.calls, second.calls, sub_first.calls, sub_second.calls):
        # The override wins -- the grandparent's set_a must not also run.
        assert "grandparent:set_a" not in calls
        assert set(calls) == expected_names - {"grandparent:set_a"}
        # Each method runs exactly once per instance.
        assert len(calls) == len(set(calls))

    assert first.calls == second.calls
    assert sub_first.calls == sub_second.calls
    assert first.calls == sub_first.calls
