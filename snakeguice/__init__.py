"""Main API entry point for snake-guice."""

from snakeguice.decorators import annotate, inject, provides
from snakeguice.errors import BindingError, CreationError, SnakeGuiceError
from snakeguice.injector import Injector, create_injector
from snakeguice.interceptors import ParameterInterceptor
from snakeguice.private_module import PrivateModule

__all__ = [
    "annotate",
    "inject",
    "provides",
    "BindingError",
    "CreationError",
    "SnakeGuiceError",
    "Injector",
    "create_injector",
    "ParameterInterceptor",
    "PrivateModule",
]
