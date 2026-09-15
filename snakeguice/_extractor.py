import functools
import inspect
from typing import Any, Callable, NamedTuple

from snakeguice.annotation import UNANNOTATED, AnnotationLike


class Param(NamedTuple):
    name: str
    dtype: Any
    annotation: AnnotationLike
    default: Any = inspect.Parameter.empty


# Process-wide and keyed by function identity: entries keep their function
# (and its evaluated annotations) alive until evicted.
@functools.lru_cache(maxsize=1024)
def _extract_params_cached(func: Callable[..., Any]) -> tuple[Param, ...]:
    types = inspect.get_annotations(func, eval_str=True)
    annotations = getattr(func, "__guice_annotations__", {})
    names = [name for name in types if name != "return"]
    if not names:
        return ()
    sig = inspect.signature(func)
    params = []
    for name in names:
        annotation = annotations.get(name, UNANNOTATED)
        sig_param = sig.parameters.get(name)
        default = (
            sig_param.default if sig_param is not None else inspect.Parameter.empty
        )
        params.append(Param(name, types[name], annotation, default))
    return tuple(params)


def extract_params(method: Callable[..., Any]) -> tuple[Param, ...]:
    return _extract_params_cached(getattr(method, "__func__", method))
