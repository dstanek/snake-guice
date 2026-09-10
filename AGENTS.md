# AGENTS.md

This file provides guidance to AI coding agents (Claude Code, etc.) when working with code in this repository.

snake-guice is a small Python dependency-injection framework modeled on
[Google Guice](https://github.com/google/guice) (pre-1.0/alpha API). Single
package `snakeguice`, uv-managed, Python `>=3.10`. VCS is Jujutsu (jj),
colocated with git.

## Code Style

- Always write concise code.
- Advanced patterns are ok.

## Commands

- `uv sync` — install deps
- `make all` — fmt + lint + tests (what CI runs)
- `make tests` — `pytest -vv tests`
- `make lint` — ruff check, ruff format --check, mypy, basedpyright (snakeguice only)
- `make fmt` — ruff check --fix + ruff format (auto-fix)
- Single test: `uv run pytest tests/test_injector.py::test_create_child -vv`

## Architecture

**Resolution flow** (`injector.py`): `Injector.get_instance(cls, annotation)`
builds a `Key(interface, annotation)` and looks up a `Binding` in the `Binder`
(binders chain to a parent via `create_child()`, so child injectors
inherit/override parent bindings). If bound: a provider class is itself
instantiated via `get_instance` (providers are injectable), then resolved
through `binding.scope.scope(key, provider).get()`. If unbound and the key is
unannotated: implicitly `create_object(cls)` (injects `__init__` params) then
`inject_members` (calls any `@inject`-decorated methods). If unbound and the
key *is* annotated: raise `MissingBindingError` - an annotation names one
specific binding, so a miss is a mismatch rather than a request to implicitly
construct something.

In-flight resolution state - the `(injector, key)` chain used for
`CircularDependencyError`, and the `Binding` currently being handed to
`scope.scope()` - lives in `_context.py` as `ContextVar`s, not on the
`Injector` instance, so a shared `Injector` resolves correctly from multiple
threads or concurrent `asyncio` tasks at once. `_format_chain()` marks a hop
to a different injector as `-> [different injector] ->` in the error message,
since the same `Key` can legitimately repeat across a `PrivateModule.expose()`
boundary.

**Decorators** (`decorators.py`, `_extractor.py`):
- `@inject` requires type annotations on all non-`self` params; on
  non-`__init__` methods it records the method name in `__guice_methods__`.
- `@annotate(param=value, ...)` sets `__guice_annotations__`; either ordering
  relative to `@inject` works — convention is `@inject` above `@annotate`.
- `@provides(SomeType)` marks a module method as a factory for `SomeType`
  (collected by `ProvidesBinderHelper`).
- `extract_params(method)` combines `__annotations__` +
  `__guice_annotations__` into `Param(name, dtype, annotation)`.

**Modules** (`modules.py`): a "simple module" just needs `configure(binder)`; a
`Module` subclass also gets `run_configure`, whose default (`_configure()`)
also collects the module's `@provides` methods onto the same binder as
`configure()`. `Module._injector` is a property,
not a plain attribute - it reads back from an ambient `ContextVar` stack
(`_configuring`) that `ModuleAdapter.configure()` pushes/pops around each
`configure()` call, keyed by module identity rather than stored on the module
instance, so one `Module`/`PrivateModule` instance can safely configure more
than one injector (e.g. two `create_injector()` calls sharing a module).
`Module.install(binder, other)` composes modules. `PrivateModule` creates an
isolated child injector and `expose()`s individual bindings to the parent
binder (robot-legs pattern, see `tests/system/test_private_modules.py` and
`docs/source/private_modules.md`); its own per-`run_configure()`-call state
(`original_binder`, `exposed_keys`, `private_injector`) is likewise held
ambiently (`private_module.py`'s `_current_run`), for the same reason.

**Providers/scopes**: `providers.create_simple_provider(cls)` builds via
`injector.create_object`; `create_instance_provider(obj)` returns a fixed
value. `scopes.NO_SCOPE` (default) is a pass-through. `scopes.SINGLETON`
caches the first instance per `Key`, per injector: the cache lives on the
`Binding` (found via the same ambient context as above), not on the shared
`Singleton` object, so independent injectors don't share a cache - a
`create_child()` injector still does, inheriting the parent's `Binding`.
First construction is guarded by a per-binding lock (`Binding.scope_lock`) so
concurrent callers building the same singleton construct exactly once, and
unrelated singletons never wait on each other. `scopes.THREAD_LOCAL` is the
same idea scoped per-thread instead of per-injector.

**Multibinder** (`multibinder.py`): `ListBinder`/`DictBinder` let multiple
modules contribute to one `List[T]`/`Dict[str, T]` binding; `DictBinder` raises
`MultiBindingError` on duplicate keys.

**Assisted injection** (`assist.py`): `@assisted_inject("name", "date")` marks
`__init__` params supplied at call time instead of injected;
`AssistProvider(cls)` builds a `.create(**kwargs)` factory for the rest.

**Configuration errors** (`binder.py`): `Binder.bind()` never raises directly -
problems (duplicate `Key`, invalid `to=`/`to_provider=`, no target at all)
are recorded via
`add_error()` as `BinderErrorRecord`s. After running every module,
`Injector.__init__` calls `binder.raise_if_errors()`, which raises one
`CreationError` (a `BindingError` subclass) with a numbered list of every
problem and its source location.

**Other**: `interceptors.ParameterInterceptor` injects a single named param into
a method call. `config.ConfigParserLoader` binds `.ini` values as
`Config("file:section:option")`. `extras/snakeweb.py` wraps the `routes`
library for WSGI.

## Tests

- `tests/` — pytest suite (`make tests`); `tests/cls_heirarchy.py` has shared
  fixture classes used across modules.
- `tests/system/` — end-to-end API tests.
- `examples/` — runnable sample apps, not part of tests/lint.

## Gotchas

- **Reproduce version-dependent behavior on the pinned 3.12**
  (`.python-version`), not whatever is on `PATH`. Python 3.14 defers
  annotation evaluation (PEP 649), so undefined names in a signature raise
  `NameError` on 3.10-3.13 but not on 3.14 — a doc snippet can look fine on
  3.14 while being broken for four of the five supported versions. Check with
  `uv run --no-project -p 3.12 python <snippet>`.
- **A stale `.venv/`** (shebangs pointing at a previous checkout path) makes
  `uv`-mediated commands fail for unrelated-looking reasons. `uv sync
  --reinstall` clears it.
- **API references live outside `docs/` too** — this file's Architecture
  section and `README.md` both name specific methods and describe
  behavior. When renaming an identifier or changing resolution/binding
  behavior, grep both, not just the docs tree. (`docs/_build/` is
  generated output; ignore it.)
