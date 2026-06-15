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

## Resolving Instances

`injector.get_instance(cls, annotation)` builds a `Key` from `cls` and
`annotation` and looks it up in the binder:

- **Bound** - if a binding exists for that key, its provider is asked for an
  instance (passed through the binding's scope - see [Scopes](#scopes)
  below).
- **Unbound** - if no binding exists, snake-guice falls back to *implicit
  construction*: it calls `create_object(cls)`, which inspects `cls.__init__`
  and injects each annotated parameter, and then `inject_members(instance)`,
  which calls every `@inject`-decorated method (other than `__init__`) the
  same way.

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

```{note}
Method injection (`inject_members`) only happens for implicit construction. If
you explicitly bind a class with `to=SomeClass`, only its `__init__` is
injected - `@inject`-decorated methods other than `__init__` won't be called
automatically. This is rarely an issue in practice: classes you want method
injection on are usually left unbound and constructed implicitly, as `Car` is
here.
```

## Modules and Binders

A **module** is anything with a `configure(binder)` method - that's the
"simple module" shown above. `snakeguice.modules.Module` is a base class that
adds two things: it tracks `self._injector`, and it gives you `install()` for
composing modules:

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
resolution of that `(interface, annotation)` key:

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

```{warning}
`scopes.SINGLETON` is a single shared object, and its cache is keyed only by
`Key` (interface + annotation) - not by injector. If *any* injector in the
process binds `IEngine` (unannotated) `in_scope=scopes.SINGLETON`, every other
injector that does the same shares that one cached instance, even if they bind
`IEngine` to a different implementation. If you need an independent cache -
for example, one per test - create your own scope with `scopes._Singleton()`
instead of using the shared `scopes.SINGLETON`, as `tests/test_singletons.py`
does.
```

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
