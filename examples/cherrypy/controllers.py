import cherrypy

from examples.shared.interfaces import TemplateLoader
from examples.shared.providers import RequestDataProvider, UserProvider
from snakeguice import inject


class HelloWorld:
    @inject  # this is optional, but helps as "documentation"
    def __init__(
        self,
        user_provider: UserProvider,
        request_data_provider: RequestDataProvider,
        loader: TemplateLoader,
    ) -> None:
        self._user_provider = user_provider
        self._request_data_provider = request_data_provider
        self._loader = loader

    @cherrypy.expose
    def index(self) -> str:
        user0 = self._user_provider.get()
        user1 = self._user_provider.get()
        request_data0 = self._request_data_provider.get()
        request_data1 = self._request_data_provider.get()

        template = self._loader.load("scopes")
        return template.render(
            user0=user0,
            user1=user1,
            request_data0=request_data0,
            request_data1=request_data1,
        )
