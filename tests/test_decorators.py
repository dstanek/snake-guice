"""Behavioral tests for the snake-guice decorators."""

import pytest

from snakeguice.decorators import annotate, inject


def test_inject_init_with_invalid_type_annotations_fails():
    """Using the inject decorator on the initializer."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def __init__(self, a):
                pass


def test_inject_methods():
    """Using the inject decorator on a method."""

    class SomeClass:
        @inject
        def go(self, y: float):
            pass

    assert SomeClass.__guice_methods__ == {"go"}


def test_inject_methods_with_invalid_type_annotations_fails0():
    """Using the inject decorator on a method."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def go(self, y):
                pass


def test_inject_methods_with_invalid_type_annotations_fails1():
    """Using the inject decorator on a method."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def go(self, x: int, y):
                pass


class Test_annotate_stores_annotations_on_methods:
    def setup(self):
        class Object:
            @annotate(a="_a_")
            def __init__(self, a, b):
                pass

            @annotate(x="_x_", y="_y_")
            def method(self, x, y):
                pass

        self.Object = Object

    def test_init(self):
        assert self.Object.__init__.__guice_annotations__ == {"a": "_a_"}

    def test_method(self):
        assert self.Object.method.__guice_annotations__ == {"x": "_x_", "y": "_y_"}
