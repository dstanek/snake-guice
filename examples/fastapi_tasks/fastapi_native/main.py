"""Entry point: builds the FastAPI app and its app-lifetime singletons."""

import logging

from fastapi import FastAPI

from examples.fastapi_tasks.fastapi_native.clock import SystemClock
from examples.fastapi_tasks.fastapi_native.db import Databases
from examples.fastapi_tasks.fastapi_native.listeners import MetricsCollector
from examples.fastapi_tasks.fastapi_native.routes import router
from examples.fastapi_tasks.shared.models import Base


def create_app(db_path: str) -> FastAPI:
    databases = Databases(db_path)
    Base.metadata.create_all(databases.writer_engine)

    app = FastAPI(title="Tasks API (native)")
    app.state.databases = databases
    app.state.clock = SystemClock()
    app.state.metrics = MetricsCollector()
    app.state.logger = logging.getLogger("fastapi_native.tasks")
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app("native.db"), host="127.0.0.1", port=8000)
