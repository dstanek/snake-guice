"""A really simple 'Hello, World' webapp to test snakeweb."""

from wsgiref.simple_server import make_server

from snakeguice import create_injector
from snakeguice.extras import snakeweb
from snakeguice.modules import Module


class HWController:
    def index(self, request):
        return snakeweb.Response(
            f"Hello, World!<br>I see you are from: {request.remote_addr}"
        )

    def hello_name(self, request, name):
        return snakeweb.Response(f"Hello, {name}!")


class HWModule(Module):
    def configure(self, binder):
        self.install(binder, HWRoutes())


class HWRoutes(snakeweb.RoutesModule):
    def configure(self, routes_binder):
        routes_binder.connect("/", controller=HWController)
        routes_binder.connect("/:name", controller=HWController, action="hello_name")


if __name__ == "__main__":
    injector = create_injector(HWModule())
    httpd = make_server("", 8080, snakeweb.Application(injector))
    httpd.serve_forever()
