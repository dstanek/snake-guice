# Assisted Injection

Most injected classes get *all* of their `__init__` parameters from the
injector. Sometimes a class needs a mix: some parameters come from bindings,
but others - a customer's name, a date, anything only known at call time -
can only come from the caller. **Assisted injection** lets a class declare
both kinds of parameters and gives you a factory for building it.

## Marking Assisted Parameters

`@assisted_inject(*names)` marks which `__init__` parameters are supplied by
the caller instead of the injector. It can only decorate `__init__` -
decorating any other method raises `AssistError` (from `snakeguice.errors`).

```python
from snakeguice import inject
from snakeguice.assist import AssistProvider, assisted_inject
from snakeguice.interfaces import Binder, Factory


class IMechanic:
    """Interface for a mechanic."""


class Mechanic(IMechanic):
    name = "Ada"


class ServiceTicket:
    @assisted_inject("customer_name", "issue")
    @inject
    def __init__(self, mechanic: IMechanic, customer_name: str, issue: str) -> None:
        self.mechanic = mechanic
        self.customer_name = customer_name
        self.issue = issue
```

`mechanic` is an ordinary injected dependency. `customer_name` and `issue` are
assisted - they won't be resolved from a binding, even though they're plain
`str` parameters.

```{note}
`@inject` isn't required here - `@assisted_inject` works on its own as long as
`__init__`'s parameters are type-annotated. Stacking `@inject` on top, as
above, buys you its early validation: a missing annotation raises `TypeError`
at class-definition time instead of surfacing later.
```

## Building a Factory with `AssistProvider`

`AssistProvider(cls)` builds a provider whose `.get()` returns a factory with
a `create(**kwargs)` method. `create()` accepts the assisted parameters,
resolves everything else from the injector, and constructs `cls`:

```python
class IServiceTicketFactory(Factory[ServiceTicket]):
    """Factory for building ServiceTicket instances."""


class ShopModule:
    def configure(self, binder: Binder) -> None:
        binder.bind(IMechanic, to=Mechanic)
        binder.bind(IServiceTicketFactory, to_provider=AssistProvider(ServiceTicket))
```

```python
from snakeguice import create_injector

injector = create_injector([ShopModule()])
factory = injector.get_instance(IServiceTicketFactory)

ticket = factory.create(customer_name="Grace", issue="won't start")

assert isinstance(ticket.mechanic, Mechanic)
assert ticket.customer_name == "Grace"
assert ticket.issue == "won't start"
```

`factory.create()` only accepts the names passed to `@assisted_inject` -
anything else raises `TypeError`:

```python
try:
    factory.create(customer_name="Grace", issue="won't start", oops="x")
except TypeError as e:
    print(e)
    # create() got unexpected keyword argument(s) {'oops'}; expected a
    # subset of {'customer_name', 'issue'}
```

```{note}
`AssistProvider(cls)` requires `cls.__init__` to be decorated with
`@assisted_inject`. Calling it on a class that isn't raises `AssistError`.
```
