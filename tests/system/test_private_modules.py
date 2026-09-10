import pytest

from snakeguice import PrivateModule, annotate, create_injector, inject, scopes
from snakeguice.errors import (
    BindingError,
    CircularDependencyError,
    CreationError,
    MissingBindingError,
)
from snakeguice.interfaces import Binder
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.modules import Module


class IConnectionConfig:
    """Interface for a database connection configuration."""


class PrimaryConfig(IConnectionConfig):
    host = "db-primary.internal"


class ReplicaConfig(IConnectionConfig):
    host = "db-replica.internal"


class IDatabase:
    """Interface for a database connection."""


class Database(IDatabase):
    @inject
    def __init__(self, config: IConnectionConfig) -> None:
        self.config = config


def test_binding_the_same_interface_twice_on_one_binder_raises() -> None:
    class PrimaryModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(IConnectionConfig, to=PrimaryConfig)

    class ReplicaModule:
        def configure(self, binder: Binder) -> None:
            binder.bind(IConnectionConfig, to=ReplicaConfig)

    with pytest.raises(BindingError):
        create_injector([PrimaryModule(), ReplicaModule()])


class PrimaryDatabaseModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        binder.bind(IDatabase, annotated_with="primary", to=Database)
        self.expose(binder, IDatabase, "primary")


class ReplicaDatabaseModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=ReplicaConfig)
        binder.bind(IDatabase, annotated_with="replica", to=Database)
        self.expose(binder, IDatabase, "replica")


class UserRepository:
    @inject
    @annotate(primary="primary", replica="replica")
    def __init__(self, primary: IDatabase, replica: IDatabase) -> None:
        self.primary = primary
        self.replica = replica


class AppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrimaryDatabaseModule())
        self.install(binder, ReplicaDatabaseModule())


def test_private_modules_isolate_bindings_and_expose_the_rest() -> None:
    injector = create_injector([AppModule()])
    repo = injector.get_instance(UserRepository)

    assert isinstance(repo.primary, Database)
    assert isinstance(repo.replica, Database)
    assert isinstance(repo.primary.config, PrimaryConfig)
    assert isinstance(repo.replica.config, ReplicaConfig)


class BrokenReplicaDatabaseModule(PrivateModule):
    """Exposes IDatabase under an annotation it never binds privately."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=ReplicaConfig)
        binder.bind(IDatabase, to=Database)
        self.expose(binder, IDatabase, "replica")


class BrokenAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrimaryDatabaseModule())
        self.install(binder, BrokenReplicaDatabaseModule())


def test_expose_without_a_matching_private_binding_raises_at_creation() -> None:
    msg = r"replica.*has no matching private binding"
    with pytest.raises(CreationError, match=msg):
        create_injector([BrokenAppModule()])


class UnannotatedConfigModule(PrivateModule):
    """Binds and exposes IConnectionConfig without an annotation."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        self.expose(binder, IConnectionConfig)


def test_expose_without_an_annotation_resolves_the_private_binding() -> None:
    injector = create_injector([UnannotatedConfigModule()])

    config = injector.get_instance(IConnectionConfig)

    assert isinstance(config, PrimaryConfig)


class HiddenDatabaseModule(PrivateModule):
    """Binds IDatabase privately, under an annotation, but never exposes it."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        binder.bind(IDatabase, annotated_with="hidden", to=Database)


class HiddenAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, HiddenDatabaseModule())


def test_private_binding_never_exposed_is_invisible_to_the_parent() -> None:
    """A key bound inside a private module but never passed to expose() must
    stay invisible to the parent injector -- under the old fall-through
    behavior an unexposed annotated key would silently implicitly-construct
    a plausible but wrong instance; now it must raise MissingBindingError."""

    injector = create_injector([HiddenAppModule()])

    with pytest.raises(MissingBindingError, match=r"hidden"):
        injector.get_instance(IDatabase, "hidden")


class IInner:
    """Interface for a cycle that lives entirely inside a private module."""


class IInnerOther:
    """The other half of the internal cycle."""


class InnerImpl(IInner):
    @inject
    def __init__(self, other: IInnerOther) -> None:
        self.other = other


class InnerOtherImpl(IInnerOther):
    @inject
    def __init__(self, inner: IInner) -> None:
        self.inner = inner


class CyclicPrivateModule(PrivateModule):
    """Both bindings, and the cycle between them, are entirely private.

    Exposing IInner doesn't matter here -- the cycle never crosses the
    private/parent boundary, it's confined to the private injector.
    """

    def configure(self, binder: Binder) -> None:
        binder.bind(IInner, to=InnerImpl)
        binder.bind(IInnerOther, to=InnerOtherImpl)
        self.expose(binder, IInner)


class CyclicPrivateAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, CyclicPrivateModule())


def test_cycle_entirely_inside_a_private_module_is_detected() -> None:
    """A genuine cycle confined to one private module's own bindings must
    still raise CircularDependencyError, not RecursionError -- the
    per-injector resolving stack has to work for the private injector too.
    """

    injector = create_injector([CyclicPrivateAppModule()])

    with pytest.raises(CircularDependencyError):
        injector.get_instance(IInner)


class IK:
    """Exposed by PrivA; its implementation depends on IL, exposed by PrivB."""


class IL:
    """Exposed by PrivB; its implementation depends on IK, exposed by PrivA."""


class KImpl(IK):
    @inject
    def __init__(self, ell: IL) -> None:
        self.ell = ell


class LImpl(IL):
    @inject
    def __init__(self, k: IK) -> None:
        self.k = k


class PrivA(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IK, to=KImpl)
        self.expose(binder, IK)


class PrivB(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IL, to=LImpl)
        self.expose(binder, IL)


class CrossPrivateAppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, PrivA())
        self.install(binder, PrivB())


def test_cycle_spanning_two_private_modules_expose_boundaries_is_detected() -> None:
    """IK (exposed by PrivA) depends on IL (exposed by PrivB) depends back on
    IK: a cycle that crosses two separate expose() boundaries must still be
    detected, since every hop through an expose() provider always re-enters
    that private module's own (consistent) injector instance.
    """

    injector = create_injector([CrossPrivateAppModule()])

    with pytest.raises(CircularDependencyError):
        injector.get_instance(IK)


def test_cycle_spanning_two_private_modules_message_marks_the_expose_hops() -> None:
    """This cycle crosses two expose() boundaries (PrivA -> PrivB -> PrivA),
    so _format_chain() must mark each hop rather than render an unmarked
    "->" that would read like the false positive it isn't. The label is the
    neutral "[different injector]": a frame only records the injector it was
    resolved on, so an expose() hop and a plain create_child() hop are
    indistinguishable at format time (see
    test_injector.test_cross_injector_cycle_via_create_child_is_not_mislabeled_private_module
    for the create_child() side of that)."""

    injector = create_injector([CrossPrivateAppModule()])

    with pytest.raises(CircularDependencyError) as exc_info:
        injector.get_instance(IK)

    message = str(exc_info.value)
    # the cycle crosses PrivA -> PrivB -> PrivA, i.e. two injector hops
    assert message.count("[different injector]") >= 2


class Marker:
    pass


# One process-wide Singleton() instance, shared across every run of
# ReusedPrivateModule.configure() below -- deliberately, to show that
# scopes.Singleton's cache is keyed by the per-run Binding object (B3), not
# by this shared scope instance, so reusing it doesn't merge the two
# private injectors' caches.
_MARKER_SCOPE = scopes.Singleton()


class ReusedPrivateModule(PrivateModule):
    """A single instance of this is deliberately passed to two separate
    create_injector() calls below -- see B5."""

    def configure(self, binder: Binder) -> None:
        binder.bind(Marker, to=Marker, in_scope=_MARKER_SCOPE)
        self.expose(binder, Marker)


def test_reusing_a_private_module_across_two_injectors_keeps_them_independent() -> None:
    """Regression test for B5: run_configure() used to store
    original_binder/private_injector on the *module instance*, and the
    expose() provider closure read private_injector back off the module at
    resolution time -- so building a second injector from the same
    PrivateModule instance would silently repoint the first injector's
    exposed bindings into the second injector's private scope. Both
    injectors must resolve correctly and independently, even after the
    second one is built.
    """

    module = ReusedPrivateModule()

    i1 = create_injector([module])
    i2 = create_injector([module])

    # Resolved *after* i2 exists -- under the old bug, i1's exposed
    # provider would by now read module.private_injector == i2's private
    # injector, so m1 would incorrectly come out equal to m2.
    m1 = i1.get_instance(Marker)
    m2 = i2.get_instance(Marker)
    m1_again = i1.get_instance(Marker)

    assert type(m1) is Marker
    assert type(m2) is Marker
    assert m1 is not m2  # each injector's private scope is its own
    assert m1 is m1_again  # i1 keeps resolving through its OWN private injector


class InstalledSubModule:
    """A plain (non-Private) module installed *from inside* a
    PrivateModule.configure() -- see
    test_private_module_install_sees_the_parent_injector_not_the_private_child.
    """

    def configure(self, binder: Binder) -> None:
        pass


class InjectorRecordingPrivateModule(PrivateModule):
    def __init__(self) -> None:
        self.seen_injector: InjectorI | None = None

    def configure(self, binder: Binder) -> None:
        # Recorded here, not returned, since self._injector is only valid
        # for the duration of this configure() call.
        self.seen_injector = self._injector
        self.install(binder, InstalledSubModule())


def test_private_module_install_sees_the_parent_injector_not_the_private_child() -> (
    None
):
    """Regression test for B5's wrapper-indirection: run_configure() runs
    the module's own configure() *nested* one layer inside
    _PrivateModuleWrapper's own ModuleAdapter.configure() call for the
    private child injector -- so the innermost `_configuring` frame at the
    point configure() runs belongs to the wrapper, not to the module
    itself. self._injector (and anything configure() derives from it, like
    self.install()) must still resolve to the real PARENT injector, not
    the in-progress private child injector that wraps it.
    """

    module = InjectorRecordingPrivateModule()

    injector = create_injector([module])

    assert module.seen_injector is injector
