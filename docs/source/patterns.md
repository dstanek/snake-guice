# Dependency Injection Patterns

This page is a cookbook: short recipes for common DI patterns, each with a
pointer to the page that covers it in depth and - where one exists - to the
place it's used in [`examples/fastapi_tasks/`](../../examples/fastapi_tasks/),
a pair of small REST APIs that implement the same Tasks API once with
FastAPI's native `Depends()` and once with snake-guice. That example's
[`design.md`](../../examples/fastapi_tasks/design.md) has a feature-by-feature
table mapping several of these patterns to exact files and lines, alongside
the native equivalent.

Patterns that snake-guice *doesn't* support are listed separately in
[What's Missing](future.md).

## Bind an interface to an implementation (`to=`)

The basic binding: when something needs `IEngine`, construct a
`SmallBlockEngine`.

```python
class AutoModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)
```

Full explanation: [Guice Basics](guicebasics.md).

**In `examples/fastapi_tasks`:** `ClockModule` binds `Clock` to `SystemClock`
(`fastapi_snakeguice/modules.py`).

## Constructor injection (`@inject`)

Declare what a class needs as type-annotated `__init__` parameters; the
injector supplies them.

```python
class Car:
    @inject
    def __init__(self, engine: IEngine) -> None:
        self.engine = engine
```

Full explanation: [Guice Basics — Simple Example](guicebasics.md#simple-example).

**In `examples/fastapi_tasks`:** every service, repository, and listener -
e.g. `TaskService.__init__` (`fastapi_snakeguice/service.py`).

## Multiple bindings via annotations (`@annotate` / `annotated_with=`)

When several constructor parameters share an interface but need different
implementations, annotate the parameters and the bindings to disambiguate.

```python
class Car:
    @inject
    @annotate(left_door="left", right_door="right")
    def __init__(self, engine: IEngine, left_door: IDoor, right_door: IDoor) -> None:
        ...
```

Full explanation: [Guice Basics — Multiple Bindings Using
Annotations](guicebasics.md#multiple-bindings-using-annotations).

**In `examples/fastapi_tasks`:** `TaskRepository.__init__` is `@inject
@annotate(reader="reader", writer="writer")`, resolving two independently
scoped `Session`s (`fastapi_snakeguice/repository.py`).

## Bind to a pre-built instance (`to_instance=`)

When an object already exists - or must be constructed outside the injector -
bind it directly instead of asking snake-guice to build one.

```python
binder.bind(IDatabase, to_instance=self._database)
```

Full explanation: [User Guide — The Binder DSL](userguide.md#the-binder-dsl).

**In `examples/fastapi_tasks`:** `ReaderDatabaseModule`/`WriterDatabaseModule`
each eagerly construct one `Database` and bind it with `to_instance=`, so the
reader and writer never collide on - or share - `scopes.SINGLETON`'s
process-global cache for unannotated `IDatabase`
(`fastapi_snakeguice/modules.py`; rationale in `fastapi_snakeguice/db.py`).

## Custom providers (`to_provider=`)

When building a value takes logic - not just constructing a class - write a
small `Provider` (anything with a `get()` method) and bind to it.

```python
class TurboEngineProvider:
    def get(self) -> IEngine:
        engine = SmallBlockEngine()
        engine.add_turbo()
        return engine


binder.bind(IEngine, to_provider=TurboEngineProvider)
```

Full explanation: [Using Providers](using_providers.md).

**In `examples/fastapi_tasks`:** `_SessionProvider` wraps
`IDatabase.get_session()` and is bound `to_provider=_SessionProvider` for both
the reader and writer `Session` bindings (`fastapi_snakeguice/modules.py`).

## Factory methods on a module (`@provides`)

For a one-off value that needs a couple of dependencies but doesn't warrant a
whole provider class, decorate a module method instead.

```python
class AutoModule:
    @provides(IDashboard)
    @inject
    def provide_dashboard(self, engine: IEngine) -> IDashboard:
        return Dashboard(redline=engine.max_rpm)
```

Full explanation: [Using Providers — `@provides`: Factory Methods on a
Module](using_providers.md#provides-factory-methods-on-a-module).

**Not used in `examples/fastapi_tasks`** - every binding there needs
`annotated_with=` or `in_scope=`, and `@provides` supports neither (see
[What's Missing](future.md)).

## Singleton scope (`scopes.SINGLETON`)

Build an instance once per `(interface, annotation)` key and reuse it for the
life of the process.

```python
binder.bind(IEngine, to=SmallBlockEngine, in_scope=scopes.SINGLETON)
```

Full explanation: [User Guide — Scopes](userguide.md#scopes) - read the
warning about the global cache before reaching for this.

**In `examples/fastapi_tasks`:** `ClockModule` binds `Clock` to `SystemClock`
`in_scope=scopes.SINGLETON` - safe because `SystemClock` is stateless, so
sharing the cache across `create_app()` calls causes no harm
(`fastapi_snakeguice/modules.py`).

## Custom scopes

Any object with a `scope(key, provider) -> Provider` method can be passed to
`in_scope=`. This is how to express lifetimes `NO_SCOPE`/`SINGLETON` don't
cover - "one per request" being the most common.

```python
class RequestScope:
    def scope(self, key: Key, provider: Provider[Any]) -> Provider[Any]:
        ...
```

Full explanation: [Extending — Custom Scopes](extending.md#custom-scopes).

**In `examples/fastapi_tasks`:** `FastAPIRequestScope` caches one `Session`
per request in a `ContextVar`, applied to both the reader and writer `Session`
bindings; `main.py`'s middleware resets the cache and closes sessions at the
end of each request (`fastapi_snakeguice/scopes.py`).

## Per-instance singleton scope (avoiding `SINGLETON`'s global cache)

When you want "one instance for the life of *this* injector" rather than "one
instance for the life of the *process*" - e.g. so two `create_app()` calls in
the same test run don't share state - write a scope with its own private
cache.

```python
class PerAppSingleton:
    def __init__(self) -> None:
        self._cache: Dict[Key, Any] = {}

    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        if key not in self._cache:
            self._cache[key] = provider.get()
        return create_instance_provider(self._cache[key])()
```

Full explanation: [User Guide — Scopes
warning](userguide.md#scopes) and [Extending — Custom
Scopes](extending.md#custom-scopes).

**In `examples/fastapi_tasks`:** `PerAppSingleton` gives `MetricsCollector` its
own per-`create_app()` cache, since `scopes.SINGLETON`'s cache is
process-global and keyed only by `(interface, annotation)` - using it for
`MetricsCollector` would leak counters between apps (and tests)
(`fastapi_snakeguice/scopes.py`, used by `MetricsModule` in
`fastapi_snakeguice/modules.py`).

## Isolating bindings with `PrivateModule` ("robot legs")

When two modules each need their own binding for the same interface - and
neither should have to be annotated everywhere it's used - give each its own
`PrivateModule` and `expose()` only what the rest of the app needs.

```python
class PrimaryDatabaseModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(IConnectionConfig, to=PrimaryConfig)
        binder.bind(IDatabase, annotated_with="primary", to=Database)
        self.expose(binder, IDatabase, "primary")
```

Full explanation: [Private Modules](private_modules.md) - including the
`expose()`/recursion gotcha to watch for.

**In `examples/fastapi_tasks`:** `ReaderDatabaseModule`/`WriterDatabaseModule`
are `PrivateModule`s that each privately bind `IDatabase` and an annotated
`Session`, exposing only the annotated `Session` to the parent
(`fastapi_snakeguice/modules.py`).

## Composing modules (`install()`)

Split bindings across multiple small modules, then have one top-level module
install them all against the same binder.

```python
class AppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, EngineModule())
        self.install(binder, DashboardModule())
```

Full explanation: [User Guide — Modules and Binders](userguide.md#modules-and-binders).

**In `examples/fastapi_tasks`:** `AppModule.configure` installs
`ReaderDatabaseModule`, `WriterDatabaseModule`, `ClockModule`, `AuditModule`,
and `MetricsModule` (`fastapi_snakeguice/modules.py`).

## Multibindings (`ListBinder` / `DictBinder`)

Let several independent modules each contribute one implementation to a
shared `List[T]` or `Dict[str, T]`, without any of them knowing about the
others.

```python
class EngineModule:
    def configure(self, binder: Binder) -> None:
        ListBinder(binder, List[IWarningLight]).add_binding(to=CheckEngineLight)
```

Full explanation: [Multibindings](multibinder.md).

**In `examples/fastapi_tasks`:** `AuditModule` and `MetricsModule` each
contribute one `TaskListener` to a shared `List[TaskListener]` via
`ListBinder` - `TaskService` just sees the combined list
(`fastapi_snakeguice/modules.py`). `DictBinder` isn't used in this example; see
[Multibindings — `DictBinder`](multibinder.md#dictbinder) for a runnable
`Dict[str, T]` example.

## Assisted injection (`@assisted_inject` + `AssistProvider`)

When a class needs *some* parameters from the injector and others only known
at call time (a customer's name, a date, ...), mark the call-time parameters
and get a factory for the rest.

```python
class ServiceTicket:
    @assisted_inject("customer_name", "issue")
    @inject
    def __init__(self, mechanic: IMechanic, customer_name: str, issue: str) -> None:
        ...
```

Full explanation: [Assisted Injection](assisted_injection.md).

**Not used in `examples/fastapi_tasks`** - nothing there needs "inject most
constructor args, pass the rest at call time." See `tests/test_assist.py` for
a runnable example.

## Parameter interceptors

When one method needs a dependency resolved fresh on *every call*, without
making it part of the class's constructor, wrap the method with
`ParameterInterceptor`.

```python
class Garage:
    @intercept(key_card=IKeyCard, annotation="master")
    def open(self, key_card: Any = None) -> str:
        return f"opened with {type(key_card).__name__}"
```

Full explanation: [Parameter Interceptors](parameter_interceptors.md).

**Not used in `examples/fastapi_tasks`.** See `tests/system/test_api.py` for a
runnable example.

## Configuration injection

Bind values loaded from an `.ini` file so they can be injected like anything
else.

```python
class Database:
    @inject
    def __init__(self, dsn: config.Config("app.ini:db:dsn")) -> None:
        self.dsn = dsn
```

Full explanation: [Injecting Configuration](injecting_configuration.md).

**Not used in `examples/fastapi_tasks`** - its `db_path` is passed directly to
`AppModule.__init__` rather than loaded from a config file. See
`tests/test_config.py` for a runnable example.

## Deferred resolution (`get_provider()`)

When you're holding onto an injector and want to defer resolution - a fresh
instance each time, or to avoid building something until it's needed - ask for
a provider instead of an instance.

```python
provider = injector.get_provider(IEngine)
...
engine = provider.get()  # resolved now, not when get_provider() was called
```

Full explanation: [Using Providers — Deferred Resolution with
`get_provider`](using_providers.md#deferred-resolution-with-get_provider).

**Not used directly in `examples/fastapi_tasks`** - `deps.py`'s
`get_task_service`/`get_metrics` call `injector.get_instance(...)`
immediately, since FastAPI's own `Depends()` already provides per-request
deferral (`fastapi_snakeguice/deps.py`).

## Swapping implementations for tests

Because dependent classes only ever see interfaces, a test module can bind
fakes in place of real implementations without changing the class under test.

```python
class TestModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=FakeEngine)
```

Full explanation: [User Guide — Why It Matters: Swapping Implementations in
Tests](userguide.md#why-it-matters-swapping-implementations-in-tests), and
[User Guide — Child Injectors](userguide.md#child-injectors) for overriding
just *some* bindings via `create_child()`.

**In `examples/fastapi_tasks`:** not via fakes - both apps talk to a real
SQLite database - but the same idea: `test_fastapi_tasks_api.py` builds a
fresh `AppModule`/`Injector` per test, pointed at a `tmp_path`-backed database,
so each test gets its own object graph instead of sharing one injector's
cached state.
