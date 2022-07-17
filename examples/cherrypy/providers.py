
class User:
    """An object representing a user."""


class UserProvider:

    def get(self):
        return User()


class RequestData:
    """Some some data generated for each request."""


class RequestDataProvider:

    def get(self):
        return RequestData()
