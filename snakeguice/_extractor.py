import inspect
from typing import Any, Callable, Iterable, NamedTuple

from snakeguice.annotation import UNANNOTATED, AnnotationLike


class Param(NamedTuple):
    name: str
    dtype: Any
    annotation: AnnotationLike


def extract_params(method: Callable[..., Any]) -> Iterable[Param]:
    types = inspect.get_annotations(method)
    annotations = getattr(method, "__guice_annotations__", {})
    for name, dtype in types.items():
        if name == "return":
            continue
        annotation = annotations.get(name, UNANNOTATED)
        yield Param(name, dtype, annotation)
