from snakeguice import create_injector, inject, annotate
from snakeguice.interfaces import Injector
from snakeguice.multibinder import ListBinder, List, DictBinder, Dict
from snakeguice import providers
from snakeguice import scopes


class ISnack(object):
    """A snack interface."""


class Twix(object):
    """A concrete snack implementation."""


class Snickers(object):
    """A concrete snack implementation."""


class Skittles(object):
    """A concrete snack implementation."""


class Lays(object):
    """A concrete snack implementation."""


class Tostitos(object):
    """A concrete snack implementation."""


class Ruffles(object):
    """A concrete snack implementation."""


class ListCandyModule(object):
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        listbinder = ListBinder(binder, ISnack)
        listbinder.add_binding(to=Twix)
        provider = providers.create_simple_provider(Snickers)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Skittles())


class ListChipsModule(object):
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        listbinder = ListBinder(binder, ISnack)
        listbinder.add_binding(to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        listbinder.add_binding(to_provider=provider)
        listbinder.add_binding(to_instance=Ruffles())


class ListSnackMachine(object):

    @inject(snacks=List(ISnack))
    def __init__(self, snacks):
        self.snacks = snacks


class DictCandyModule(object):
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        dictbinder = DictBinder(binder, ISnack)
        dictbinder.add_binding('twix', to=Twix)
        provider = providers.create_simple_provider(Snickers)
        dictbinder.add_binding('snickers', to_provider=provider)
        dictbinder.add_binding('skittles', to_instance=Skittles())


class DictChipsModule(object):
    """One to two modules adding to the multibinder."""

    def configure(self, binder):
        dictbinder = DictBinder(binder, ISnack)
        dictbinder.add_binding('lays', to=Lays)
        provider = providers.create_simple_provider(Tostitos)
        dictbinder.add_binding('tostitos', to_provider=provider)
        dictbinder.add_binding('ruffles', to_instance=Ruffles())


class DictSnackMachine(object):

    @inject(snacks=Dict(ISnack))
    def __init__(self, snacks):
        self.snacks = snacks


SNACK_CLASSES = (Twix, Snickers, Skittles, Lays, Tostitos, Ruffles)


class base_multibinder(object):

    def test_that_the_injected_value_has_the_correct_number_of_elements(self):
        assert len(self.snack_machine.snacks) == len(SNACK_CLASSES)


class test_using_ListBinder(base_multibinder):

    def setup(self):
        injector = create_injector([ListCandyModule(), ListChipsModule()])
        self.snack_machine = injector.get_instance(ListSnackMachine)

    def test_that_the_elements_have_the_correct_type(self):
        for n, snack in enumerate(self.snack_machine.snacks):
            assert isinstance(snack, SNACK_CLASSES[n])

    def test_that_items_are_created_in_scope(self):
        class MyListChipsModule(object):
            def configure(self, binder):
                listbinder = ListBinder(binder, ISnack)
                listbinder.add_binding(to=Lays, in_scope=scopes.SINGLETON)
                provider = providers.create_simple_provider(Tostitos)
                listbinder.add_binding(to_provider=provider, in_scope=scopes.SINGLETON)
                listbinder.add_binding(to_instance=Ruffles(), in_scope=scopes.SINGLETON)
        injector = create_injector([ListCandyModule(), MyListChipsModule()])
        snacks1 = injector.get_instance(ListSnackMachine)
        snacks2 = injector.get_instance(ListSnackMachine)
        for n, snack in enumerate(snacks1.snacks):
            if isinstance(snack, Lays) or \
                isinstance(snack, Tostitos) or \
                isinstance(snack, Ruffles):
                assert snack is snacks2.snacks[n]

    def test_using_annotation_on_ListBinder(self):
        class MyListChipsModule(object):
            def configure(self, binder):
                listbinder = ListBinder(binder, ISnack, annotated_with='FritoLaySnackMachine')
                provider = providers.create_simple_provider(Tostitos)
                listbinder.add_binding(to_provider=provider, in_scope=scopes.SINGLETON)
                listbinder.add_binding(to_instance=Ruffles(), in_scope=scopes.SINGLETON)
        class MySnackMachine(object):
            @inject(snacks=List(ISnack))
            @annotate(snacks='FritoLaySnackMachine')
            def __init__(self, snacks):
                self.snacks = snacks
        injector = create_injector([ListChipsModule(), MyListChipsModule()])
        snacks1 = injector.get_instance(ListSnackMachine)
        snacks2 = injector.get_instance(MySnackMachine, annotation='FritoLaySnackMachine')
        assert len(snacks2.snacks) == 2

class test_using_DictBinder(base_multibinder):

    def setup(self):
        injector = create_injector([DictCandyModule(), DictChipsModule()])
        self.snack_machine = injector.get_instance(DictSnackMachine)

    def test_that_the_elements_have_the_correct_type(self):
        for k, v in self.snack_machine.snacks.items():
            assert k == v.__class__.__name__.lower()
            assert v.__class__ in SNACK_CLASSES

    def test_that_items_are_created_in_scope(self):
        class MyDictChipsModule(object):
            def configure(self, binder):
                listbinder = DictBinder(binder, ISnack)
                listbinder.add_binding('Lays', to=Lays, in_scope=scopes.SINGLETON)
                provider = providers.create_simple_provider(Tostitos)
                listbinder.add_binding('Tostitos', to_provider=provider, in_scope=scopes.SINGLETON)
                listbinder.add_binding('Ruffles', to_instance=Ruffles(), in_scope=scopes.SINGLETON)
        injector = create_injector([DictCandyModule(), MyDictChipsModule()])
        snacks1 = injector.get_instance(DictSnackMachine)
        snacks2 = injector.get_instance(DictSnackMachine)
        for k, snack in snacks1.snacks.iteritems():
            if isinstance(snack, Lays) or \
                isinstance(snack, Tostitos) or \
                isinstance(snack, Ruffles):
                assert snack is snacks2.snacks[k]

    def test_using_annotation_on_DictBinder(self):
        class MyDictChipsModule(object):
            def configure(self, binder):
                dictbinder = DictBinder(binder, ISnack, annotated_with='FritoLaySnackMachine')
                provider = providers.create_simple_provider(Tostitos)
                dictbinder.add_binding('Tostitos', to_provider=provider, in_scope=scopes.SINGLETON)
                dictbinder.add_binding('Ruffles', to_instance=Ruffles(), in_scope=scopes.SINGLETON)
        class MySnackMachine(object):
            @inject(snacks=Dict(ISnack))
            @annotate(snacks='FritoLaySnackMachine')
            def __init__(self, snacks):
                self.snacks = snacks
        injector = create_injector([DictChipsModule(), MyDictChipsModule()])
        snacks1 = injector.get_instance(DictSnackMachine)
        snacks2 = injector.get_instance(MySnackMachine, annotation='FritoLaySnackMachine')
        assert len(snacks2.snacks) == 2
