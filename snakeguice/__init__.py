"""Main API entry point for snake-guice."""

from snakeguice.decorators import annotate, inject, provides
from snakeguice.errors import BindingError, SnakeGuiceError
from snakeguice.injector import Injector, create_injector
from snakeguice.interceptors import ParameterInterceptor

__all__ = [
    "annotate",
    "inject",
    "provides",
    "BindingError",
    "SnakeGuiceError",
    "Injector",
    "create_injector",
    "ParameterInterceptor",
]
