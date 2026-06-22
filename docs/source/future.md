# What's Missing

[DI Patterns](patterns.md) covers what snake-guice can do today. This page is
the flip side: patterns that are common in Guice and other DI frameworks but
that snake-guice doesn't support yet - either the feature doesn't exist, or an
existing feature has a sharp edge that rules it out. None of these are used
anywhere in `examples/` or `tests/`, because they can't be.

## Eager / validated injectors (`Stage.PRODUCTION`)

Guice can validate the entire binding graph - and eagerly construct every
`asEagerSingleton()` - at injector-creation time, so a missing or
unsatisfiable binding fails at startup. `create_injector()`/`Injector(...)`
does none of this: bindings are only checked lazily, when `get_instance()` is
actually called for that `(interface, annotation)` key. A typo affecting a
rarely-used code path won't surface until that path runs.

## Eager singletons

Relatedly, `scopes.SINGLETON` (and any custom scope) is lazy - the first
`get_instance()` call wins. There's no `asEagerSingleton()`-style declaration
that forces construction (and any constructor side effects) at
injector-creation time.

## Binding overrides (`Modules.override()`)

Guice's `Modules.override(prodModule).with(testModule)` lets a test replace
just the bindings it cares about while keeping the rest of the production
wiring. snake-guice's `Binder` records an error the second time the same
`(interface, annotation)` is bound in the same binder, raised as
`CreationError` (a `BindingError` subclass) once the injector is created -
there's no "last one wins" or override mechanism. The closest options today
are writing a complete alternate module (see [Swapping Implementations in
Tests](userguide.md#why-it-matters-swapping-implementations-in-tests)) or
`create_child()` (overrides apply only to resolutions made through the child
injector, not the parent's).

## General method interception (AOP)

Guice's `bindInterceptor()` wraps arbitrary methods - matched by class/method
predicates - with a `MethodInterceptor`, the basis for things like
`@Transactional`. snake-guice's [`ParameterInterceptor`](parameter_interceptors.md)
only injects one named keyword argument into a method call; it has no
before/after/around hooks and can't wrap the call itself, change arguments, or
change the return value.

## Optional bindings

Guice's `OptionalBinder` lets a dependency be "bound if some module provides
it, otherwise absent/default" - the basis for optional plugins. snake-guice
has no equivalent: an interface with no binding either falls back to implicit
construction (if it's a concrete, injectable class) or fails outright. There's
no way to ask "give me `None` if nothing bound this."

## Contributing to multibindings from `@provides`

Guice's `@ProvidesIntoSet`/`@ProvidesIntoMap` let a `@Provides` method
contribute its return value directly to a multibinding. snake-guice's
[`@provides`](using_providers.md#provides-factory-methods-on-a-module) only
produces a single-value binding (`binder.bind(type, to_provider=...)`);
contributing to a `ListBinder`/`DictBinder` means calling `add_binding()`
directly in `configure()` instead.

## `@provides` with `annotated_with=` / `in_scope=`

`@provides(SomeType)` always produces an unannotated, `NO_SCOPE` binding -
there's no `@provides(SomeType, annotated_with="x", in_scope=scopes.SINGLETON)`.
A factory-method-style provider that needs an annotation or a scope has to be
rewritten as an explicit provider class bound with
`binder.bind(SomeType, annotated_with=..., to_provider=..., in_scope=...)`
instead.

## Generic container bindings beyond `list[T]` / `dict[str, T]`

[`ListBinder`/`DictBinder`](multibinder.md) are the only multibinding shapes.
There's no `Set[T]`, no `Optional[T]` ("bind this if available"), and no way to
register an arbitrary generic type as a first-class injectable shape - `Key`
equality for generics is hardcoded around `List` and `Dict`.

## Circular dependency support

Guice can resolve some circular dependencies - e.g. by injecting a
`Provider<T>` to break the cycle, or via proxies for circular singletons.
snake-guice has no cycle detection or breaking: two implicitly-constructed
classes that depend on each other (directly or transitively) recurse until
`RecursionError`.

## Built-in web-request/session scopes

Guice ships `@RequestScoped`/`@SessionScoped` (via `guice-servlet`) as
ready-made scopes for web frameworks. snake-guice has no built-in equivalent
for any framework -
[`FastAPIRequestScope`](../../examples/fastapi_tasks/fastapi_snakeguice/scopes.py)
in `examples/fastapi_tasks` shows the pattern (a `ContextVar`-backed cache plus
middleware that resets it per request and cleans up afterward), but every
integration has to write its own.
