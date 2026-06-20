from typing import Any

import pytest

from snakeguice import create_injector, inject, providers
from snakeguice.errors import MultiBindingError
from snakeguice.interfaces import Binder
from snakeguice.multibinder import DictBinder, ListBinder


class ISnack:
    """A snack interface."""


class Twix:
    """A concrete snack implementation."""


class Snickers:
    """A concrete snack implementation."""


class Skittles:
    """A concrete snack implementation."""


class Lays:
    """A concrete snack implementation."""


class Tostitos:
    """A concrete snack implementation."""


class Ruffles:
    """A concrete snack implementation."""


class ListCandyModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[ISnack])
        listbinder.add_binding(to=Twix)
        provider = providers.create_simple_provider(Snickers)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Skittles())


class ListChipsModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[ISnack])
        listbinder.add_binding(to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Ruffles())


class ListSnackMachine:
    @inject
    def __init__(self, snacks: list[ISnack]) -> None:
        self.snacks = snacks


class DictCandyModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, ISnack])
        dictbinder.add_binding("twix", to=Twix)
        provider = providers.create_simple_provider(Snickers)
        dictbinder.add_binding("snickers", to_provider=provider)
        dictbinder.add_binding("skittles", to_instance=Skittles())


class DictChipsModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, ISnack])
        dictbinder.add_binding("lays", to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        dictbinder.add_binding("tostitos", to_provider=provider)
        dictbinder.add_binding("ruffles", to_instance=Ruffles())


class DictSnackMachine:
    @inject
    def __init__(self, snacks: dict[str, ISnack]) -> None:
        self.snacks = snacks


SNACK_CLASSES = (Twix, Snickers, Skittles, Lays, Tostitos, Ruffles)


class BaseMultibinder:
    snack_machine: Any  # TODO: remove this

    def test_that_the_injected_value_has_the_correct_number_of_elements(self) -> None:
        assert len(self.snack_machine.snacks) == len(SNACK_CLASSES)


class TestUsingListBinder(BaseMultibinder):
    def setup_method(self) -> None:
        injector = create_injector([ListCandyModule(), ListChipsModule()])
        self.snack_machine = injector.get_instance(ListSnackMachine)

    def test_that_the_elements_have_the_correct_type(self) -> None:
        for n, snack in enumerate(self.snack_machine.snacks):
            assert isinstance(snack, SNACK_CLASSES[n])


class TestUsingDictBinder(BaseMultibinder):
    def setup_method(self) -> None:
        injector = create_injector([DictCandyModule(), DictChipsModule()])
        self.snack_machine = injector.get_instance(DictSnackMachine)

    def test_that_the_elements_have_the_correct_type(self) -> None:
        for k, v in self.snack_machine.snacks.items():
            assert k == v.__class__.__name__.lower()
            assert v.__class__ in SNACK_CLASSES


class DuplicateKeyModule:
    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, ISnack])
        dictbinder.add_binding("twix", to=Twix)
        dictbinder.add_binding("twix", to=Snickers)


def test_dict_binder_raises_multi_binding_error_on_duplicate_key() -> None:
    with pytest.raises(MultiBindingError) as exc_info:
        create_injector([DuplicateKeyModule()])

    assert "twix" in str(exc_info.value)


# Ensure no child ListBinder/DictBinder contributions leak back into the parent.
# Adding a binding through a child injector used to mutate class-level provider
# state shared with the parent, so the parent would resolve the child's bindings.


class ChildListModule:
    """Adds one extra snack binding via a child injector."""

    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[ISnack])
        listbinder.add_binding(to=Ruffles)


def test_list_binder_child_does_not_affect_parent() -> None:
    parent = create_injector([ListCandyModule()])
    parent_snacks_before = parent.get_instance(ListSnackMachine).snacks

    child = parent.create_child([ChildListModule()])
    child_snacks = child.get_instance(ListSnackMachine).snacks

    parent_snacks_after = parent.get_instance(ListSnackMachine).snacks

    # child should include the extra binding
    assert len(child_snacks) == len(parent_snacks_before) + 1
    # parent must not be affected by the child's extra binding
    assert len(parent_snacks_after) == len(parent_snacks_before)


class ChildDictModule:
    """Adds one extra snack binding via a child injector."""

    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, ISnack])
        dictbinder.add_binding("ruffles", to=Ruffles)


def test_dict_binder_child_does_not_affect_parent() -> None:
    parent = create_injector([DictCandyModule()])
    parent_snacks_before = parent.get_instance(DictSnackMachine).snacks

    child = parent.create_child([ChildDictModule()])
    child_snacks = child.get_instance(DictSnackMachine).snacks

    parent_snacks_after = parent.get_instance(DictSnackMachine).snacks

    # child should include the extra binding
    assert set(child_snacks.keys()) == set(parent_snacks_before.keys()) | {"ruffles"}
    # parent must not be affected by the child's extra binding
    assert set(parent_snacks_after.keys()) == set(parent_snacks_before.keys())


# Multibinder keys are compared by exact type, so list[T] and typing.List[T] are
# different keys.  The docs previously used typing.List/typing.Dict; they now use
# the builtin forms.  These tests guard that the builtin forms work correctly and
# serve as a reminder that typing.List / typing.Dict must not be mixed in.


class SingleListCandyModule:
    """Registers one binding under list[ISnack] (builtin generic, as docs now show)."""

    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[ISnack])
        listbinder.add_binding(to=Twix)


class SingleListSnackMachine:
    @inject
    def __init__(self, snacks: list[ISnack]) -> None:
        self.snacks = snacks


def test_list_binder_builtin_generic_matches_injection() -> None:
    injector = create_injector([SingleListCandyModule()])
    machine = injector.get_instance(SingleListSnackMachine)
    assert len(machine.snacks) == 1
    assert isinstance(machine.snacks[0], Twix)


class SingleDictCandyModule:
    """Registers one binding under dict[str, ISnack] (builtin generic)."""

    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, ISnack])
        dictbinder.add_binding("twix", to=Twix)


class SingleDictSnackMachine:
    @inject
    def __init__(self, snacks: dict[str, ISnack]) -> None:
        self.snacks = snacks


def test_dict_binder_builtin_generic_matches_injection() -> None:
    injector = create_injector([SingleDictCandyModule()])
    machine = injector.get_instance(SingleDictSnackMachine)
    assert "twix" in machine.snacks
    assert isinstance(machine.snacks["twix"], Twix)


# Falsey to_instance values (False, 0, "", [], {}) must be accepted, not rejected.


class FalseyListModule:
    def configure(self, binder: Binder) -> None:
        lb = ListBinder(binder, list[object])
        lb.add_binding(to_instance=False)
        lb.add_binding(to_instance=0)
        lb.add_binding(to_instance="")


class FalseyListConsumer:
    @inject
    def __init__(self, items: list[object]) -> None:
        self.items = items


class SnickersProvider:
    def get(self) -> Snickers:
        return Snickers()


class TwixProvider:
    def get(self) -> Twix:
        return Twix()


class ListProviderInstanceModule:
    def configure(self, binder: Binder) -> None:
        lb = ListBinder(binder, list[ISnack])
        lb.add_binding(to_provider=SnickersProvider())
        lb.add_binding(to_provider=TwixProvider())


def test_list_binder_accepts_provider_instance() -> None:
    injector = create_injector([ListProviderInstanceModule()])
    machine = injector.get_instance(ListSnackMachine)
    assert len(machine.snacks) == 2
    assert isinstance(machine.snacks[0], Snickers)
    assert isinstance(machine.snacks[1], Twix)


class DictProviderInstanceModule:
    def configure(self, binder: Binder) -> None:
        db = DictBinder(binder, dict[str, ISnack])
        db.add_binding("snickers", to_provider=SnickersProvider())
        db.add_binding("twix", to_provider=TwixProvider())


def test_dict_binder_accepts_provider_instance() -> None:
    injector = create_injector([DictProviderInstanceModule()])
    machine = injector.get_instance(DictSnackMachine)
    assert isinstance(machine.snacks["snickers"], Snickers)
    assert isinstance(machine.snacks["twix"], Twix)


def test_list_binder_accepts_falsey_to_instance_values() -> None:
    injector = create_injector([FalseyListModule()])
    consumer = injector.get_instance(FalseyListConsumer)
    assert consumer.items == [False, 0, ""]


class FalseyDictModule:
    def configure(self, binder: Binder) -> None:
        db = DictBinder(binder, dict[str, object])
        db.add_binding("flag", to_instance=False)
        db.add_binding("count", to_instance=0)
        db.add_binding("label", to_instance="")


class FalseyDictConsumer:
    @inject
    def __init__(self, items: dict[str, object]) -> None:
        self.items = items


def test_dict_binder_accepts_falsey_to_instance_values() -> None:
    injector = create_injector([FalseyDictModule()])
    consumer = injector.get_instance(FalseyDictConsumer)
    assert consumer.items == {"flag": False, "count": 0, "label": ""}
