from typing import Dict, List

from snakeguice import create_injector, inject, providers
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

    def configure(self, binder):
        listbinder = ListBinder(binder, List[ISnack])
        listbinder.add_binding(to=Twix)
        provider = providers.create_simple_provider(Snickers)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Skittles())


class ListChipsModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        listbinder = ListBinder(binder, List[ISnack])
        listbinder.add_binding(to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Ruffles())


class ListSnackMachine:
    @inject
    def __init__(self, snacks: List[ISnack]):
        self.snacks = snacks


class DictCandyModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        dictbinder = DictBinder(binder, Dict[str, ISnack])
        dictbinder.add_binding("twix", to=Twix)
        provider = providers.create_simple_provider(Snickers)
        dictbinder.add_binding("snickers", to_provider=provider)
        dictbinder.add_binding("skittles", to_instance=Skittles())


class DictChipsModule:
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        dictbinder = DictBinder(binder, Dict[str, ISnack])
        dictbinder.add_binding("lays", to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        dictbinder.add_binding("tostitos", to_provider=provider)
        dictbinder.add_binding("ruffles", to_instance=Ruffles())


class DictSnackMachine:
    @inject
    def __init__(self, snacks: Dict[str, ISnack]):
        self.snacks = snacks


SNACK_CLASSES = (Twix, Snickers, Skittles, Lays, Tostitos, Ruffles)


class BaseMultibinder:
    def test_that_the_injected_value_has_the_correct_number_of_elements(self):
        assert len(self.snack_machine.snacks) == len(SNACK_CLASSES)


class TestUsingListBinder(BaseMultibinder):
    def setup(self):
        injector = create_injector([ListCandyModule(), ListChipsModule()])
        self.snack_machine = injector.get_instance(ListSnackMachine)

    def test_that_the_elements_have_the_correct_type(self):
        for n, snack in enumerate(self.snack_machine.snacks):
            assert isinstance(snack, SNACK_CLASSES[n])


class TestUsingDictBinder(BaseMultibinder):
    def setup(self):
        injector = create_injector([DictCandyModule(), DictChipsModule()])
        self.snack_machine = injector.get_instance(DictSnackMachine)

    def test_that_the_elements_have_the_correct_type(self):
        for k, v in self.snack_machine.snacks.items():
            assert k == v.__class__.__name__.lower()
            assert v.__class__ in SNACK_CLASSES
