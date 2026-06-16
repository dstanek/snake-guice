from typing import TypeVar

import cherrypy

from snakeguice.interfaces import Key, Provider

T = TypeVar("T")


class CherrypyRequestScope:
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        class RequestProvider:
            def get(self) -> T:
                if not hasattr(cherrypy.request, "__guicy__"):
                    cherrypy.request.__guicy__ = {}

                value = cherrypy.request.__guicy__.get(key)
                if not value:
                    value = cherrypy.request.__guicy__[key] = provider.get()
                return value

        return RequestProvider()


class CherrypySessionScope:
    def scope(self, key: Key, provider: Provider[T]) -> Provider[T]:
        class SessionProvider:
            def get(self) -> T:
                value = cherrypy.session.get(key)
                if not value:
                    value = cherrypy.session[key] = provider.get()
                return value

        return SessionProvider()


CHERRYPY_REQUEST_SCOPE = CherrypyRequestScope()
CHERRYPY_SESSION_SCOPE = CherrypySessionScope()
