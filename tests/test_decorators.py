"""Behavioral tests for the snake-guice decorators."""

import pytest

from snakeguice.decorators import annotate, inject


def test_inject_init():
    """Using the inject decorator on a constructor."""

    class SomeClass:
        @inject(x=int)
        def __init__(self, x):
            pass

    assert SomeClass.__init__.__guice_types__ == {"x": int}


def test_inject_methods():
    """Using the inject decorator on a method."""

    class SomeClass:
        @inject(y=float)
        def go(self, y):
            pass

    assert SomeClass.go.__guice_types__ == {"y": float}


def test_inject_all():
    """Using combinations of inject including annotations."""
    # TODO: add annotation stuff again

    class SomeClass:
        @inject(a=bool, b=int, c=float)
        @annotate(a="free", b="paid")
        def __init__(self, a, b, c):
            pass

        @inject(y=float)
        def go(self, y):
            pass

        @inject(x=int, y=int, z=object)
        @annotate(y="old", z="new")
        def stop(self, x, y, z):
            pass

    assert SomeClass.__init__.__guice_types__ == {
        "a": bool,
        "b": int,
        "c": float,
    }
    assert SomeClass.__init__.__guice_annotations__ == {
        "a": "free",
        "b": "paid",
    }
    assert SomeClass.go.__guice_types__ == {"y": float}
    assert SomeClass.stop.__guice_types__ == {
        "x": int,
        "y": int,
        "z": object,
    }
    assert SomeClass.stop.__guice_annotations__ == {
        "y": "old",
        "z": "new",
    }


def test_incorrect_methods0():
    """Ensure inject is validating method calls."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject(int, y=int)
            def f(self, x, y):
                pass


def test_incorrect_methods1():
    """Ensure inject is validating method calls."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject(z=int, y=int)
            def f(self, x, y):
                pass


def test_incorrect_methods2():
    """Ensure inject is validating method calls."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject(y=int)
            def f(self, x, y):
                pass


def test_incorrect_methods3():
    """Ensure inject is validating method calls."""

    with pytest.raises(TypeError):

        class SomeClass:
            @inject
            def f(self, x, y):
                pass
