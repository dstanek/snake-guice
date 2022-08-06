# Using Providers with snake-guice

## Introduction 

This shows a simple example where you might want to use a Provider to grab an instance to a class at runtime.  The provider itself can be injected by snake-guice.  When a method requires use of an instance from the provider, it can automatically be given to it as an argument.


## Non-Example

This example is taken from test\_decorators.

SomeClass has an injected provider property, and a method that expects the provided instance as an attribute to its method.  We want a specific instance of Something to be provided to the get\_some\_status method in SomeClass.

```python
    from snakeguice import injector
    from snakeguice.providers import InstanceProvider

    class Something:
        def __init__(self, status):
            self.status = status

    class SomeClass:
        some_provider = inject(InstanceProvider)

        @provide(p=some_provider)
        def get_some_status(self, p):
            assert type(p) == Something
            assert p.status == 'something:provided'
            return p.status

    class Modules:
        def configure(self, binder):
            provided = InstanceProvider(Something('something:provided'))
            binder.bind(InstanceProvider, to_instance=provided)

    inj = injector.Injector(Modules())
    some_class = inj.get_instance(SomeClass)
    status = some_class.get_some_status()

    assert isinstance(some_class, SomeClass)
    assert status == 'something:provided'
```

## Session Provider Example

There are times that you might want to use a Provider for a session service.  For example, your web app might use a Controller that hangs around for the life of the application.  Action methods within the controller probably need to dispatch based on request/user data.  The provider would do its magic look up the session relevant to the current context and return it for a class to use.

The session provider itself might do something like this, however ugly:

```python
class SessionProvider:
   def get(self):
       pass

class MySessionProvider:
   def __init__(self, _globals):
      self._globals = _globals

   def get(self):
      app_context = self._globals['app.current_context']
      session_store = app_context['session']
      return session
```

The nice thing about the provider pattern is that the lookup into globals or whatever other trickery your app server needs is encapsulated in one place.

Theoretically, multiple applications on a server could be using slightly different variations of the session provider.  Your controller would contain an instance of a SessionProvider, which conforms to the `ProviderInterface`.  The DI framework (snake-guice) handles giving the controller the proper `SessionProvider`.

Your controller then looks like this:

```python
class Controller:
   session_provider = inject(SessionProvider)

   @provide(session=session_provider)
   def GET(self, session=Provided):
       if session.is_signed_in:
           return Template('index.htm')
       else:
           return Template('index_guest.htm')
```

The GET method of the controller now has the contextually relevant session provided to it, upon which it can make decisions.

To wire everything up, you'll need to coordinate building the Injector, wiring the SessionProvider, and spinning up the `Controller` in the app server.
