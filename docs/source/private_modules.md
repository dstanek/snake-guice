# Private Modules

Every `binder.bind()` call in a normal module adds to one shared binder. That's
fine until two modules each need their *own* binding for the same interface -
each binder only allows one binding per `(interface, annotation)` key, so the
second call is recorded as a configuration error and `create_injector()` raises
`BindingError` (specifically `CreationError`) once every module has run. This
is sometimes called the "robot legs" problem, after the classic Guice example -
but it shows up in ordinary applications too.

## The Problem

Say an application talks to both a primary database and a read replica. Each
connection needs its own `IConnectionConfig` (different host, credentials,
etc.), but both modules binding `IConnectionConfig` directly collides:

```python
from snakeguice import create_injector
from snakeguice.errors import BindingError
from snakeguice.interfaces import Binder


class IConnectionConfig:
    """Interface for a database connection configuration."""


class PrimaryConfig(IConnectionConfig):
    host = "db-primary.internal"


class ReplicaConfig(IConnectionConfig):
    host = "db-replica.internal"


class PrimaryModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)


class ReplicaModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=ReplicaConfig)


try:
    create_injector([PrimaryModule(), ReplicaModule()])
except BindingError as e:
    print(e)
    # 1 error while creating an injector:
    #
    # 1) baseclass <class 'IConnectionConfig'> already bound
    #   at File path/to/module.py, line 17, in configure
    #       binder.bind(IConnectionConfig, to=ReplicaConfig)
```

Annotating the two `IConnectionConfig` bindings (`"primary"` /
`"replica"`) would avoid the collision, but then *every* class that depends on
`IConnectionConfig` - including `Database` below - would need
`@annotate` to say which one it wants, even though each `Database` instance
only ever uses one.

## Isolating Bindings with `PrivateModule`

`snakeguice.PrivateModule` is a `Module` whose `configure(binder)`
receives a *private* binder, backed by its own child injector. Bindings made
there - like `IConnectionConfig` - aren't visible to the parent binder or to
other modules, so two `PrivateModule`s can each bind `IConnectionConfig` to a
different implementation without colliding, and `Database` doesn't need to
know which one it got.

To make a binding visible outside the private module, call
`self.expose(binder, interface, annotation)`. This adds a binding to the
*parent* binder that, when resolved, delegates to the private injector:

```python
from snakeguice import annotate, inject, PrivateModule
from snakeguice.modules import Module


class IDatabase:
    """Interface for a database connection."""


class Database(IDatabase):
    @inject
    def __init__(self, config: IConnectionConfig) -> None:
        self.config = config


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


injector = create_injector([AppModule()])
repo = injector.get_instance(UserRepository)

assert isinstance(repo.primary.config, PrimaryConfig)
assert isinstance(repo.replica.config, ReplicaConfig)
```

`IConnectionConfig` is bound twice - once per private module - with no
conflict, because each `PrivateModule` has its own binder. Only `IDatabase`
(annotated `"primary"` and `"replica"`) is exposed to `AppModule`'s binder,
which is where `UserRepository` resolves it. `Database` itself depends on the
unannotated `IConnectionConfig` and never has to care which database it ended
up talking to.

```{warning}
The binding passed to `expose(binder, interface, annotation)` must also exist
in the private module *under that same `(interface, annotation)` key* - here,
`binder.bind(IDatabase, annotated_with="primary", to=Database)` inside
`PrimaryDatabaseModule`.

If the private binder has no binding for the exposed key, `create_injector()`
raises `CreationError` immediately with a message identifying the missing key.
```
