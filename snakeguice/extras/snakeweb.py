#!/usr/bin/env python

import inspect
from types import MethodType
from typing import Any, Callable, Dict

import routes
from webob import Request, Response  # noqa: F401
from webob.exc import HTTPNotFound

from snakeguice.annotation import UNANNOTATED, Annotation
from snakeguice.interfaces import Binder as BinderI
from snakeguice.interfaces import Injector as InjectorI
from snakeguice.modules import Module


def is_unbound_method(func: Any) -> bool:
    return inspect.ismethod(func) and getattr(func, "im_self", None) is None


class RoutesBinder:
    def __init__(self, mapper: Any, annotation: Annotation) -> None:
        self.mapper = mapper
        self._annotation = annotation
        self.controller_map: Dict[Any, Any] = {}

    def connect(self, *args: Any, **kwargs: Any) -> None:
        controller = kwargs.get("controller")

        if controller is None:
            raise TypeError("no controller specified")

        key = str((id(controller), repr(controller)))
        self.controller_map[key] = controller
        kwargs["controller"] = key
        self.mapper.connect(*args, **kwargs)

    def match(self, url: str, environ: Dict[str, Any]) -> Any:
        # TODO: i have a patch that makes this suck less - i need to submit it
        old_environ, self.mapper.environ = self.mapper.environ, environ
        try:
            return self.mapper.match(url)
        finally:
            self.mapper.environ = old_environ


class RoutesModule(Module):

    annotation = UNANNOTATED

    def run_configure(self, binder: BinderI) -> None:
        self._mapper = routes.Mapper()
        self.routes_binder = RoutesBinder(self._mapper, self.annotation)
        binder.bind(
            RoutesBinder, to_instance=self.routes_binder, annotated_with=self.annotation
        )

        self.configure(self.routes_binder)
        self._mapper.create_regs([])

    def configure(self, routes_binder: RoutesBinder) -> None:
        raise NotImplementedError


class AutoRoutesModule(RoutesModule):
    configured_routes: Dict[Any, Any]

    def configure(self, routes_binder: RoutesBinder) -> None:
        for route, controller in self.configured_routes.items():
            if isinstance(controller, MethodType):
                routes_binder.connect(
                    route, controller=controller.__self__, action=controller.__name__
                )
            else:
                routes_binder.connect(route, controller=controller)


class Application:
    def __init__(self, injector: InjectorI) -> None:
        self._injector = injector

    def __call__(
        self, environ: Dict[str, Any], start_response: Callable[..., Any]
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

        elif is_unbound_method(controller):
            controller = self.controller_from_method(controller)

        elif not callable(controller):
            return HTTPNotFound()(environ, start_response)

        if not controller:
            return HTTPNotFound()(environ, start_response)

        response = controller(request, **route)
        return response(environ, start_response)

    def controller_from_class(self, controller: Any, action: Any) -> Any:
        controller = self._injector.get_instance(controller)
        return getattr(controller, action, None)

    def controller_from_method(self, controller: Any) -> Any:
        return self.controller_from_class(controller.im_class, controller.__name__)
