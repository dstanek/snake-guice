"""Task use cases: validation, 404s, and listener notification."""

from typing import List

from fastapi import HTTPException

from examples.fastapi_tasks.fastapi_snakeguice.listeners import TaskListener
from examples.fastapi_tasks.fastapi_snakeguice.repository import TaskRepository
from examples.fastapi_tasks.shared.schemas import TaskCreate, TaskRead, TaskUpdate
from snakeguice import inject


class TaskService:
    @inject
    def __init__(
        self, repository: TaskRepository, listeners: List[TaskListener]
    ) -> None:
        self._repository = repository
        self._listeners = listeners

    def list_tasks(self) -> list[TaskRead]:
        return [TaskRead.model_validate(task) for task in self._repository.list()]

    def get_task(self, task_id: int) -> TaskRead:
        task = self._repository.get(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        return TaskRead.model_validate(task)

    def create_task(self, data: TaskCreate) -> TaskRead:
        task = self._repository.create(data)
        for listener in self._listeners:
            listener.on_created(task)
        return TaskRead.model_validate(task)

    def update_task(self, task_id: int, data: TaskUpdate) -> TaskRead:
        task = self._repository.get_for_write(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        was_done = task.done
        task = self._repository.update(task, data)
        if task.done and not was_done:
            for listener in self._listeners:
                listener.on_completed(task)
        return TaskRead.model_validate(task)

    def delete_task(self, task_id: int) -> None:
        task = self._repository.get_for_write(task_id)
        if task is None:
            raise HTTPException(404, "task not found")
        self._repository.delete(task)
