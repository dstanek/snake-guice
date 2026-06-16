# Examples Using snake-guice

The repository includes several runnable examples. All can be validated with:

```bash
make example-tests
```

```{toctree}
:maxdepth: 1
:caption: "Contents:"

simple_webapp
```

## Additional examples in the repository

The following examples live under `examples/` in the source tree. See
`examples/README.md` for run commands.

**`examples/cherrypy/`** — Request-scoped DI with CherryPy. Demonstrates
custom request and session scopes, module composition, and provider injection
in a small web application.

**`examples/wsgiapp/`** — A lightweight WSGI application using WebOb and
Routes, showing snake-guice without a full web framework.

**`examples/fastapi_tasks/`** — Side-by-side task-management API implemented
twice: once with native FastAPI `Depends` and once with snake-guice. See
`examples/fastapi_tasks/design.md` for an in-depth comparison of the two
approaches.

**`examples/snakeweb/`** — Minimal hello-world using the bundled
`extras/snakeweb.py` WSGI helper.
