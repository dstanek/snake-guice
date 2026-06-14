# WebApp Example

This walks through a minimal WSGI web application wired up with snake-guice,
using the `snakeguice.extras.snakeweb` helpers, which combine
[Routes](https://routes.readthedocs.io/) (URL dispatch) and
[WebOb](https://webob.org/) (request/response objects).

## Setup

Install snake-guice along with Routes and WebOb:

```bash
pip install snake-guice routes webob
```

## A Controller with an Injected Dependency

The point of using snake-guice here is that controllers don't have to build
their own dependencies - they just declare what they need. Create
`controllers.py`:

```python
from webob import Request, Response

from snakeguice import inject


class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello, {name}!"


class GreeterController:
    @inject
    def __init__(self, greeter: Greeter) -> None:
        self._greeter = greeter

    def index(self, request: Request) -> Response:
        name = request.params.get("name", "world")
        return Response(self._greeter.greet(name))
```

Because `Greeter` isn't explicitly bound to anything, snake-guice will
construct it directly the first time a `GreeterController` is created - see
[Guice Basics](../guicebasics.md) for why that "implicit binding" works. In a
real application you'd bind `Greeter` to an interface so it can be swapped out
(for testing, or for a different greeting strategy) without touching
`GreeterController`.

## Wiring Up Routes

`AutoRoutesModule` maps URL paths to controller classes. Create `app.py`:

```python
from wsgiref.simple_server import make_server

from snakeguice import create_injector
from snakeguice.extras.snakeweb import AutoRoutesModule, Application

from controllers import GreeterController


class AppModule(AutoRoutesModule):
    configured_routes = {
        "/": GreeterController,
    }


def main() -> None:
    injector = create_injector([AppModule()])
    app = Application(injector)

    httpd = make_server("", 8000, app)
    print("Serving on port 8000...")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
```

A route mapped to a class via `configured_routes` dispatches to that class's
`index` action. `Application` resolves the controller with
`injector.get_instance(GreeterController)` for every request, so `Greeter` is
injected fresh each time.

## Running It

```bash
$ python app.py
Serving on port 8000...
```

Then visit:

* http://localhost:8000/ - "Hello, world!"
* http://localhost:8000/?name=Ada - "Hello, Ada!"

## Adding More Routes

`AutoRoutesModule.configured_routes` maps each path to a controller class,
dispatching to that class's `index` action:

```python
class AppModule(AutoRoutesModule):
    configured_routes = {
        "/": GreeterController,
        "/about": AboutController,
    }
```

For routes that need more control - URL segments like `:name`, custom HTTP
method conditions, etc. - override `configure()` instead of using
`configured_routes`, and call `routes_binder.connect(...)` directly (it accepts
the same arguments as
[`routes.Mapper.connect`](https://routes.readthedocs.io/)). Matched URL
segments are passed to the action as keyword arguments:

```python
from snakeguice.extras.snakeweb import RoutesBinder, RoutesModule


class GreeterController:
    @inject
    def __init__(self, greeter: Greeter) -> None:
        self._greeter = greeter

    def index(self, request: Request) -> Response:
        name = request.params.get("name", "world")
        return Response(self._greeter.greet(name))

    def show(self, request: Request, name: str) -> Response:
        return Response(self._greeter.greet(name))


class AppModule(RoutesModule):
    def configure(self, routes_binder: RoutesBinder) -> None:
        routes_binder.connect("/", controller=GreeterController, action="index")
        routes_binder.connect(
            "/greet/:name", controller=GreeterController, action="show"
        )
```

`/greet/Ada` now dispatches to `GreeterController.show(request, name="Ada")`.
