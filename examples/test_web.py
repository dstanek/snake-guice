#!/usr/bin/env python

"""
This very ficticious example shows a cheap implementation of a web
framework built entirely using snakejuice.
"""

###############################################################
# <loggers.py>
# Logging functionality
###############################################################


class Logger:
    pass


class FileLogger:
    pass


###############################################################
# </loggers.py>
###############################################################

###############################################################
# <session.py>
# Session in a stateful application.
###############################################################

from snakeguice import inject  # noqa: E402

# from loggers import Logger -- not needed in this example


class Session:
    pass


class WebSession:
    logger = inject(Logger)


###############################################################
# </session.py>
###############################################################

###############################################################
# <handlers.py>
# Defines handlers that are used for each request.
###############################################################

from snakeguice import inject  # noqa: E402

# from session import Session -- not needed in this example


class Handler:

    session = inject(Session)

    def handle(self, request) -> None:
        """got something!"""


class HTTPHandler(Handler):
    pass


class SMTPHandler(Handler):
    pass


###############################################################
# </handlers.py>
###############################################################

###############################################################
# <server.py>
# Basic serving functionality
###############################################################

from snakeguice import inject  # noqa: E402

# from handlers import Handler -- not needed in this example


class Server:
    pass


class WebServer(Server):

    handler = inject(Handler)

    def start(self):
        fake_requests = (1, 2, 3)
        for request in fake_requests:
            self.handler.handle(request)


###############################################################
# </server.py>
###############################################################

###############################################################
# <myappmodule.py>
# Defines the dependencies between classes that this application will use.
###############################################################

# from handlers import Handler, HTTPHandler -- not needed in this example


class MyAppModule:
    def configure(self, binder):
        binder.bind(Server).to(WebServer)
        binder.bind(Handler).to(HTTPHandler)
        binder.bind(Session).to(WebSession)
        binder.bind(Logger).to(FileLogger)


###############################################################
# </myappmodule.py>
###############################################################

###############################################################
# <start application.py>
# This would be the entry point of your application.
###############################################################

from snakeguice import Injector  # noqa: E402

# from myappmodule import MyAppModule -- not needed in this example
# from server import Server -- not needed in this example


class Application:
    """Hello. I am responsible for setting up all of the application's state.
    Not only will I setup the snakeguice injector, but I may also initialize
    dataconnections or other application-wide resources.
    """

    def __init__(self) -> None:
        injector = Injector(MyAppModule())
        # connect_to_db()
        # read_config_files()

        self.server = injector.get_instance(Server)
        self.server.start()


###############################################################
# </application.py>
###############################################################


# the actualy executed test
def test_run():
    app = Application()
    server = app.server

    # the application is done running, but lets verify the tree
    assert isinstance(server, WebServer)
    assert isinstance(server.handler, HTTPHandler)
    assert isinstance(server.handler.session, WebSession)
    assert isinstance(server.handler.session.logger, FileLogger)
