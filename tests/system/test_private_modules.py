import pytest

from snakeguice import PrivateModule, annotate, create_injector, inject
from snakeguice.errors import BindingError, CircularDependencyError, CreationError
from snakeguice.interfaces import Binder
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
