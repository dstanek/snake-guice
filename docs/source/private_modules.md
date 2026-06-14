# Private Modules

Every `binder.bind()` call in a normal module adds to one shared binder. That's
fine until two modules each need their *own* binding for the same interface -
each binder only allows one binding per `(interface, annotation)` key, so the
second call raises `BindingError`.

This is the classic "robot legs" problem: a left and a right leg both need a
foot, but they need *different* feet. `PrivateModule` solves it by giving each
module its own isolated binder, and a way to publish just the bindings it
wants the rest of the application to see.

## The Problem

Imagine two car doors, each with its own lock mechanism. Both need an `ILock`,
but the left door needs a `LeftLock` and the right door needs a `RightLock`.
Binding `ILock` directly in two modules doesn't work:

```python
from snakeguice import create_injector
from snakeguice.errors import BindingError
from snakeguice.interfaces import Binder


class ILock:
    """Interface for a door lock mechanism."""


class LeftLock(ILock):
    pass


class RightLock(ILock):
    pass


class LeftDoorModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(ILock, to=LeftLock)


class RightDoorModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(ILock, to=RightLock)


try:
    create_injector([LeftDoorModule(), RightDoorModule()])
except BindingError as e:
    print(e)  # baseclass <class 'ILock'> already bound
```

## Isolating Bindings with `PrivateModule`

`snakeguice.modules.PrivateModule` is a `Module` whose `configure(binder)`
receives a *private* binder, backed by its own child injector. Bindings made
there - like `ILock` - aren't visible to the parent binder or to other
modules, so two `PrivateModule`s can each bind `ILock` to a different
implementation without colliding.

To make a binding visible outside the private module, call
`self.expose(binder, interface, annotation)`. This adds a binding to the
*parent* binder that, when resolved, delegates to the private injector:

```python
from snakeguice import annotate, inject
from snakeguice.modules import Module, PrivateModule


class IDoor:
    """Interface for a car door."""


class Door(IDoor):
    @inject
    def __init__(self, lock: ILock) -> None:
        self.lock = lock


class LeftDoorModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(ILock, to=LeftLock)
        binder.bind(IDoor, annotated_with="left", to=Door)
        self.expose(binder, IDoor, "left")


class RightDoorModule(PrivateModule):
    def configure(self, binder: Binder) -> None:
        binder.bind(ILock, to=RightLock)
        binder.bind(IDoor, annotated_with="right", to=Door)
        self.expose(binder, IDoor, "right")


class Car:
    @inject
    @annotate(left_door="left", right_door="right")
    def __init__(self, left_door: IDoor, right_door: IDoor) -> None:
        self.left_door = left_door
        self.right_door = right_door


class CarModule(Module):
    def configure(self, binder: Binder) -> None:
        self.install(binder, LeftDoorModule())
        self.install(binder, RightDoorModule())


injector = create_injector([CarModule()])
car = injector.get_instance(Car)

assert isinstance(car.left_door.lock, LeftLock)
assert isinstance(car.right_door.lock, RightLock)
```

`ILock` is bound twice - once per private module - with no conflict, because
each `PrivateModule` has its own binder. Only `IDoor` (annotated `"left"` and
`"right"`) is exposed to `CarModule`'s binder, which is where `Car` resolves
it.

```{warning}
The binding passed to `expose(binder, interface, annotation)` must also exist
in the private module *under that same `(interface, annotation)` key* - here,
`binder.bind(IDoor, annotated_with="left", to=Door)` inside `LeftDoorModule`.

`expose()` adds a provider to the *parent* binder that calls
`private_injector.get_instance(interface, annotation)`. If the private binder
doesn't have its own binding for that exact key, the lookup falls through to
the parent binder - where it finds the very provider `expose()` just added,
and calls it again, infinitely. Binding the same `(interface, annotation)` key
inside the private module (as `LeftDoorModule` does for `(IDoor, "left")`)
ensures the lookup is satisfied locally.
```
