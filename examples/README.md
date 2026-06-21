# Examples

Each example lives in its own subdirectory. Use `uv run` to launch them.

## CherryPy web app (`cherrypy/`)

A request-scoped DI example using CherryPy.

```bash
uv run python -m examples.cherrypy.app
```

Requires CherryPy (`pip install cherrypy`).

## WSGI app (`wsgiapp/`)

A lightweight WSGI example using WebOb and Routes.

```bash
uv run python -m examples.wsgiapp.app
```

## FastAPI comparison (`fastapi_tasks/`)

Side-by-side FastAPI implementations — one using native FastAPI `Depends`,
the other using snake-guice — doing the same task-management API.

```bash
# snake-guice version (port 8001)
uv run python -m examples.fastapi_tasks.fastapi_snakeguice.main

# native FastAPI version (port 8000)
uv run python -m examples.fastapi_tasks.fastapi_native.main
```

See `fastapi_tasks/design.md` for a detailed write-up.

## snakeweb (`snakeweb/`)

A minimal hello-world showing `extras/snakeweb.py`.

```bash
uv run python examples/snakeweb/simple_hello_world.py
```

## Running example tests

```bash
make example-tests
```
