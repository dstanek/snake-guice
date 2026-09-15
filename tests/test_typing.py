"""Type-level tests for `Binder.bind()`'s overloads on abstract interfaces.

`make lint` runs `mypy --strict` over `tests/`, so this module doubles as a
type check: binding a `Protocol` or an ABC interface `to=`, `to_instance=`,
or `to_provider=` must type-check with zero `# type: ignore`s.
"""

from abc import ABC, abstractmethod
from typing import Protocol

from snakeguice import create_injector
from snakeguice.interfaces import Binder

# NOTE: there is no test here pinning a concrete-interface `to_instance=`
# mismatch with `# type: ignore[call-overload]`. There was never a nominal
# check to lose: `to_instance=`'s unconstrained `_T` gets inferred as the
# join of the `_class`/`to_instance` argument types, so mypy already accepts
# any value for any class (see tests/test_binder.py's
# test_to_instance_accepts_a_duck_typed_stand_in, which documents the same
# thing at runtime).


class GreeterP(Protocol):
    """A `Protocol` interface: bindable `to=`, `to_instance=`, and
    `to_provider=` with no ignores."""

    def greet(self) -> str: ...


class FriendlyGreeter:
    def greet(self) -> str:
        return "hi"


class GreeterProvider:
    def get(self) -> GreeterP:
        return FriendlyGreeter()


class Farewell(ABC):
    """An abstract base class interface, same three targets as `GreeterP`."""

    @abstractmethod
    def say(self) -> str: ...


class ConcreteFarewell(Farewell):
    def say(self) -> str:
        return "bye"


class FarewellProvider:
    def get(self) -> Farewell:
        return ConcreteFarewell()


class TypingModule:
    def configure(self, binder: Binder) -> None:
        # Protocol interface, all three binding targets.
        binder.bind(GreeterP, to=FriendlyGreeter)
        binder.bind(GreeterP, to_instance=FriendlyGreeter(), annotated_with="instance")
        binder.bind(
            GreeterP,
            to_provider=GreeterProvider(),
            annotated_with="provider-instance",
        )
        binder.bind(
            GreeterP, to_provider=GreeterProvider, annotated_with="provider-class"
        )

        # ABC interface, all three binding targets.
        binder.bind(Farewell, to=ConcreteFarewell, annotated_with="to")
        binder.bind(Farewell, to_instance=ConcreteFarewell(), annotated_with="instance")
        binder.bind(
            Farewell,
            to_provider=FarewellProvider(),
            annotated_with="provider-instance",
        )
        binder.bind(
            Farewell, to_provider=FarewellProvider, annotated_with="provider-class"
        )


def test_typing_module_resolves_every_binding() -> None:
    injector = create_injector([TypingModule()])

    assert injector.get_instance(GreeterP).greet() == "hi"
    assert injector.get_instance(GreeterP, "instance").greet() == "hi"
    assert injector.get_instance(GreeterP, "provider-instance").greet() == "hi"
    assert injector.get_instance(GreeterP, "provider-class").greet() == "hi"

    assert injector.get_instance(Farewell, "to").say() == "bye"
    assert injector.get_instance(Farewell, "instance").say() == "bye"
    assert injector.get_instance(Farewell, "provider-instance").say() == "bye"
    assert injector.get_instance(Farewell, "provider-class").say() == "bye"
