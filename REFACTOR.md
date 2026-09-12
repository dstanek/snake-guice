# Refactoring notes

## Status

Steps 1-4 below are done, on the line above `00ec0569`:

- `e67aded6` per-binding singleton lock (step 1's follow-up)
- `819e802a` `@provides` bound on the same binder as `configure()` (step 2)
- `13b3f45a` `PrivateBinder` and the two-phase bootstrap (step 3)
- `61a5b247` module-side injector plumbing deleted (step 4)

`modules.py` and `private_module.py` no longer reference the injector at
all; a module's only collaborator is its binder. Step 5, the `Binder`
protocol, is still open. The sections below describe the design as it was
when the decision was made, and the plan that was followed.

## Why `Module` knew about `Injector`

Conceptually, the core roles in this codebase are:

- `Binder`: stores bindings.
- `Binding`: describes how a key is resolved.
- `Injector`: resolves keys into instances at runtime.
- `Module`: contributes bindings to a binder.

In a clean separation, a module would only need a binder. Before this refactor,
`Module` subclasses could also reach the current injector.
That exists to support configuration-time behavior that goes beyond simply
declaring bindings.

The places this showed up, as of the concurrency change (`51cf06ee`):

- `Injector._add_modules()` passes itself into `ModuleAdapter`.
- `ModuleAdapter.configure()` pushes a `(module, injector)` frame onto an
  ambient `ContextVar` stack (`modules._configuring`) around each
  `configure()` call, for any module that has a `set_injector` attribute.
  `Module.set_injector()` itself is now a no-op that exists only to be found
  by that check.
- `Module._injector` is a property that searches that stack for the frame
  pushed for `self`, rather than trusting the innermost frame, because
  `PrivateModule` runs `configure()` one layer down inside a wrapper.
- `Module.install()` reuses that injector when installing another module.
- `PrivateModule.run_configure()` uses `self._injector.create_child(...)` to
  build an isolated child injector, and keeps its per-run state
  (`original_binder`, `exposed_keys`, `private_injector`) in a second
  ambient `ContextVar` (`private_module._current_run`) so that `expose()` can
  find it from inside `configure()`.
- `_PrivateModuleWrapper` exists solely to stop the child injector from
  calling `run_configure()` again.

So the injector reference is not for ordinary modules. It exists for module
composition and private child injectors, and three ambient mechanisms exist
only to deliver it safely to a `configure()` call that has no parameter for
it.

## What was awkward about that design

This couples configuration-time concepts to runtime concepts:

- A module is supposed to describe bindings.
- An injector is supposed to resolve instances from bindings.

When a module needs the injector during configuration, those responsibilities
blur. Most modules do not need `get_instance()` or any runtime resolution
behavior, but the API exposes the larger concept anyway.

The coupling has a second, concrete cost: configuration runs against a module
*instance*, so per-run state ends up attached to an object whose lifetime the
user controls. That was BUGS.md's B5 (reusing a `PrivateModule` across two
injectors repointed the first one). The concurrency change fixed the symptom
by moving that state into the ambient `ContextVar`s listed above. That is
scaffolding, not design: it is correct, and it is exactly what this refactor
should delete.

Two bugs were direct consequences of the coupling (both fixed by steps 2 and 3):

1. **`@provides` on a `PrivateModule` binds to the parent binder** (BUGS.md
   B2). `Injector._add_modules()` runs the `@provides` scan
   against the injector's own binder, while `ModuleAdapter` has independently
   routed `configure()` into the private child. Two binders in play for one
   module.
2. **Nested private modules parent to the wrong injector.** A `PrivateModule`
   installed from inside another `PrivateModule.configure()` builds its
   private injector from `self._injector`, which is the *outer* injector, not
   the enclosing private one. It therefore cannot see the enclosing module's
   private bindings and silently falls through to implicit construction:
   a `Secret` bound `to=RealSecret` in the outer private module resolves as a
   plain `Secret` in the inner one. Verified on the current code and on the
   commit before the concurrency change; it is pre-existing.

Under a design with one binder per module and no injector at configuration
time, neither bug can be expressed.

## A better direction

Separate configuration-time APIs from runtime resolution APIs and stop
handing the injector to modules.

### Principles

1. Modules configure only against a binder-like API.
2. Injectors are created after configuration is complete.
3. Special features depend on narrower collaborators than `Injector`.

## Abstraction split

| Concern | Abstraction |
| --- | --- |
| Add bindings | `Binder` |
| Install submodules | `binder.install(module)` |
| Create private scopes | `PrivateBinder` (a child `Binder` that records exposures) |
| Resolve instances at runtime | `Injector` |

With that split:

- `Module.configure(binder)` is the whole module API; `Module.install()` and
  `PrivateModule.expose()` keep their signatures and delegate to the binder.
- `Injector` is used by providers and runtime injection only.

## Refactoring approach: two-phase bootstrap

### Phase 1: configuration

Modules build a tree of binders. A `PrivateBinder` is a child of the binder
that installed it, records which keys are exposed, and validates the
exposures when its configuration ends. No runtime resolution occurs.

### Phase 2: runtime assembly

`Injector.__init__` builds the root injector from the root binder, then one
injector per recorded `PrivateBinder`, eagerly. Exposure providers resolve
through the injector built for their private binder.

Two decisions to make explicit:

- **Eager, not lazy, child injectors.** Cycle-detection frames and
  `Injector` self-injection key on injector identity; building them once in
  phase 2 keeps that identity stable.
- **Nested private binders parent to the enclosing private binder**, which
  is Guice's semantics and fixes bug 2 above by construction.

The runtime side is untouched by this: the resolution chain and current
binding in `_context.py`, and the cache and lock slots on `Binding`, are
runtime concerns and stay as they are.

## Order of work

1. **Land the concurrency change first.** Its tests for module reuse,
   private-module cycles and threaded resolution are the regression net the
   refactor runs under.
2. **`Binder.install(module)`** that runs `configure()` *and* the
   `@provides` scan against the binder it was given, with `Module.install()`
   delegating to it. Fixes B2 on its own and removes the injector from module
   composition. Small and independently shippable.
3. **`PrivateBinder`** plus the phase-2 assembly in `Injector.__init__`.
   Deletes `_PrivateModuleWrapper`, `private_module._current_run` and the
   `create_child()` call in `run_configure()`; fixes nested parenting.
4. **Delete the module-side injector plumbing**: `Module.set_injector`,
   `Module._injector`, `modules._configuring`, and the injector parameter of
   `ModuleAdapter`. Update the User Guide sentence that says `Module`
   "tracks `self._injector`".
5. **Promote `interfaces.Binder` from `Any` to a real Protocol** as its own
   change (BUGS.md T1). The new binder surface is what to type, and the
   `bind()` overloads already exist.

## Public API impact

- `configure(binder)`, `install(binder, module)` and
  `expose(binder, interface, annotation)` keep their signatures.
- `Module.run_configure(binder)` stays as the documented hook (Extending
  guide); `PrivateModule` simply no longer needs it to build an injector.
- `Module.set_injector` and `Module._injector` go away. Nothing in the docs
  relies on them beyond the one User Guide sentence above.
- `extras/snakeweb.py` obtains its injector by runtime injection, so it is
  unaffected.
- `Injector.create_child(modules)` becomes: child binder, install modules,
  build injector.

## Alternatives considered

- **A narrower configuration-context object handed to modules instead of
  the injector.** A half-measure: configuration would still run inside
  injector construction, and B2 and nested parenting would each need
  special-casing.
- **Guice-style element lists** (modules produce binding elements that an
  injector builder interprets). The same idea with an intermediate
  representation this codebase does not need; the binder tree already is the
  configuration output.

## Expected payoff

- Modules stay declarative; injectors stay operational.
- Three ambient mechanisms and one wrapper class are deleted, and two open
  bugs become structurally impossible.
- Configuration and resolution are modeled as distinct phases, which makes
  future features (eager singletons, binding validation, a real
  `Binder` protocol) easier to implement and test.
