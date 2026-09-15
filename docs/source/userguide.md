# User Guide

This guide goes one level deeper than [Guice Basics](guicebasics.md): how
`get_instance` actually resolves a class, how modules and binders fit
together, how child injectors share and override bindings, and how scopes
control instance lifetime. It builds on the `Car` / `IEngine` example from the
basics page, adding a couple of new pieces along the way:

```python
from snakeguice import inject
from snakeguice.interfaces import Binder


class IEngine:
    """Interface for a car engine."""


class SmallBlockEngine(IEngine):
    """A small block V8."""


class IDashboard:
    """Interface for a dashboard."""


class BasicDashboard(IDashboard):
    """A basic dashboard."""


class Car:
    @inject
    def __init__(self, engine: IEngine) -> None:
        self.engine = engine

    @inject
    def set_dashboard(self, dashboard: IDashboard) -> None:
        self.dashboard = dashboard
```

When you only need constructor injection and no method injection, `@inject` can
be placed on the class itself instead of on `__init__`:

```python
@inject
class Car:
    def __init__(self, engine: IEngine) -> None:
        self.engine = engine
```

The two forms are identical — the injector reads `__init__`'s type annotations
either way. If you also want `@inject` on other methods, keep `@inject` on
those methods regardless of which form you use for `__init__`.

## Resolving Instances

`injector.get_instance(cls, annotation)` builds a `Key` from `cls` and
`annotation` and looks it up in the binder:

- **Bound** - if a binding exists for that key, its provider is asked for an
  instance (passed through the binding's scope - see [Scopes](#scopes)
  below).
- **Unbound, unannotated** - if no binding exists and `annotation` is
  `UNANNOTATED`, snake-guice falls back to *implicit construction*: it calls
  `create_object(cls)`, which inspects `cls.__init__` and injects each
  annotated parameter, and then `inject_members(instance)`, which calls every
  `@inject`-decorated method (other than `__init__`) the same way.
- **Unbound, annotated** - if no binding exists for an annotated key,
  snake-guice raises `MissingBindingError` instead of implicitly constructing
  anything. An annotation names one specific binding; if there's no match,
  that's a mismatch to report loudly, not a signal to fall back and build a
  plausible-looking but unbound instance. See [Guice
  Basics](guicebasics.md#multiple-bindings-using-annotations) for why a plain
  string and an `Annotation` instance can produce two different keys here.

```python
from snakeguice import create_injector


class EngineModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)
        binder.bind(IDashboard, to=BasicDashboard)


injector = create_injector([EngineModule()])
car = injector.get_instance(Car)

assert isinstance(car.engine, SmallBlockEngine)     # via __init__
assert isinstance(car.dashboard, BasicDashboard)    # via set_dashboard
```

`Car` itself was never bound to anything, so it goes through implicit
construction: `__init__` gets its `IEngine`, and then `set_dashboard` is called
automatically with its `IDashboard`.

Method injection runs for both implicit construction and explicit `to=`
bindings — any class that snake-guice constructs is fully injected.

Injected methods run after `__init__`, base classes first and in declaration
order within each class. A method overridden in a subclass runs once, at the
subclass's position.

### Circular Dependencies

`get_instance()` tracks the chain of keys it's currently resolving. If
resolving a key requires resolving that same key again — directly, or
transitively through some chain of other bindings — it raises
`CircularDependencyError` (a `BindingError` subclass) instead of recursing
until Python raises `RecursionError`:

```python
class A:
    @inject
    def __init__(self, b: "B") -> None:
        self.b = b


class B:
    @inject
    def __init__(self, a: A) -> None:
        self.a = a


create_injector([]).get_instance(A)
```

```text
CircularDependencyError: Circular dependency detected:
  A -> B -> A
```

The message shows the full chain from the top-level `get_instance()` call, not
just the cyclic part, so it's clear what actually pulled in the bad subgraph.
An annotated key in the chain renders as `Name['annotation']`. Detection works
the same way through `@provides` methods, `@inject` method injection,
`to_provider=` bindings, assisted injection, and `SINGLETON`-scoped bindings —
anything that goes through `get_instance()`.

snake-guice detects cycles; it doesn't break them for you the way Guice can
with proxies for circular singletons. The standard Guice workaround still
applies here: depend on a `Provider[T]` instead of `T` for one side of the
cycle. [`get_provider()`](using_providers.md#deferred-resolution-with-get_provider)
defers the actual `get_instance()` call until `.get()` runs, so as long as
that happens later — e.g. inside a method, not in `__init__` — the cycle
never appears on the resolving stack at once.

### Default Parameter Values

When a parameter has a Python default value and no binding exists for its
type, snake-guice skips it and lets Python supply the default. If a binding
*does* exist, the binding wins:

```python
@inject
class Car:
    def __init__(self, engine: IEngine, name: str = "default") -> None:
        self.engine = engine
        self.name = name


# No binding for str → name stays "default"
car = create_injector([EngineModule()]).get_instance(Car)
assert car.name == "default"

# Explicit binding for str → binding overrides the default
class NameModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(str, to_instance="sport")

car = create_injector([EngineModule(), NameModule()]).get_instance(Car)
assert car.name == "sport"
```

This applies to both constructor injection and method injection. It lets
optional collaborators or low-value defaults stay in the signature without
requiring a binding for every parameter.

## Modules and Binders

A **module** is anything with a `configure(binder)` method - that's the
"simple module" shown above. `snakeguice.modules.Module` is a base class that
gives you `install()` for composing modules:

```python
from snakeguice.modules import Module


class EngineModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)


class DashboardModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(IDashboard, to=BasicDashboard)


class AppModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, EngineModule())
        self.install(binder, DashboardModule())


injector = create_injector([AppModule()])
```

`install()` runs the installed module's `configure()` against the same
binder, so `AppModule` ends up with both bindings. This is how larger
applications split bindings across files without losing the single binder
that the injector resolves against.

### The Binder DSL

`binder.bind(interface, ...)` takes one of three ways to satisfy the binding,
plus two optional modifiers:

| argument | meaning |
| --- | --- |
| `to=Implementation` | construct `Implementation` via the injector (implicit construction rules apply - see above) |
| `to_provider=Provider` | delegate to a `Provider`'s `get()` (see [Using Providers](using_providers.md)) |
| `to_instance=obj` | always return this exact object |
| `annotated_with=annotation` | disambiguate multiple bindings of the same interface (see [Guice Basics](guicebasics.md)) |
| `in_scope=scope` | control instance lifetime (see [Scopes](#scopes) below) |

Each `(interface, annotation)` pair - a `Key` - can only be bound once per
binder. Binding the same key twice is recorded as a configuration error and,
along with any other problems found while configuring the injector, raised as
a single `CreationError` (a `BindingError` subclass) once `create_injector()`
finishes running every module.

## Child Injectors

`injector.create_child(modules)` returns a new injector that inherits every
binding from its parent, plus whatever the child's own modules add. The child
can override a parent binding without changing what the parent resolves:

```python
class TurboEngine(IEngine):
    """A turbocharged engine."""


class ParentModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)
        binder.bind(IDashboard, to=BasicDashboard)


class ChildModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=TurboEngine)


parent = create_injector([ParentModule()])
child = parent.create_child(ChildModule())

assert isinstance(parent.get_instance(Car).engine, SmallBlockEngine)
assert isinstance(child.get_instance(Car).engine, TurboEngine)
```

Bindings the child *doesn't* override - like `IDashboard` here - resolve
exactly as they would on the parent.

## Scopes

A binding's scope decides how long the instance it produces lives. The
default, `scopes.NO_SCOPE`, is a pass-through: every resolution builds a fresh
instance.

```python
class NoScopeModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)
        binder.bind(IDashboard, to=BasicDashboard)


injector = create_injector([NoScopeModule()])
car1 = injector.get_instance(Car)
car2 = injector.get_instance(Car)
assert car1.engine is not car2.engine
```

`scopes.SINGLETON` builds the instance once and reuses it for every later
resolution of that `(interface, annotation)` key, *on that injector*:

```python
from snakeguice import scopes


class SingletonModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine, in_scope=scopes.SINGLETON)
        binder.bind(IDashboard, to=BasicDashboard)


injector = create_injector([SingletonModule()])
car1 = injector.get_instance(Car)
car2 = injector.get_instance(Car)
assert car1.engine is car2.engine
```

The cache lives on the `Binding`, not on the shared `scopes.SINGLETON` object
itself, so it's scoped to the injector the binding belongs to: two independent
`create_injector([SingletonModule()])` calls - two runs of a test, two
`create_app()`s - each get their own instance, even though both use the same
exported `scopes.SINGLETON`. A `create_child()` injector is the exception: it
shares a singleton its parent already created, the same as Guice, because
inheriting a parent's bindings is the point of a child injector.

```{note}
If you want one instance shared across *independent* injectors - not a
parent/child pair - `scopes.SINGLETON` won't do that; build the instance
yourself and bind it with `to_instance=`, which bypasses scoping entirely.
```

For state that must stay on one thread - a non-thread-safe client, say -
rather than one per injector, use `scopes.THREAD_LOCAL` instead:

```python
binder.bind(IHttpClient, to=RequestsSessionClient, in_scope=scopes.THREAD_LOCAL)
```

It caches one instance per thread per binding, and - like `SINGLETON` - never
resets itself; it isn't a request scope.

### Thread and Async Safety

An `Injector` is safe to call from multiple threads, or from multiple
concurrent `asyncio` tasks: `get_instance()`'s in-progress resolution state is
tracked per-thread and per-task, not on the injector, so two unrelated
resolutions running concurrently can't interfere with each other's circular
dependency detection or scope caching. `scopes.Singleton()` (and the exported
`scopes.SINGLETON`) additionally guards each key's *first* resolution with a
lock, so concurrent callers racing to build the same singleton get exactly one
construction, not one each.

This covers snake-guice's own bookkeeping, not the objects it builds - a
provider that does I/O or touches shared mutable state is still that
provider's own responsibility to make safe. See [Threads and
Async](concurrency.md) for how to structure a threaded or `asyncio`
application around this guarantee, and its
[Limitations](concurrency.md#limitations) section for two pre-existing edge
cases - reentrant singleton construction through a child injector, and cycles
that cross a fresh `create_child()` on every hop - that it doesn't cover.

## Why It Matters: Swapping Implementations in Tests

None of `Car`'s code mentions `SmallBlockEngine` or `BasicDashboard` - it only
depends on `IEngine` and `IDashboard`. That means a test module can bind
fakes instead, and `Car` never knows the difference:

```python
class FakeEngine(IEngine):
    def __init__(self) -> None:
        self.started = False

    def start(self) -> None:
        self.started = True


class TestModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=FakeEngine)
        binder.bind(IDashboard, to=BasicDashboard)


injector = create_injector([TestModule()])
car = injector.get_instance(Car)

assert isinstance(car.engine, FakeEngine)
car.engine.start()
assert car.engine.started
```

This is the payoff for declaring dependencies instead of constructing them:
production code wires up real implementations, tests wire up fakes, and `Car`
itself - the thing you're actually testing - doesn't change.
