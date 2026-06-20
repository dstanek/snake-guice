# Using Providers with snake-guice

## Introduction

Most bindings just point an interface at an implementation class
(`binder.bind(IEngine, to=SmallBlockEngine)`) and let snake-guice construct it.
Sometimes that isn't enough - you need to compute, look up, or otherwise build
a value yourself. That's what a `Provider` is for.

A provider is any object with a `get()` method that returns the instance. This
contract is defined as `snakeguice.interfaces.Provider`:

```python
class Provider(Protocol[T]):
    def get(self) -> T: ...
```

Bind to a provider with `to_provider=` instead of `to=`. You can pass either
a provider class (snake-guice instantiates it, so it can itself be injected)
or a pre-built provider instance:

```python
binder.bind(IEngine, to_provider=TurboEngineProvider)   # class
binder.bind(IEngine, to_provider=TurboEngineProvider())  # instance
```

## A Simple Provider

A provider class just needs a `get()` method. snake-guice will instantiate the
provider class itself (so it can be injected too) before calling `get()`:

```python
class TurboEngineProvider:
    def get(self) -> IEngine:
        engine = SmallBlockEngine()
        engine.add_turbo()
        return engine


class AutoModule:
    def configure(self, binder):
        binder.bind(IEngine, to_provider=TurboEngineProvider)
```

Whenever something needs an `IEngine`, snake-guice creates a
`TurboEngineProvider` and calls `.get()` on it.

## Injectable Providers

Because the provider class is itself created with `get_instance`, it can have
its own `@inject`-decorated `__init__` and depend on other bindings - including
the `Injector` itself. This is handy when the value you want to provide depends
on some runtime context:

```python
from snakeguice.interfaces import Injector


class SessionProvider:
    @inject
    def __init__(self, injector: Injector) -> None:
        self._injector = injector

    def get(self) -> Session:
        request_context = self._injector.get_instance(RequestContext)
        return request_context.session


class WebModule:
    def configure(self, binder):
        binder.bind(Session, to_provider=SessionProvider)
```

Every class that has a `Session` injected will go through `SessionProvider`,
which resolves the session for the current request via whatever
`RequestContext` binding is active.

## `@provides`: Factory Methods on a Module

For simple cases, writing a whole provider class is more ceremony than the
value deserves. A module method decorated with `@provides(SomeType)` is
collected automatically and used as a factory for `SomeType`. Combine it with
`@inject` to pull in dependencies:

```python
from snakeguice import inject, provides


class AutoModule:
    def configure(self, binder):
        binder.bind(IEngine, to=SmallBlockEngine)

    @provides(IDashboard)
    @inject
    def provide_dashboard(self, engine: IEngine) -> IDashboard:
        return Dashboard(redline=engine.max_rpm)
```

No explicit `binder.bind(IDashboard, ...)` call is needed - the `@provides`
decorator takes care of it when the module is installed.

## Deferred Resolution with `get_provider`

`Injector.get_instance(cls)` resolves immediately. If you're holding onto the
injector and want to defer resolution - say, to get a fresh instance each time,
or to avoid building something until it's actually needed - use
`get_provider()`:

```python
provider = injector.get_provider(IEngine)
...
engine = provider.get()  # resolved now, not when get_provider() was called
```

`get_provider()` returns a small wrapper whose `.get()` just calls
`injector.get_instance(cls, annotation)`, so it honors the same bindings and
scopes as a normal lookup.

## Providers and Scopes

A binding's scope wraps whatever provider it points to. With the default
`scopes.NO_SCOPE`, `.get()` runs every time the binding is resolved. With
`scopes.SINGLETON`, the provider's `.get()` runs once and the result is cached
for the lifetime of the injector:

```python
binder.bind(IEngine, to_provider=TurboEngineProvider, in_scope=scopes.SINGLETON)
```
