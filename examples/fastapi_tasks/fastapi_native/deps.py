"""Dependency providers — the native FastAPI way: one small function per
cross-cutting concern, wired together through Depends()."""

import logging
from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from examples.fastapi_tasks.fastapi_native.clock import Clock
from examples.fastapi_tasks.fastapi_native.db import Databases
from examples.fastapi_tasks.fastapi_native.listeners import (
    AuditLogListener,
    MetricsCollector,
    MetricsListener,
    TaskListener,
)
from examples.fastapi_tasks.fastapi_native.repository import TaskRepository
from examples.fastapi_tasks.fastapi_native.service import TaskService


def get_databases(request: Request) -> Databases:
    return request.app.state.databases


def get_reader_session(
    databases: Databases = Depends(get_databases),
) -> Iterator[Session]:
    session = databases.ReaderSession()
    try:
        yield session
    finally:
        session.close()


def get_writer_session(
    databases: Databases = Depends(get_databases),
) -> Iterator[Session]:
    session = databases.WriterSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_clock(request: Request) -> Clock:
    return request.app.state.clock


def get_logger(request: Request) -> logging.Logger:
    return request.app.state.logger


def get_metrics(request: Request) -> MetricsCollector:
    return request.app.state.metrics


def get_task_listeners(
    logger: logging.Logger = Depends(get_logger),
    metrics: MetricsCollector = Depends(get_metrics),
) -> list[TaskListener]:
    return [AuditLogListener(logger), MetricsListener(metrics)]


def get_task_repository(
    reader: Session = Depends(get_reader_session),
    writer: Session = Depends(get_writer_session),
    clock: Clock = Depends(get_clock),
) -> TaskRepository:
    return TaskRepository(reader, writer, clock)


def get_task_service(
    repository: TaskRepository = Depends(get_task_repository),
    listeners: list[TaskListener] = Depends(get_task_listeners),
) -> TaskService:
    return TaskService(repository, listeners)
