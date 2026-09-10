"""Wires the task API's dependency graph.

`ReaderDatabaseModule`/`WriterDatabaseModule` are `PrivateModule`s that each
own a `Database` and expose an annotated `Session` (the "robot legs" pattern
from `docs/source/private_modules.md`). `ClockModule` binds a stateless
`SINGLETON` `Clock`. `AuditModule`/`MetricsModule` each contribute a
`TaskListener` to the shared `list[TaskListener]` binding via `ListBinder`,
and `MetricsModule` gives `MetricsCollector` a custom-scope cache
(`PerAppSingleton`, see `scopes.py`) as a worked example of the `Scope`
protocol.
"""

import logging

from sqlalchemy.orm import Session

from examples.fastapi_tasks.fastapi_snakeguice.clock import Clock, SystemClock
from examples.fastapi_tasks.fastapi_snakeguice.db import Database, IDatabase
from examples.fastapi_tasks.fastapi_snakeguice.listeners import (
    AuditLogListener,
    MetricsCollector,
    MetricsListener,
    TaskListener,
)
from examples.fastapi_tasks.fastapi_snakeguice.scopes import (
    FASTAPI_REQUEST_SCOPE,
    PerAppSingleton,
)
from snakeguice import PrivateModule, inject, scopes
from snakeguice.interfaces import Binder
from snakeguice.modules import Module
from snakeguice.multibinder import ListBinder


class _SessionProvider:
    @inject
    def __init__(self, database: IDatabase) -> None:
        self._database = database

    def get(self) -> Session:
        return self._database.get_session()


class ReaderDatabaseModule(PrivateModule):
    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._database = Database(db_path)

    def configure(self, binder: Binder) -> None:
        binder.bind(IDatabase, to_instance=self._database)
        binder.bind(
            Session,
            annotated_with="reader",
            to_provider=_SessionProvider,
            in_scope=FASTAPI_REQUEST_SCOPE,
        )
        self.expose(binder, Session, "reader")


class WriterDatabaseModule(PrivateModule):
    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._database = Database(db_path)

    def configure(self, binder: Binder) -> None:
        binder.bind(IDatabase, to_instance=self._database)
        binder.bind(
            Session,
            annotated_with="writer",
            to_provider=_SessionProvider,
            in_scope=FASTAPI_REQUEST_SCOPE,
        )
        self.expose(binder, Session, "writer")


class ClockModule(Module):
    def configure(self, binder: Binder) -> None:
        # Each create_app() gets its own injector, so its own SINGLETON
        # cache for Clock - SystemClock being stateless means it wouldn't
        # matter even if that weren't true.
        binder.bind(Clock, to=SystemClock, in_scope=scopes.SINGLETON)


class AuditModule(Module):
    def configure(self, binder: Binder) -> None:
        binder.bind(
            logging.Logger,
            to_instance=logging.getLogger("fastapi_snakeguice.tasks"),
        )
        ListBinder(binder, list[TaskListener]).add_binding(to=AuditLogListener)


class MetricsModule(Module):
    def __init__(self) -> None:
        super().__init__()
        self._scope = PerAppSingleton()

    def configure(self, binder: Binder) -> None:
        # self._scope is a worked example of a custom Scope (see scopes.py);
        # scopes.SINGLETON would behave identically here, since each
        # MetricsModule already gets its own injector's cache.
        binder.bind(MetricsCollector, to=MetricsCollector, in_scope=self._scope)
        ListBinder(binder, list[TaskListener]).add_binding(to=MetricsListener)


class AppModule(Module):
    def __init__(self, db_path: str) -> None:
        super().__init__()
        self._db_path = db_path

    def configure(self, binder: Binder) -> None:
        self.install(binder, ReaderDatabaseModule(self._db_path))
        self.install(binder, WriterDatabaseModule(self._db_path))
        self.install(binder, ClockModule())
        self.install(binder, AuditModule())
        self.install(binder, MetricsModule())
