# Parameter Interceptors

`@inject` resolves a class's dependencies once, when the instance is
constructed. Sometimes you want a dependency resolved *per call* instead - for
a single parameter on a single method, without making it part of the class's
constructor. `ParameterInterceptor` does this.

## Creating an Interceptor

`ParameterInterceptor(injector)` builds a decorator factory bound to a
specific injector:

```python
from typing import Any

from snakeguice import ParameterInterceptor, create_injector
from snakeguice.interfaces import Binder


class IKeyCard:
    """Interface for a garage key card."""


class MasterKeyCard(IKeyCard):
    pass


class GuestKeyCard(IKeyCard):
    pass


class SecurityModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IKeyCard, annotated_with="master", to=MasterKeyCard)
        binder.bind(IKeyCard, annotated_with="guest", to=GuestKeyCard)


injector = create_injector([SecurityModule()])
intercept = ParameterInterceptor(injector)
```

## Decorating a Method

`@intercept(name=Type, annotation=...)` wraps a method so that calling it
always supplies `name` by resolving `Type` (with the given `annotation`, if
any) from the injector - the caller never passes it:

```python
class Garage:
    @intercept(key_card=IKeyCard, annotation="master")
    def open(self, key_card: Any = None) -> str:
        return f"opened with {type(key_card).__name__}"


garage = injector.get_instance(Garage)
assert garage.open() == "opened with MasterKeyCard"
```

`key_card` is filled in by `intercept` on every call - it's resolved fresh
each time, the same way `get_instance(IKeyCard, "master")` would be.

`@intercept(...)` takes exactly one `name=Type` keyword argument, plus the
optional `annotation=`. Interceptors stack, so a method can have several
injected parameters, each resolved independently:

```python
class Garage:
    @intercept(master=IKeyCard, annotation="master")
    @intercept(guest=IKeyCard, annotation="guest")
    def audit(self, master: Any = None, guest: Any = None) -> str:
        return f"{type(master).__name__}, {type(guest).__name__}"


garage = injector.get_instance(Garage)
assert garage.audit() == "MasterKeyCard, GuestKeyCard"
```

```{warning}
Passing a managed parameter explicitly raises `TypeError`:

    garage.open(key_card=some_card)  # TypeError

The parameter is always resolved by the injector; the caller must not supply it.
```

```{note}
Unlike `@inject`, `ParameterInterceptor` doesn't validate type annotations and
doesn't require the intercepted parameter to be annotated at all - it just
injects a keyword argument by name before calling the underlying method.
```
