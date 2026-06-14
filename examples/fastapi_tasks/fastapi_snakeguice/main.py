"""Entry point: builds the FastAPI app, the snake-guice injector, and the
per-request scope middleware."""

from fastapi import FastAPI, Request, Response
from sqlalchemy import create_engine
from starlette.middleware.base import RequestResponseEndpoint

from examples.fastapi_tasks.fastapi_snakeguice.modules import AppModule
from examples.fastapi_tasks.fastapi_snakeguice.routes import router
from examples.fastapi_tasks.fastapi_snakeguice.scopes import (
    close_request_sessions,
    reset_request_scope,
)
from examples.fastapi_tasks.shared.models import Base
from snakeguice import create_injector


def create_app(db_path: str) -> FastAPI:
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()

    app = FastAPI(title="Tasks API (snake-guice)")
    app.state.injector = create_injector([AppModule(db_path)])

    @app.middleware("http")
    async def request_scope_middleware(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        cache = reset_request_scope()
        try:
            return await call_next(request)
        finally:
            close_request_sessions(cache)

    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(create_app("snakeguice.db"), host="127.0.0.1", port=8001)
