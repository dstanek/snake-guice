from wsgiref.simple_server import make_server

from examples.shared.modules.mako_module import MakoTemplateModule
from examples.wsgiapp.modules import URLMapperModule
from snakeguice import create_injector
from snakeguice.extras.snakeweb import Application


def main() -> None:
    # URLMapperModule.configure() takes a RoutesBinder, so it is not a Module.
    injector = create_injector(
        [URLMapperModule(), MakoTemplateModule()]  # type: ignore[list-item]
    )
    app = Application(injector)

    httpd = make_server("", 8080, app)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
