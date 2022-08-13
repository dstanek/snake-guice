import cherrypy

from examples.cherrypy.controllers import HelloWorld
from examples.cherrypy.modules import Module
from examples.shared.modules.jinja_module import JinjaTemplateModule
from snakeguice import Injector


def main() -> None:
    injector = Injector([Module(), JinjaTemplateModule()])
    controller = injector.get_instance(HelloWorld)
    cherrypy.config.update(
        {
            "tools.sessions.on": True,
            "tools.sessions.timeout": 1,
        }
    )
    cherrypy.quickstart(controller, "/")


if __name__ == "__main__":
    main()
