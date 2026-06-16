# Multibindings

A normal binding maps one interface to one implementation. Sometimes you want
the opposite: several implementations of the same interface, contributed by
different modules, collected into a single `list[T]` or `dict[str, T]`. That's
what `ListBinder` and `DictBinder` (from `snakeguice.multibinder`) are for.

## `ListBinder`

Each module that wants to contribute gets its own `ListBinder` for the same
`list[T]` type and calls `add_binding()`. All the bindings - across however
many modules use a `ListBinder` for that type - end up in one list:

```python
from snakeguice import create_injector, inject
from snakeguice.interfaces import Binder
from snakeguice.multibinder import ListBinder


class IWarningLight:
    """Interface for a dashboard warning light."""


class CheckEngineLight(IWarningLight):
    pass


class BrakeLight(IWarningLight):
    pass


class EngineModule:
    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[IWarningLight])
        listbinder.add_binding(to=CheckEngineLight)


class BrakeModule:
    def configure(self, binder: Binder) -> None:
        listbinder = ListBinder(binder, list[IWarningLight])
        listbinder.add_binding(to=BrakeLight)


class Dashboard:
    @inject
    def __init__(self, warning_lights: list[IWarningLight]) -> None:
        self.warning_lights = warning_lights


injector = create_injector([EngineModule(), BrakeModule()])
dashboard = injector.get_instance(Dashboard)

assert {type(w).__name__ for w in dashboard.warning_lights} == {
    "CheckEngineLight",
    "BrakeLight",
}
```

`EngineModule` and `BrakeModule` don't need to know about each other, or how
many other modules also contribute `IWarningLight`s - `Dashboard` just sees the
combined list.

`add_binding()` accepts the same three ways of satisfying a binding as
`binder.bind()`:

| argument | meaning |
| --- | --- |
| `to=Implementation` | construct `Implementation` via the injector |
| `to_provider=Provider` | delegate to a `Provider`'s `get()` |
| `to_instance=obj` | always return this exact object |

Elements appear in the list in the order `add_binding()` was called, across
all contributing modules in the order those modules were installed.

## `DictBinder`

`DictBinder` works the same way, but each binding is registered under a string
key, producing a `dict[str, T]`:

```python
from snakeguice.multibinder import DictBinder


class IGauge:
    """Interface for a dashboard gauge."""


class SpeedGauge(IGauge):
    pass


class FuelGauge(IGauge):
    pass


class EngineGaugeModule:
    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, IGauge])
        dictbinder.add_binding("speed", to=SpeedGauge)


class FuelGaugeModule:
    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, IGauge])
        dictbinder.add_binding("fuel", to=FuelGauge)


class GaugeCluster:
    @inject
    def __init__(self, gauges: dict[str, IGauge]) -> None:
        self.gauges = gauges


injector = create_injector([EngineGaugeModule(), FuelGaugeModule()])
cluster = injector.get_instance(GaugeCluster)

assert isinstance(cluster.gauges["speed"], SpeedGauge)
assert isinstance(cluster.gauges["fuel"], FuelGauge)
```

Two modules contributing the same key is an error - `DictBinder` raises
`MultiBindingError` (from `snakeguice.errors`) as soon as the injector is
created:

```python
from snakeguice.errors import MultiBindingError


class DuplicateGaugeModule:
    def configure(self, binder: Binder) -> None:
        dictbinder = DictBinder(binder, dict[str, IGauge])
        dictbinder.add_binding("speed", to=SpeedGauge)
        dictbinder.add_binding("speed", to=FuelGauge)


try:
    create_injector([DuplicateGaugeModule()])
except MultiBindingError as e:
    assert "speed" in str(e)
```
