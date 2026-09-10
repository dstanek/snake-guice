`snake-guice` is a simple, lightweight Python dependency injection framework
based on `google-guice`. The Guice way of doing things is quite a bit different
than the current breed of XML IoC containers.

- **Repository**: https://github.com/dstanek/snake-guice
- **Documentation**: https://snake-guice.readthedocs.io/

## Installation

```bash
pip install snake-guice
```

## Quick Start

Declare dependencies with `@inject` and type annotations, wire them up in a
module, then let the injector build your object graph:

```python
from snakeguice import create_injector, inject
from snakeguice.interfaces import Binder


class IEngine:
    """Interface for an engine."""


class SmallBlockEngine(IEngine):
    pass


class Car:
    @inject
    def __init__(self, engine: IEngine) -> None:
        self.engine = engine


class AutoModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)


injector = create_injector([AutoModule()])
car = injector.get_instance(Car)

assert isinstance(car.engine, SmallBlockEngine)
```

## Going Further

- [User Guide](https://snake-guice.readthedocs.io/en/latest/userguide.html) — bindings, scopes, child injectors
- [Using Providers](https://snake-guice.readthedocs.io/en/latest/using_providers.html) — per-call construction and lazy resolution
- [Multibinding](https://snake-guice.readthedocs.io/en/latest/multibinder.html) — collecting multiple implementations of one interface
- [Private Modules](https://snake-guice.readthedocs.io/en/latest/private_modules.html) — scoping bindings to a subsystem

## Sharp Edges

- `scopes.SINGLETON` is per-injector: two `create_injector()` calls each get
  their own cached instance. A `create_child()` injector still shares a
  parent-defined singleton with its parent (that's deliberate, matching
  Guice). For an instance shared across independent injectors, construct it
  yourself and bind it with `to_instance=`, which bypasses scoping. For
  per-thread instances, use `scopes.THREAD_LOCAL`.
- `Injector` is safe to share between threads (and asyncio tasks): resolution
  state is per-thread/per-task, not shared. Objects it constructs are still
  your responsibility to make thread-safe.
- Method injection (`@inject` on methods other than `__init__`) runs for any
  class snake-guice constructs, whether that's implicit construction or an
  explicit `to=` binding.
- `annotated_with="left"` and `annotated_with=Annotation("left")` are
  different keys, not two spellings of the same one - see [Guice
  Basics](https://snake-guice.readthedocs.io/en/latest/guicebasics.html#multiple-bindings-using-annotations).
  An annotated lookup with no matching binding raises `MissingBindingError`
  rather than implicitly constructing something unbound.
