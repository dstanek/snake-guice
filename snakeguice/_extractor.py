import inspect
from typing import Any, Callable, Iterable, NamedTuple

from snakeguice.annotation import UNANNOTATED, AnnotationLike


class Param(NamedTuple):
    name: str
    dtype: Any
    annotation: AnnotationLike
    default: Any = inspect.Parameter.empty


def extract_params(method: Callable[..., Any]) -> Iterable[Param]:
    types = inspect.get_annotations(method, eval_str=True)
    annotations = getattr(method, "__guice_annotations__", {})
    sig = inspect.signature(method)
    for name, dtype in types.items():
        if name == "return":
            continue
        annotation = annotations.get(name, UNANNOTATED)
        sig_param = sig.parameters.get(name)
        default = (
            sig_param.default if sig_param is not None else inspect.Parameter.empty
        )
        yield Param(name, dtype, annotation, default)
