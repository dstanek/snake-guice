""" """

from typing import Any, Callable, TypeVar, cast

from snakeguice.annotation import UNANNOTATED, AnnotationLike
from snakeguice.interfaces import Injector as InjectorI

F = TypeVar("F", bound=Callable[..., Any])


class ParameterInterceptor:
    def __init__(self, injector: InjectorI) -> None:
        self._injector = injector

    def __call__(
        self, annotation: AnnotationLike = UNANNOTATED, **kwargs: Any
    ) -> Callable[[F], F]:
        if len(kwargs) != 1:
            raise TypeError("ParameterInterceptor expects exactly one name=Type kwarg")
        param_name, param_type = next(iter(kwargs.items()))

        def callback(method: F) -> F:
            def _callback(*args: Any, **kwargs: Any) -> Any:
                kwargs[param_name] = self._injector.get_instance(param_type, annotation)
                return method(*args, **kwargs)

            return cast(F, _callback)

        return callback
