import inspect
import sys


def _validate_method_args(method):
    """Validate decorator args when used to decorate a method."""
    sig = inspect.signature(method)
    for param in sig.parameters.values():
        if param.name != "self" and param.annotation is inspect.Parameter.empty:
            raise TypeError(
                f"param '{param.name}' is missing a type annotation "
                "and cannot be injected"
            )


def enclosing_frame(frame=None, level=2):
    """Get an enclosing frame that skips decorator code"""
    frame = frame or sys._getframe(level)
    while frame.f_globals.get("__name__") == __name__:
        frame = frame.f_back
    return frame


def inject(method):
    _validate_method_args(method)
    if method.__name__ != "__init__":
        class_locals = enclosing_frame().f_locals
        class_locals.setdefault("__guice_methods__", set()).add(method.__name__)
    return method


class annotate:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __call__(self, method):
        class_locals = enclosing_frame().f_locals
        if "__guice__" in class_locals:
            if method.__name__ in class_locals["__guice__"].methods:
                raise Exception("annotate must be applied before inject")
        method.__guice_annotations__ = self.kwargs
        return method


class provides:
    def __init__(self, type):
        self._type = type

    def __call__(self, method):
        method.__guice_provides__ = self._type
        return method
