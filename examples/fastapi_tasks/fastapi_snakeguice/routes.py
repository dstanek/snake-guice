"""HTTP routes for the Tasks API."""

from fastapi import APIRouter, status

from examples.fastapi_tasks.fastapi_snakeguice.deps import from_injector
from examples.fastapi_tasks.fastapi_snakeguice.listeners import MetricsCollector
from examples.fastapi_tasks.fastapi_snakeguice.service import TaskService
from examples.fastapi_tasks.shared.schemas import (
    StatsRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
)

router = APIRouter()


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate, service: TaskService = from_injector(TaskService)
) -> TaskRead:
    return service.create_task(data)


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(service: TaskService = from_injector(TaskService)) -> list[TaskRead]:
    return service.list_tasks()


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(
    task_id: int, service: TaskService = from_injector(TaskService)
) -> TaskRead:
    return service.get_task(task_id)


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(
    task_id: int, data: TaskUpdate, service: TaskService = from_injector(TaskService)
) -> TaskRead:
    return service.update_task(task_id, data)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int, service: TaskService = from_injector(TaskService)
) -> None:
    service.delete_task(task_id)


@router.get("/stats", response_model=StatsRead)
def get_stats(metrics: MetricsCollector = from_injector(MetricsCollector)) -> StatsRead:
    return StatsRead(created=metrics.created, completed=metrics.completed)
