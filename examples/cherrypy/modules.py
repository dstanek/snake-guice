from examples.cherrypy.scopes import CHERRYPY_REQUEST_SCOPE, CHERRYPY_SESSION_SCOPE
from examples.shared.providers import RequestDataProvider, UserProvider
from snakeguice.interfaces import Binder


class Module:
    def configure(self, binder: Binder) -> None:
        binder.bind(UserProvider, to=UserProvider, in_scope=CHERRYPY_SESSION_SCOPE)
        binder.bind(
            RequestDataProvider, to=RequestDataProvider, in_scope=CHERRYPY_REQUEST_SCOPE
        )
