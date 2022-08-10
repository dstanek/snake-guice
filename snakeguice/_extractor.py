from collections import namedtuple
from typing import Any, Callable, Iterable

Param = namedtuple("Param", ["name", "dtype", "annotation"])  # TODO: type me


def extract_params(method: Callable[..., Any]) -> Iterable[Param]:
    types = getattr(method, "__annotations__", {})
    annotations = getattr(method, "__guice_annotations__", {})
    for name, dtype in types.items():
        if name == "return":
            continue
        annotation = annotations.get(name)
        yield Param(name, dtype, annotation)
