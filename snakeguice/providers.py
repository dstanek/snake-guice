"""Providers used in the binding process."""

# pylint: disable-msg=C0111
#         providers are so small that we can safely omit doc comments

from typing import Any, Type

from snakeguice.decorators import inject
from snakeguice.interfaces import Injector, Provider


def create_simple_provider(cls: Type[Any]) -> Type[Provider[Any]]:
    class DynamicSimpleProvider:
        @inject
        def __init__(self, injector: Injector) -> None:
            self._injector = injector

        def get(self) -> Any:
            return self._injector.create_object(cls)

    return DynamicSimpleProvider


def create_instance_provider(obj: Any) -> Type[Provider[Any]]:
    class DynamicInstanceProvider:
        def get(self) -> Any:
            return obj

    return DynamicInstanceProvider
