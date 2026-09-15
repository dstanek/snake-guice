from typing import Any
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest
from webob import Request, Response

from snakeguice import create_injector
from snakeguice.extras import snakeweb


class TestRoutesModuleSetup(TestCase):
    def setUp(self) -> None:
        patcher = patch("snakeguice.extras.snakeweb.routes")
        self.mock_routes = patcher.start()
        self.addCleanup(patcher.stop)

        class MyRoutesModule(snakeweb.RoutesModule):
            configure = Mock()

        self.binder = Mock()
        self.module = MyRoutesModule()
        self.module.run_configure(binder=self.binder)

    def test_configure_is_called_with_a_mapper(self) -> None:
        self.module.configure.assert_called_once()
        (routes_binder,), _ = self.module.configure.call_args
        assert isinstance(routes_binder, snakeweb.RoutesBinder)

    def test_real_routes_mapper_was_created(self) -> None:
        self.mock_routes.Mapper.assert_called_once()


class TestRoutesModuleIsAbstract:
    def setup_method(self) -> None:
        self.module = snakeweb.RoutesModule()

    def test_configure_mapper_is_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            self.module.configure(Mock())


class BaseTestRoutesBinder:
    def setup_method(self) -> None:
        self.routes_mapper = Mock()
        self.binder = snakeweb.RoutesBinder(self.routes_mapper)


class TestRoutesBinderConnectWithInvalidControllers(BaseTestRoutesBinder):
    def test_an_exception_is_raised_is_no_controller_is_specified(self) -> None:
        with pytest.raises(TypeError):
            self.binder.connect("/post/3/view")


class TestWhenCallingRoutesBinder(BaseTestRoutesBinder):
    def setup_method(self) -> None:
        super(TestWhenCallingRoutesBinder, self).setup_method()
        self.controller = object
        self.args = (Mock(), Mock())
        self.kwargs = dict(a=Mock(), controller=object)
        self.binder.connect(*self.args, **self.kwargs)

        self.key = str((id(self.controller), repr(self.controller)))
        self.kwargs["controller"] = self.key

    def test_pass_through_to_real_mapper(self) -> None:
        assert self.routes_mapper.calls("connect", *self.args, **self.kwargs)

    def test_controller_should_be_added_to_the_map(self) -> None:
        assert self.binder.controller_map == {self.key: self.controller}


class TestWhenAutoConfiguringRoutes(TestCase):
    def setUp(self) -> None:
        mock_routes_binder = self.mock_routes_binder = Mock(spec=snakeweb.RoutesBinder)
        # patcher = patch("snakeguice.extras.snakeweb.RoutesBinder")
        # patcher.start()
        # self.addCleanup(patcher.stop)

        class MyController:
            def __call__(self) -> None:
                pass

            def bar(self, request: Any) -> None:
                pass

        self.controller = MyController()

        class MyModule(snakeweb.AutoRoutesModule):
            configured_routes = {
                "/": self.controller,
                "/foo": self.controller.bar,
            }

            def configure(self, routes_binder: snakeweb.RoutesBinder) -> None:  # type: ignore[override]
                # User don't have to override this. It's just a type-safe way
                # to inject a Mock.
                super().configure(mock_routes_binder)

        self.module = MyModule()
        self.module.run_configure(binder=Mock())

    def test_should_map_callables(self) -> None:
        self.mock_routes_binder.connect.assert_any_call("/", controller=self.controller)

    def test_should_map_methods(self) -> None:
        self.mock_routes_binder.connect.assert_any_call(
            "/foo", controller=self.controller, action="bar"
        )


class TestApplication:
    def setup_method(self) -> None:
        class GreeterController:
            def index(self, request: Request) -> Response:
                return Response("hello world")

        class GreeterModule(snakeweb.AutoRoutesModule):
            configured_routes = {"/": GreeterController}

        # AutoRoutesModule.configure() takes a RoutesBinder, not a Binder
        # (see examples/wsgiapp/app.py), so GreeterModule doesn't
        # structurally satisfy the Module protocol's configure(binder: Binder).
        injector = create_injector([GreeterModule()])  # type: ignore[list-item]
        self.app = snakeweb.Application(injector)

    def test_matched_route_returns_the_controllers_response(self) -> None:
        response = Request.blank("/").get_response(self.app)
        assert response.status_int == 200
        assert response.text == "hello world"

    def test_unmatched_route_returns_404(self) -> None:
        response = Request.blank("/nope").get_response(self.app)
        assert response.status_int == 404
