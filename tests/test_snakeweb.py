from typing import Any
from unittest import TestCase
from unittest.mock import Mock, patch

import pytest

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
        assert self.module.configure.calls("()", snakeweb.RoutesBinder)

    def test_real_routes_mapper_was_created(self) -> None:
        assert self.mock_routes.Mapper.calls()


class TestRoutesModuleIsAbstract:
    def setup(self) -> None:
        self.module = snakeweb.RoutesModule()

    def test_configure_mapper_is_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            self.module.configure(Mock())


class BaseTestRoutesBinder:
    def setup(self) -> None:
        self.routes_mapper = Mock()
        self.annotation = Mock()
        self.binder = snakeweb.RoutesBinder(self.routes_mapper, self.annotation)


class TestRoutesBinderConnectWithInvalidControllers(BaseTestRoutesBinder):
    def test_an_exception_is_raised_is_no_controller_is_specified(self) -> None:
        with pytest.raises(TypeError):
            self.binder.connect("/post/3/view")


class TestWhenCallingRoutesBinder(BaseTestRoutesBinder):
    def setup(self) -> None:
        super(TestWhenCallingRoutesBinder, self).setup()
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

            def configure(self, routes_binder):
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
