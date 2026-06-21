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

`ConfigParserLoader` can be called more than once. By default the key prefix
is the file's basename, so two files with different names load without
collision:

```python
class ConfigModule:
    def configure(self, binder: Binder) -> None:
        config.ConfigParserLoader("app.ini").bind_configuration(binder)
        config.ConfigParserLoader("logging.ini").bind_configuration(binder)
```

Two loaders can share the same namespace (or the same basename) as long as
their `section`/`option` keys don't overlap — the values simply merge:

```python
class ConfigModule:
    def configure(self, binder: Binder) -> None:
        # base.ini has [server] host = ...
        # overrides.ini has [server] port = ...
        config.ConfigParserLoader("base.ini", namespace="app").bind_configuration(binder)
        config.ConfigParserLoader("overrides.ini", namespace="app").bind_configuration(binder)
```

If two files share the same basename *and* the same `section`/`option` key,
`create_injector()` raises `CreationError` with a message identifying the
conflicting key and suggesting `namespace=`. Pass distinct namespaces to keep
the values separate:

```python
class ConfigModule:
    def configure(self, binder: Binder) -> None:
        config.ConfigParserLoader(
            "config/primary/settings.ini", namespace="primary"
        ).bind_configuration(binder)
        config.ConfigParserLoader(
            "config/replica/settings.ini", namespace="replica"
        ).bind_configuration(binder)
```

Values are then available under `Config("primary:section:option")` and
`Config("replica:section:option")` respectively.
