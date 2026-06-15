"""A single Depends() seam: from_injector(cls) resolves cls through the
request's snake-guice Injector, regardless of how deep its dependency graph
is."""

from typing import Type, TypeVar

from fastapi import Depends, Request

T = TypeVar("T")


def from_injector(cls: Type[T]) -> T:
    def resolve(request: Request) -> T:
        return request.app.state.injector.get_instance(cls)

    return Depends(resolve)
