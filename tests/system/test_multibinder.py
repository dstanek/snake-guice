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
