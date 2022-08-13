from examples.wsgiapp.controllers import HomeController
from snakeguice.extras.snakeweb import RoutesBinder, RoutesModule


class URLMapperModule(RoutesModule):
    def configure(self, routes_binder: RoutesBinder) -> None:
        routes_binder.connect(
            "/form",
            controller=HomeController,
            action="form",
            conditions=dict(method="POST"),
        )
        routes_binder.connect("/", controller=HomeController, action="index")
