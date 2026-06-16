"""Behavioral tests for the snake-guice decorators."""

import pytest

from snakeguice.decorators import annotate, inject


def test_inject_init_with_invalid_type_annotations_fails() -> None:
    """Using the inject decorator on the initializer."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def __init__(self, a) -> None:  # type: ignore
                pass


def test_inject_methods() -> None:
    """Using the inject decorator on a method."""

    class SomeClass:
        @inject
        def go(self, y: float) -> None:
            pass

    assert getattr(SomeClass, "__guice_methods__") == ["go"]


def test_inject_methods_preserve_declaration_order() -> None:
    """@inject on multiple methods must record them in declaration order."""

    class Ordered:
        @inject
        def step_one(self, x: int) -> None:
            pass

        @inject
        def step_two(self, x: int) -> None:
            pass

        @inject
        def step_three(self, x: int) -> None:
            pass

    methods = getattr(Ordered, "__guice_methods__")
    assert not isinstance(methods, set), "__guice_methods__ must not be a set"
    assert list(methods) == ["step_one", "step_two", "step_three"]


def test_inject_methods_with_invalid_type_annotations_fails0() -> None:
    """Using the inject decorator on a method."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def go(self, y):  # type: ignore
                pass


def test_inject_methods_with_invalid_type_annotations_fails1() -> None:
    """Using the inject decorator on a method."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def go(self, x: int, y):  # type: ignore
                pass


class Test_annotate_stores_annotations_on_methods:
    def setup_method(self) -> None:
        class Object:
            @annotate(a="_a_")
            def __init__(self, a: object, b: object) -> None:
                pass

            @annotate(x="_x_", y="_y_")
            def method(self, x: object, y: object) -> None:
                pass

        self.Object = Object

    def test_init(self) -> None:
        assert getattr(self.Object.__init__, "__guice_annotations__") == {"a": "_a_"}

    def test_method(self) -> None:
        assert getattr(self.Object.method, "__guice_annotations__") == {
            "x": "_x_",
            "y": "_y_",
        }


# Bug: the docs claimed @annotate must be listed *below* @inject, but the guard
# that was supposed to enforce this never fired (it checked "__guice__" in class
# locals; @inject sets "__guice_methods__", never "__guice__").  Both orderings
# have always worked.  The tests below document that both are valid.


def test_annotate_below_inject_works() -> None:
    """Conventional order: @inject above @annotate in source."""

    class Widget:
        @inject
        @annotate(x="_x_")
        def __init__(self, x: object) -> None:
            self.x = x

    assert getattr(Widget.__init__, "__guice_annotations__") == {"x": "_x_"}


def test_annotate_above_inject_works() -> None:
    """Reversed order: @annotate above @inject in source (inject applied first).
    The docs incorrectly said this order was forbidden; it works identically."""

    class Widget:
        @annotate(x="_x_")
        @inject
        def __init__(self, x: object) -> None:
            self.x = x

    assert getattr(Widget.__init__, "__guice_annotations__") == {"x": "_x_"}
