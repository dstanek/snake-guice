""" """

from typing import Any, Callable

from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.interfaces import Injector as InjectorI


class ParameterInterceptor:
    def __init__(self, injector: InjectorI) -> None:
        self._injector = injector

    def __call__(
        self, annotation: AnnotationLike = UNANNOTATED, **kwargs: Any
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        if len(kwargs) != 1:
            raise TypeError("ParameterInterceptor expects exactly one name=Type kwarg")
        param_name, param_type = next(iter(kwargs.items()))

        def callback(method: Callable[..., Any]) -> Callable[..., Any]:
            def _callback(*args: Any, **kwargs: Any) -> Any:
                kwargs[param_name] = self._injector.get_instance(param_type, annotation)
                return method(*args, **kwargs)

            return _callback

        return callback
