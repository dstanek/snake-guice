from examples.wsgiapp.controllers import HomeController
from snakeguice.extras.snakeweb import RoutesBinder, RoutesModule


class URLMapperModule(RoutesModule):
    # RoutesModule.run_configure() deliberately routes configure() through
    # RoutesBinder instead of Binder - see docs/source/extending.md.
    def configure(self, routes_binder: RoutesBinder) -> None:  # type: ignore[override]
        routes_binder.connect(
            "/form",
            controller=HomeController,
            action="form",
            conditions=dict(method="POST"),
        )
        routes_binder.connect("/", controller=HomeController, action="index")
