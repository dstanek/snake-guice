# FastAPI Tasks: native `Depends()` vs. snake-guice

Two small "task management" REST APIs — same domain, same endpoints, same
SQLite-backed reader/writer split, same audit-log + metrics behavior — built
twice:

- `fastapi_native/` — idiomatic FastAPI: `Depends()` provider functions and
  `app.state` for everything.
- `fastapi_snakeguice/` — the same app, with cross-cutting concerns expressed
  as snake-guice `Module`s and resolved through an `Injector`.

`shared/` holds only the parts that aren't about dependency injection: the
SQLAlchemy `Task` model (`shared/models.py`) and the Pydantic request/response
schemas (`shared/schemas.py`). Everything else — DB wiring, clock, listeners,
repository, service, routes, app factory — is duplicated per app on purpose,
so each directory reads top-to-bottom as a complete, self-contained example.
The two directories mirror each other file-for-file (`db.py`, `clock.py`,
`listeners.py`, `repository.py`, `service.py`, `deps.py`, `routes.py`,
`main.py`), so diffing a file against its counterpart shows exactly what
changes when snake-guice is introduced.

## Running it

```sh
# native app, port 8000
uv run python -m examples.fastapi_tasks.fastapi_native.main

# snake-guice app, port 8001
uv run python -m examples.fastapi_tasks.fastapi_snakeguice.main

# shared test suite (22 tests: 11 cases x 2 apps)
make example-tests
```

Both apps create their SQLite file on first run and expose the same six
endpoints: `POST /tasks`, `GET /tasks`, `GET /tasks/{id}`, `PATCH
/tasks/{id}`, `DELETE /tasks/{id}`, `GET /stats`.

## Feature-by-feature

| Feature | Where (snake-guice) | Why it fit | Native equivalent |
| --- | --- | --- | --- |
| `PrivateModule` + `expose()` ("robot legs") | `fastapi_snakeguice/modules.py`: `ReaderDatabaseModule`/`WriterDatabaseModule` (lines 45-74) | Reader and writer each need their own `IDatabase`/`Session` binding. Without `PrivateModule`, the second `binder.bind(IDatabase, ...)` would raise `BindingError` for colliding on the same `(interface, annotation)` key. Each module gets a private child injector and exposes only its annotated `Session` to the parent. | `fastapi_native/db.py`'s `Databases` holds two engines/sessionmakers by hand; `fastapi_native/deps.py`'s `get_reader_session`/`get_writer_session` pick the right one. |
| Custom `Scope` (`FastAPIRequestScope`) | `fastapi_snakeguice/scopes.py` (lines 44-68), applied via `in_scope=FASTAPI_REQUEST_SCOPE` at `modules.py:56` and `:72` | snake-guice ships `NO_SCOPE`/`SINGLETON` but nothing per-request. A `ContextVar`-backed cache keyed by snake-guice `Key` lets `Session` be declared "one per request" right on the binding, with cleanup driven by `main.py`'s middleware. | `fastapi_native/deps.py`'s `get_reader_session`/`get_writer_session` are `Depends()` generators: FastAPI itself provides the per-request lifecycle via `yield`/`finally`. |
| `ListBinder` (multibinder) | `fastapi_snakeguice/modules.py`: `AuditModule` (line 90) and `MetricsModule` (line 103) each call `ListBinder(binder, List[TaskListener]).add_binding(to=...)` | Audit logging and metrics are independent concerns that both want to hear about task lifecycle events. `ListBinder` lets each module register its listener without either knowing about the other, accumulating into one `List[TaskListener]` binding that `TaskService` depends on. | `fastapi_native/deps.py`'s `get_task_listeners` hand-assembles `[AuditLogListener(logger), MetricsListener(metrics)]` — one function that has to know about every listener. |
| `scopes.SINGLETON` vs. `PerAppSingleton` | `Clock` via `scopes.SINGLETON` (`modules.py:81`); `MetricsCollector` via `PerAppSingleton` (`modules.py:96,102`, scope class at `scopes.py:71-86`) | `SystemClock` is stateless, so sharing snake-guice's process-global `SINGLETON` cache across `create_app()` calls is harmless. `MetricsCollector` is stateful counters — if it used `SINGLETON` too, every `create_app()` (e.g. each test) would share one counter, since `SINGLETON`'s cache is keyed only by `(interface, annotation)`. `PerAppSingleton` gives each `MetricsModule` instance (one per `create_app()`) its own cache. | `app.state.clock = SystemClock()` and `app.state.metrics = MetricsCollector()` in `fastapi_native/main.py` — each `create_app()` call naturally gets fresh `app.state`, so there's no equivalent pitfall to avoid. |
| `@inject` / `@annotate` | `TaskRepository.__init__` (`repository.py:16-17`): `@inject` + `@annotate(reader="reader", writer="writer")`; also `listeners.py:30,42`, `service.py:15`, `modules.py:37` | `@inject` lets the injector build constructor dependencies automatically; `@annotate` disambiguates which `Session` binding (`"reader"` vs `"writer"`) each parameter should resolve to, while `clock: Clock` stays unannotated and resolves from `ClockModule`'s single binding. | No equivalent — `TaskRepository(reader, writer, clock)` is called directly inside a `Depends()` function (`fastapi_native/deps.py:get_task_repository`) with the right session passed positionally. |
| `to=` / `to_instance=` / `to_provider=` | `to=`: `binder.bind(Clock, to=SystemClock, ...)` (`modules.py:81`). `to_instance=`: `binder.bind(IDatabase, to_instance=self._database)` (`modules.py:51,67`; rationale in `db.py`). `to_provider=`: `binder.bind(Session, ..., to_provider=_SessionProvider, ...)` (`modules.py:55,71`) | Three ways to satisfy one binding: build via the injector (`to=`), reuse a pre-built object (`to_instance=` — here, a `Database` constructed eagerly so reader/writer don't share a `SINGLETON`-cached `IDatabase`), or run custom logic on every resolution (`to_provider=`, here `IDatabase.get_session()`). | No equivalent — every dependency is either a plain function call or an `app.state` attribute lookup. |

## Dependency-wiring size

`fastapi_native/deps.py` has **9** `Depends()` provider functions, one per
cross-cutting concern and one per layer of the call graph: `get_databases` →
`get_reader_session`/`get_writer_session` → `get_clock`, `get_logger`,
`get_metrics` → `get_task_listeners` → `get_task_repository` →
`get_task_service`.

`fastapi_snakeguice/deps.py` has **1**: `from_injector(cls)`, a generic
`Depends()`-producing helper that resolves any type via
`request.app.state.injector.get_instance(cls)`. Routes use it inline -
`service: TaskService = from_injector(TaskService)`,
`metrics: MetricsCollector = from_injector(MetricsCollector)`. The rest of the
graph — `TaskRepository`, `TaskService`, `TaskListener`s, `Session`s, `Clock` —
is resolved by `injector.get_instance` without any FastAPI-facing code,
regardless of how deep it gets.

That gap widens with each new cross-cutting concern. Adding a third listener
(say, a `NotificationListener` that depends on some `NotificationService`):

- **Native**: add the class, add a `get_notification_service` `Depends()`
  function (10th function), and add one line to `get_task_listeners` to
  include it in the returned list.
- **snake-guice**: add the class with `@inject`, add (or extend) a `Module`
  that binds its dependencies and calls
  `ListBinder(binder, List[TaskListener]).add_binding(to=NotificationListener)`,
  and install that module in `AppModule.configure`. `deps.py` and `routes.py`
  are untouched entirely.

## What was left out

`@provides` (factory methods on a `Module`), assisted injection
(`@assisted_inject` / `AssistProvider`), and `ParameterInterceptor` were all
considered. None has a natural home in this domain without inventing a need
for it — every binding here is either a straightforward class, a pre-built
instance, or a small custom provider, and nothing needs "inject most
constructor args but pass the rest at call time" or "intercept one named
parameter." Forcing them in would make the example less representative of
when you'd actually reach for snake-guice.
