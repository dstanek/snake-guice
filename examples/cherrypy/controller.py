from snakeguice import inject

from providers import UserProvider, RequestDataProvider


class HelloWorld:

    @inject(user_provider=UserProvider,
            request_data_provider=RequestDataProvider)
    def __init__(self, user_provider, request_data_provider) -> None:
        self._user_provider = user_provider
        self._request_data_provider = request_data_provider

    def index(self):
        output = ["Hello world!<br><br>"]

        user = self._user_provider.get()
        output.append("Session scoped: %s id=%s<br>"
                % (user.__class__.__name__, id(user)))

        user = self._user_provider.get()
        output.append("Session scoped: %s id=%s<br>"
                % (user.__class__.__name__, id(user)))

        request_data = self._request_data_provider.get()
        output.append("Request scoped: %s id=%s<br>"
                % (request_data.__class__.__name__, id(request_data)))

        request_data = self._request_data_provider.get()
        output.append("Request scoped: %s id=%s<br>"
                % (request_data.__class__.__name__, id(request_data)))

        return "".join(output)
    index.exposed = True
