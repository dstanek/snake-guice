# What to Inject

Just because a class *can* be constructed through the injector doesn't mean it
*should* be. snake-guice (like Guice) shines for objects that need other
objects wired in; for everything else, a plain constructor call is simpler and
clearer.

## Good Candidates for Injection

A class is a good fit for `@inject`/`binder.bind(...)` when it has:

- **Dependencies of its own** - constructor parameters that are interfaces,
  not data, that the class needs in order to do its job.
- **A reason to swap implementations** - in tests you want a fake, or in
  production you might support more than one backend.
- **A reason to be a singleton** - shared state or an expensive-to-create
  resource, bound `in_scope=scopes.SINGLETON` (see
  [Scopes](userguide.md#scopes)).

```python
from snakeguice import inject
from snakeguice.interfaces import Binder


class IEngine:
    """Interface for a car engine."""


class SmallBlockEngine(IEngine):
    def __init__(self) -> None:
        self.horsepower = 350


class Car:
    @inject
    def __init__(self, engine: IEngine) -> None:
        self.engine = engine


class AutoModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IEngine, to=SmallBlockEngine)
```

`Car` depends on the *interface* `IEngine`, not on `SmallBlockEngine`
specifically. That's exactly what makes it worth injecting: a test module can
bind `IEngine` to a `FakeEngine` and `Car` never knows the difference - see
[Swapping Implementations in
Tests](userguide.md#why-it-matters-swapping-implementations-in-tests).

## Poor Candidates: Plain Data

Not every object in your application needs a binding. Values that are just
data - with no behavior, no dependencies, and nothing you'd ever fake in a
test - don't benefit from going through the injector. Build them the normal
way, with their constructor:

```python
from dataclasses import dataclass


@dataclass
class EngineSpec:
    """A plain bundle of numbers - just data, no behavior."""

    horsepower: int
    displacement_liters: float


class SmallBlockEngine(IEngine):
    def __init__(self) -> None:
        self.spec = EngineSpec(horsepower=350, displacement_liters=5.7)
```

`EngineSpec` has no dependencies to wire up and no reason to be swapped out in
tests - it's the same kind of object whether `SmallBlockEngine` creates it
directly or a test does. Binding it would only add ceremony: an interface, a
module, and a binding, all to stand in for `EngineSpec(350, 5.7)`.

## A Rule of Thumb

Dhanji R. Prasanna, one of Guice's original authors, put it this way in a post
to the google-guice Google Group:

> As a rule of thumb, Guice should generally only create:
>
> - what you want it to populate with other dependencies
> - what you want to be testable with mock substitutes
> - singletons
>
> If it doesn't come under one of these, you likely don't need to Guice it
> (example: an "Address" data model object).
