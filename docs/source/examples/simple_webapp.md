# WebApp Example

HOWTO create a really simple web application using snake-guice

**Experimental** features not available in the public release. The API is highly volitile.

**Warning** this document is a brain dump and not necessarily organized properly.

**Warning** this document assumes that you are using a UNIX variant and Python 2.5 or above - this will work for other platforms and/or older versions of Python, but the instructions would vary a little.

## Basic Steps

You must decide where you want your web application. For this tutorial I'll assume you'll be using `$HOME/src/mywebapp`.

```bash
$ cd $HOME
$ mkdir src
$ cd src
```

I'll be using [[http:// virtualenv]] to create an isolated environment for our webapp. We first need to download it. I prefer to get it directly from its Subversion trunk.

```bash
$ wget http://svn.colorstudy.com/virtualenv/trunk/virtualenv.py
```

New lets use virtualenv to create our environment and activate the environment.

```bash
$ python virtualenv.py mywebsite
$ cd mywebsite
$ . bin/activate
```

I really like using [[WebOb](http://pythonpaste.org/webob/)] and [[http:// Routes]] so I'm going to install them now along with snake-guice.

```bash
$ easy_install webob routes snake-guice
```

The actual source files for the webapp will be stord in a src directory. So we'll create that now.
```bash
$ mkdir src
$ cd src
```

We now need to create the controller class that will actually handle to request. Create a file named `controllers.py` and paste in the following code:

```python
from webob import Response


class EntryController:

    def index(self, request):
        return Response('This is your default action. '
                'You may show a list of entries here.')

    def show(self, request, id):
        return Response('You are looking at entry #%s.' % id)

    def new(self, request):
        return Response('In a more fully featured example you would be '
                        'adding a new record to the database.')

    def update(self, request, id):
        return Response('In a more fully featured example you would be '
                        'updating record #%s in the database.' % id)
```

Lets wire up the `EntryController` using snake-guice. Create a file named `app.py` and paste in the following code:
```python
from wsgiref.simple_server import make_server

from controllers import EntryController
from snakeguice import Injector
from snakeguice.extras.modules.snakeroutes import (
        RoutesBinder, RoutesModule, Application)


class Module(RoutesModule):

    def configure_mapper(self, binder):
        binder.connect('/entries', controller=EntryController, action='index')
        binder.connect('/entries/new', controller=EntryController, action='new')
        binder.connect('/entry/:id/:action', controller=EntryController)


injector = Injector(Module())
app = Application(injector)

httpd = make_server('', 8000, app)
print "Serving on port 8000..."
httpd.serve_forever()
```

Trying running it now:
```bash
$ python app.py
```

You now have a web server listening on port 8000. Trying hitting one of the following URLs in you web browser:
  * http://localhost:8000/entries
  * http://localhost:8000/entries/new
  * http://localhost:8000/entry/123/show
  * http://localhost:8000/entry/123/update

## Other Notes
There is some support for virtual hosting using the annotation property of your binder. This is still a bit complicated so I'll have to document it later. The general idea is that you would be able to serve multiple sites, each with a separate mapper, from within the same process.
