Release Notes
=============

Pre-3.0
-------

We are marching toward a 3.0. This release contains significant changes to
support Python 3.8+ and solidifies the API.

**Upgrade notes**

- snake-guice now depends on using standard type annotations. The ``@inject``
  decorator no longer accepts any arguments. A future version of the project
  may read type information from guice modules or type stubs.

**New features**

- Annotations can now be any object. Previously instances of ``Annotation``
  could only be strings — any other object passed to ``__init__`` was
  automatically converted to a string.
