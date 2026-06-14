"""Listeners notified when tasks are created or completed.

Two independent concerns (audit logging, metrics) both hook into the same
lifecycle events on `Task`. `AuditModule` and `MetricsModule` each contribute
one of these to the shared `List[TaskListener]` binding via `ListBinder`.
"""

import logging

from examples.fastapi_tasks.shared.models import Task
from snakeguice import inject


class TaskListener:
    def on_created(self, task: Task) -> None:
        raise NotImplementedError

    def on_completed(self, task: Task) -> None:
        raise NotImplementedError


class MetricsCollector:
    def __init__(self) -> None:
        self.created = 0
        self.completed = 0


class AuditLogListener(TaskListener):
    @inject  # optional, but helps as "documentation"
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def on_created(self, task: Task) -> None:
        self._logger.info("task %s created: %r", task.id, task.title)

    def on_completed(self, task: Task) -> None:
        self._logger.info("task %s completed", task.id)


class MetricsListener(TaskListener):
    @inject  # optional, but helps as "documentation"
    def __init__(self, metrics: MetricsCollector) -> None:
        self._metrics = metrics

    def on_created(self, task: Task) -> None:
        self._metrics.created += 1

    def on_completed(self, task: Task) -> None:
        self._metrics.completed += 1
