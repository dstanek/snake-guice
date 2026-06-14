# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
- `make lint` — flake8, black --check, isort --check, mypy
- `make fmt` — black + isort (auto-fix)
- Single test: `uv run pytest tests/test_injector.py::test_create_child -vv`

## Architecture

**Resolution flow** (`injector.py`): `Injector.get_instance(cls, annotation)`
builds a `Key(interface, annotation)` and looks up a `Binding` in the `Binder`
(binders chain to a parent via `create_child()`, so child injectors
inherit/override parent bindings). If bound: a provider class is itself
instantiated via `get_instance` (providers are injectable), then resolved
through `binding.scope.scope(key, provider).get()`. If unbound: implicitly
`create_object(cls)` (injects `__init__` params) then `inject_members` (calls
any `@inject`-decorated methods).

**Decorators** (`decorators.py`, `_extractor.py`):
- `@inject` requires type annotations on all non-`self` params; on
  non-`__init__` methods it records the method name in `__guice_methods__`.
- `@annotate(param=value, ...)` sets `__guice_annotations__`; must be applied
  *before* `@inject` (i.e. listed below it).
- `@provides(SomeType)` marks a module method as a factory for `SomeType`
  (collected by `ProvidesBinderHelper`).
- `extract_params(method)` combines `__annotations__` +
  `__guice_annotations__` into `Param(name, dtype, annotation)`.

**Modules** (`modules.py`): a "simple module" just needs `configure(binder)`; a
`Module` subclass also gets `run_configure` (sets `_injector` first).
`Module.install(binder, other)` composes modules. `PrivateModule` creates an
isolated child injector and `expose()`s individual bindings to the parent
binder (robot-legs pattern, see `tests/system/test_private_modules.py` and
`docs/source/private_modules.md`).

**Providers/scopes**: `providers.create_simple_provider(cls)` builds via
`injector.create_object`; `create_instance_provider(obj)` returns a fixed
value. `scopes.NO_SCOPE` (default) is a pass-through; `scopes.SINGLETON` caches
the first instance per `Key`.

**Multibinder** (`multibinder.py`): `ListBinder`/`DictBinder` let multiple
modules contribute to one `List[T]`/`Dict[str, T]` binding; `DictBinder` raises
`MultiBindingError` on duplicate keys.

**Assisted injection** (`assist.py`): `@assisted_inject("name", "date")` marks
`__init__` params supplied at call time instead of injected;
`AssistProvider(cls)` builds a `.create(**kwargs)` factory for the rest.

**Other**: `interceptors.ParameterInterceptor` injects a single named param into
a method call. `config.ConfigParserLoader` binds `.ini` values as
`Config("file:section:option")`. `extras/snakeweb.py` wraps the `routes`
library for WSGI. `binder.LazyBinder` is unused/dead code.

## Tests

- `tests/` — pytest suite (`make tests`); `tests/cls_heirarchy.py` has shared
  fixture classes used across modules.
- `tests/system/` — end-to-end API tests.
- `specs/` — legacy `describe_*/when_*/then_*` BDD specs, **not** run by
  `make tests` or CI; useful as design reference only.
- `examples/` — runnable sample apps, not part of tests/lint.
