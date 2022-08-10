from collections import namedtuple
from typing import Any, Callable, Iterable

from snakeguice.annotation import UNANNOTATED

Param = namedtuple("Param", ["name", "dtype", "annotation"])  # TODO: type me


def extract_params(method: Callable[..., Any]) -> Iterable[Param]:
    types = getattr(method, "__annotations__", {})
    annotations = getattr(method, "__guice_annotations__", {})
    for name, dtype in types.items():
        if name == "return":
            continue
        annotation = annotations.get(name, UNANNOTATED)
        yield Param(name, dtype, annotation)
