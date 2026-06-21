# Refactoring notes

## Why `Module` currently knows about `Injector`

Conceptually, the core roles in this codebase are:

- `Binder`: stores bindings.
- `Binding`: describes how a key is resolved.
- `Injector`: resolves keys into instances at runtime.
- `Module`: contributes bindings to a binder.

In a clean separation, a module would only need a binder. In the current
implementation, `Module` subclasses can also receive the current injector.
That exists to support configuration-time behavior that goes beyond simply
declaring bindings.

The main places this shows up are:

- `Injector.add_modules()` passes itself into `ModuleAdapter`.
- `ModuleAdapter` calls `set_injector()` when a module supports it.
- `Module.install()` reuses that injector when installing another module.
- `PrivateModule.run_configure()` uses `self._injector.create_child(...)` to
  build an isolated child injector.

So the injector reference is not really for ordinary modules. It exists mainly
for advanced module behavior such as module composition and private child
injectors.

## What is awkward about the current design

This couples configuration-time concepts to runtime concepts:

- A module is supposed to describe bindings.
- An injector is supposed to resolve instances from bindings.

When a module needs the injector during configuration, those responsibilities
start to blur. Most modules do not need `get_instance()` or any runtime
resolution behavior, but the API currently exposes the larger concept anyway.

## A better direction

The cleanest decoupling is to separate configuration-time APIs from runtime
resolution APIs and stop handing the full injector to modules.

### Principles

1. Modules should configure only against a binder-like API.
2. The injector should be created after configuration is complete.
3. Special features should depend on narrower collaborators than `Injector`.

## Possible abstraction split

| Concern | Better abstraction |
| --- | --- |
| Add bindings | `Binder` |
| Install submodules | `ModuleInstaller` or `binder.install(module)` |
| Create private scopes | `PrivateBinder` or `PrivateModuleContext` |
| Resolve instances at runtime | `Injector` |

With that split, the design becomes more explicit:

- `Module.configure(binder)`
- `PrivateModule.configure(private_binder)`
- `Injector` used by providers and runtime injection only

## Refactoring approach

The most natural redesign is a two-phase bootstrap:

### Phase 1: configuration

Modules build a tree of binders or private binders. No runtime resolution
occurs here.

### Phase 2: runtime assembly

Injectors are constructed from that configured binder tree and are then used
for instance resolution.

## Where to start

If refactoring incrementally, `PrivateModule` is the best first target because
it is the clearest place where configuration currently depends on injector
behavior.

The goal would be to replace its need for `self._injector.create_child(...)`
with a narrower configuration-time abstraction that can:

- create a private binding scope
- record exposed bindings
- assemble child/parent relationships before runtime injector creation

## Expected payoff

This would make the architecture easier to reason about:

- modules stay declarative
- injectors stay operational
- advanced features remain possible without exposing runtime APIs everywhere

That separation should also make future features easier to implement and test,
because configuration and resolution would be modeled as distinct phases.
