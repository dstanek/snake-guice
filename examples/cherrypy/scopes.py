import cherrypy
from snakeguice.providers import InstanceProvider


class CherrypyRequestScope:

    def scope(self, key, provider):
        class SessionProvider:
            def get(self):
                if not hasattr(cherrypy.request, '__guicy__'):
                    cherrypy.request.__guicy__ = {}

                value = cherrypy.request.__guicy__.get(key)
                if not value:
                    value = cherrypy.request.__guicy__[key] = provider.get()
                return value
        return InstanceProvider(SessionProvider())


class CherrypySessionScope:

    def scope(self, key, provider):
        class SessionProvider:
            def get(self):
                value = cherrypy.session.get(key)
                if not value:
                    value = cherrypy.session[key] = provider.get()
                return value
        return InstanceProvider(SessionProvider())


CHERRYPY_REQUEST_SCOPE = CherrypyRequestScope()
CHERRYPY_SESSION_SCOPE = CherrypySessionScope()
