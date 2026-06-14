"""Dependency providers — the snake-guice way: a thin Depends() seam that
hands off to the injector, regardless of how deep the service/repository/
listener graph is."""

from fastapi import Depends, Request

from examples.fastapi_tasks.fastapi_snakeguice.listeners import MetricsCollector
from examples.fastapi_tasks.fastapi_snakeguice.service import TaskService
from snakeguice import Injector


def get_injector(request: Request) -> Injector:
    return request.app.state.injector


def get_task_service(injector: Injector = Depends(get_injector)) -> TaskService:
    return injector.get_instance(TaskService)


def get_metrics(injector: Injector = Depends(get_injector)) -> MetricsCollector:
    return injector.get_instance(MetricsCollector)
