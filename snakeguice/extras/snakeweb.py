#!/usr/bin/env python

import inspect
from types import MethodType
from typing import Any, Callable

import routes
from webob import Request, Response
from webob.exc import HTTPNotFound

from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.modules import Module

__all__ = ["Response"]


class RoutesBinder:
    def __init__(self, mapper: Any) -> None:
        self.mapper = mapper
        self.controller_map: dict[Any, Any] = {}

    def connect(self, *args: Any, **kwargs: Any) -> None:
        controller = kwargs.get("controller")

        if controller is None:
            raise TypeError("no controller specified")

        key = str((id(controller), repr(controller)))
        self.controller_map[key] = controller
        kwargs["controller"] = key
        self.mapper.connect(*args, **kwargs)

    def match(self, url: str, environ: dict[str, Any]) -> Any:
        # TODO: i have a patch that makes this suck less - i need to submit it
        old_environ, self.mapper.environ = self.mapper.environ, environ
        try:
            return self.mapper.match(url)
        finally:
            self.mapper.environ = old_environ


class RoutesModule(Module):
    def run_configure(self, binder: BinderI) -> None:
        self._mapper = routes.Mapper()
        self._binder = RoutesBinder(self._mapper)
        binder.bind(RoutesBinder, to_instance=self._binder)

        self.configure(self._binder)
        self._mapper.create_regs([])

    # `run_configure` (above) routes `configure()` through `RoutesBinder`
    # instead of the real `Binder` - the deliberate "change the binder"
    # pattern documented in docs/source/extending.md - so this legitimately
    # narrows `Module.configure(binder: Binder)`'s parameter type.
    def configure(self, binder: RoutesBinder) -> None:  # type: ignore[override]
        raise NotImplementedError


class AutoRoutesModule(RoutesModule):
    configured_routes: dict[Any, Any]

    def configure(self, binder: RoutesBinder) -> None:  # type: ignore[override]
        for route, controller in self.configured_routes.items():
            if isinstance(controller, MethodType):
                binder.connect(
                    route, controller=controller.__self__, action=controller.__name__
                )
            else:
                binder.connect(route, controller=controller)


class Application:
    def __init__(self, injector: InjectorI) -> None:
        self._injector = injector

    def __call__(
        self, environ: dict[str, Any], start_response: Callable[..., Any]
    ) -> Any:
        request = Request(environ)

        binder = self._injector.get_instance(RoutesBinder)

        route = binder.match(environ["PATH_INFO"], environ)
        if not route:
            return HTTPNotFound("no matching route")(environ, start_response)

        controller = route.pop("controller")
        controller = binder.controller_map.get(controller)

        if inspect.isclass(controller):
            action = route.pop("action", "index")
            controller = self.controller_from_class(controller, action)

        elif not callable(controller):
            return HTTPNotFound()(environ, start_response)

        if not controller:
            return HTTPNotFound()(environ, start_response)

        response: Any = controller(request, **route)
        return response(environ, start_response)

    def controller_from_class(self, controller: Any, action: Any) -> Any:
        controller = self._injector.get_instance(controller)
        return getattr(controller, action, None)
