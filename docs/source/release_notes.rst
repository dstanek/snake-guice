Release Notes
=============

1.0.0a1 (alpha)
----------------

This is the first alpha release on the road to a stable 1.0. It requires
Python 3.10 or later.

**Highlights**

- Annotations can now be any object. Previously instances of ``Annotation``
  could only hold strings — any other value passed to ``__init__`` was
  silently converted to a string.
- ``@inject`` requires standard type annotations on all non-``self``
  parameters. The decorator no longer accepts arguments.
- Deferred binding errors: ``Binder.bind()`` never raises directly; all
  problems are collected and reported together as a single ``CreationError``
  when the injector is created.
- ``PrivateModule`` for isolated child injectors (robot-legs pattern).
- ``ListBinder`` and ``DictBinder`` multi-bindings.
- ``@assisted_inject`` for factory-style partial injection.
