# snake-guice's documentation

snake-guice is a simple, lightweight Python dependency injection framework based on google-guice. The Guice way of doing things is quite a bit different than the current breed of XML IoC containers.

We are working toward an official 1.0 release! The current version is `1.0.0a1` (alpha). The package requires Python 3.10 or later.

This documentation is a work in progress. For general information on the Guice concepts you may want to take a look at the [google-guice](https://github.com/google/guice/wiki) project documentation. Just mentally translate the Java examples to Python. Most of the examples are extremely simple anyway.

```{toctree}
:maxdepth: 1
:caption: "Contents:"

release_notes
guicebasics
userguide
extending
concurrency
injecting_configuration
using_providers
multibinder
assisted_injection
private_modules
parameter_interceptors
what_to_inject
patterns
examples/index
future
```
