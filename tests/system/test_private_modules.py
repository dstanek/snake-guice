import pytest

from snakeguice import annotate, create_injector, inject
from snakeguice.errors import BindingError
from snakeguice.interfaces import Binder
from snakeguice.modules import Module, PrivateModule


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


def test_expose_without_a_matching_private_binding_recurses() -> None:
    injector = create_injector([BrokenAppModule()])

    with pytest.raises(RecursionError):
        injector.get_instance(IDatabase, "replica")


class UnannotatedConfigModule(PrivateModule):
    """Binds and exposes IConnectionConfig without an annotation."""

    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        self.expose(binder, IConnectionConfig)


def test_expose_without_an_annotation_resolves_the_private_binding() -> None:
    injector = create_injector([UnannotatedConfigModule()])

    config = injector.get_instance(IConnectionConfig)

    assert isinstance(config, PrimaryConfig)
