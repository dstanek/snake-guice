"""Providers used in the binding process."""

# pylint: disable-msg=C0111
#         providers are so small that we can safely omit doc comments

from typing import Any, ClassVar

from snakeguice.decorators import inject
from snakeguice.interfaces import Injector, Provider


class _SimpleProvider:
    _cls: ClassVar[type[Any]]

    @inject
    def __init__(self, injector: Injector) -> None:
        self._injector = injector

    def get(self) -> Any:
        return self._injector.inject_members(self._injector.create_object(self._cls))


def create_simple_provider(cls: type[Any]) -> type[Provider[Any]]:
    # `@inject`'s signature validation already ran once on `_SimpleProvider`;
    # a plain subclass carrying `cls` as a class attribute is cheap to build
    # per bind() call and needs no re-validation.
    return type("DynamicSimpleProvider", (_SimpleProvider,), {"_cls": cls})


class _InstanceProvider:
    _obj: ClassVar[Any]

    def get(self) -> Any:
        return self._obj


def create_instance_provider(obj: Any) -> type[Provider[Any]]:
    return type("DynamicInstanceProvider", (_InstanceProvider,), {"_obj": obj})
