"""Task persistence, split across a reader and a writer session."""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from examples.fastapi_tasks.fastapi_native.clock import Clock
from examples.fastapi_tasks.shared.models import Task
from examples.fastapi_tasks.shared.schemas import TaskCreate, TaskUpdate


class TaskRepository:
    def __init__(self, reader: Session, writer: Session, clock: Clock) -> None:
        self._reader = reader
        self._writer = writer
        self._clock = clock

    def list(self) -> Sequence[Task]:
        return self._reader.scalars(select(Task).order_by(Task.id)).all()

    def get(self, task_id: int) -> Task | None:
        return self._reader.get(Task, task_id)

    def get_for_write(self, task_id: int) -> Task | None:
        return self._writer.get(Task, task_id)

    def create(self, data: TaskCreate) -> Task:
        task = Task(title=data.title, done=False, created_at=self._clock.now())
        self._writer.add(task)
        self._writer.flush()
        self._writer.refresh(task)
        return task

    def update(self, task: Task, data: TaskUpdate) -> Task:
        if data.title is not None:
            task.title = data.title
        if data.done is not None:
            task.done = data.done
        self._writer.flush()
        self._writer.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self._writer.delete(task)
        self._writer.flush()
