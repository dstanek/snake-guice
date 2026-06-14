# Injecting Configuration

Objects often need a bit of configuration data when they're created - a
database connection needs credentials, a logger needs a filename and log
level. snake-guice can load values from an `.ini`-style file and bind them so
they can be injected like anything else.

## Loading a Config File

`ConfigParserLoader` reads a file with Python's
[`ConfigParser`](https://docs.python.org/3/library/configparser.html) and
binds every `section`/`option` pair it finds. Call it from a module's
`configure()`:

```python
from snakeguice import config
from snakeguice.interfaces import Binder


class ConfigModule:
    def configure(self, binder: Binder) -> None:
        config.ConfigParserLoader("app.ini").bind_configuration(binder)
```

Given an `app.ini` like:

```ini
[db]
dsn = sqlite:///app.db
```

every value becomes available under a `Config` annotation keyed by
`"<filename>:<section>:<option>"` - here, `Config("app.ini:db:dsn")`. Note that
the filename used in the key is just the basename (`os.path.basename`), even
if you pass a longer path to `ConfigParserLoader`.

## Reading a Value

A `Config(...)` instance can be used directly as a type annotation. Since
`Config` is an `Annotation`, two `Config("app.ini:db:dsn")` instances compare
equal, so this lines up with the binding created above:

```python
from snakeguice import inject


class Database:
    @inject
    def __init__(self, dsn: config.Config("app.ini:db:dsn")) -> None:
        self.dsn = dsn
```

You can also fetch a value directly from the injector without an injectable
class:

```python
injector = create_injector([ConfigModule()])
dsn = injector.get_instance(config.Config("app.ini:db:dsn"))
```

All values come back as `str`, exactly as `ConfigParser` returns them -
snake-guice does no type conversion, so convert (`int(...)`, `Path(...)`, etc.)
yourself where it matters.

## Multiple Config Files

`ConfigParserLoader` can be called more than once, for as many files as you
need - each binds its values under its own `<filename>:...` keys, so there's
no collision between files:

```python
class ConfigModule:
    def configure(self, binder: Binder) -> None:
        config.ConfigParserLoader("app.ini").bind_configuration(binder)
        config.ConfigParserLoader("logging.ini").bind_configuration(binder)
```
