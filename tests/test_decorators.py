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

    assert getattr(SomeClass, "__guice_methods__") == {"go"}


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
    def setup(self) -> None:
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
