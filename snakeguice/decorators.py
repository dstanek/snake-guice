import inspect
import sys
from types import FrameType
from typing import Any, Callable, TypeVar, overload

F = TypeVar("F", bound=Callable[..., Any])
T = TypeVar("T")


def _validate_method_args(method: Callable[..., Any]) -> None:
    """Validate decorator args when used to decorate a method."""
    sig = inspect.signature(method)
    for param in sig.parameters.values():
        if param.name != "self" and param.annotation is inspect.Parameter.empty:
            raise TypeError(
                f"param '{param.name}' is missing a type annotation "
                "and cannot be injected"
            )


def enclosing_frame(frame: FrameType | None = None, level: int = 2) -> FrameType:
    """Get an enclosing frame that skips decorator code"""
    frame = frame or sys._getframe(level)
    while frame.f_globals.get("__name__") == __name__:
        assert frame.f_back is not None
        frame = frame.f_back
    return frame


@overload
def inject(target: type[T]) -> type[T]: ...


@overload
def inject(target: F) -> F: ...


def inject(target: Any) -> Any:
    if isinstance(target, type):
        if "__init__" in target.__dict__:
            _validate_method_args(target.__dict__["__init__"])
        else:
            for base in target.__mro__[1:]:
                if base is object:
                    break
                if "__init__" in base.__dict__:
                    _validate_method_args(base.__dict__["__init__"])
                    break
        return target
    _validate_method_args(target)
    if target.__name__ != "__init__":
        class_locals = enclosing_frame().f_locals
        methods = class_locals.setdefault("__guice_methods__", [])
        if target.__name__ not in methods:
            methods.append(target.__name__)
    return target


class annotate:
    def __init__(self, **kwargs: str) -> None:
        self.kwargs = kwargs

    def __call__(self, method: F) -> F:
        setattr(method, "__guice_annotations__", self.kwargs)
        return method


class provides:
    def __init__(self, type: type[Any]) -> None:
        self._type = type

    def __call__(self, method: F) -> F:
        setattr(method, "__guice_provides__", self._type)
        return method
