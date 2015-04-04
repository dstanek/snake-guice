**Experimental** features not available in the public release. The API is highly volitile.

**Warning** this document is a brain dump and not necessarily organized properly.

# Introduction #

Often objects will need a bit of configuration data injected when they are created. Consider a database connection needing credentials or a logger needing a filename and log level. You want to make this as easy as possible for the operations folks that will deploy your application. Even if you play that role too. Luckily snake-guice provides facilities to make this very easy.

The example we'll walk through is a simple Logger class. No real implementation will be shown. Just enough to explain how to configure the instances.

# Getting started with simple injection #

Assuming the default configuration format, which will be explained later, your class definition would look like:
```
from snakeguice import inject, Injected, Config

class MyLogger(object):

    @inject(filename=Config('app.cfg:logger:filename'),
            loglevel=Config('app.cfg:logger:loglevel'))
    def __init__(self, filename,loglevel):
        pass
```

The injector is smart enough to know that needs to find filename and loglevel in a configration file. The string passed to Config is a fully qualified path to the config entry.

At this point the injector doesn't know where it can file app.cfg. We can do that by creating a new module:
```
from snakeguice.modules import ConfigModule

class MyConfigModule(ConfigModule):

    paths = ['/path/to/config/dir']
```

To hook it all up just pass an instance of MyConfigModule to the injector.

# Configuration format #
The default configuration implementation is Python's [ConfigParser](http://docs.python.org/library/configparser.html).

The fully qualified path to the config entry is really just a ':' delimited string. It must contain two parts: a filename and an option. It can also contain any number of sections. In no section in specified then 'default' is assumed.

Examples:
  1. 'app.cfg:entry' - file: app.cfg, section=default, entry=entry
  1. 'app.cfg:section:entry' - file: app.cfg, section=section, entry=entry
  1. 'app.cfg:section:sub:entry' - file: app.cfg, section=setion, subsection=sub, entry=entry

# Using a different config format #

Not everyone can or wants to use the ConfigParser format. To use your own custom implementation you need to specify it in your module.

```
from snakeguice.modules import ConfigModule
from snakeguice.interfaces import Config

from myapp import MyConfigAdapter

class MyConfigModule(ConfigModule):

    paths = ['/path/to/config/dir']

    def configure(self, binder):
        binder.bind(Config, to=MyConfigAdapter)
```

The instance of MyConfigAdapter is injected so it also has it's dependencies resolved. The ConfigAdapter interface is really simple. It just needs a lookup method that takes a (LDAP, ConfigObj, etc.) The format of the string is dependent on the ConfigAdapter implementation used.

```
class MyConfigAdapter(object):

    def lookup(self, config_entry):
        pass
```

It is also possible to use more than one configuration file format within an application. For this you just bind using annotations. For example:
```
from snakeguice import inject, Injected, Config

class MyLogger(object):

    @inject(filename=Config('app.cfg:logger:filename'),
            loglevel=Config('app.cfg:logger:loglevel'))
    def __init__(self, filename,loglevel):
        pass

class ThirdPartyStuff(object):

    @inject(port=Config('stupid.java.properties.file.entry', annotation='custom')
    def __init__(self, port):
        pass
```

In this case I have a class that needs to get it's configuration from a properties files. The MyLogger instances still use the default implementation of ConfigAdapter. To tell the injector about the custom ConfigAdapter you simply:
```
from snakeguice.modules import ConfigModule
from snakeguice.interfaces import Config

from myapp import CustomConfigAdapter

class MyConfigModule(ConfigModule):

    paths = ['/path/to/config/dir']

    def configure(self, binder):
        binder.bind(Config, to=CustomConfigAdapter, annotated_with='custom')
```

# Configuration objects #

Sometimes a subsystem will need to have a large number of configuration options. This can make the initializer very ugly. To get around this in the components I write I use a configuration class that can be passed into the API. Then I create a custom ConfigAdapter to create the config object.

```
class MyConfigAdapter(object):

    def lookup(self, config_entry):
        """Use the filename passed in to load a config object."""
        return MySuperSpecialConfig()

class MyAPI(object):

    @inject(config=Config('app.cfg'))
    def __init__(self, config):
        pass
```

# Dynamic configuration files #

TODO: explain using providers to inject dynamic config values

TODO: explain injecting descriptors