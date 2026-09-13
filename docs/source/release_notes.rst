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
- ``Injector`` is now safe to share between threads and concurrent ``asyncio``
  tasks. ``scopes.SINGLETON`` is now per-injector rather than process-global
  (a ``create_child()`` injector still shares a parent-defined singleton).
  Added ``scopes.THREAD_LOCAL`` for state that should be cached per thread
  instead. A ``PrivateModule`` instance can now safely configure more than
  one injector.
- ``interfaces.Binder`` is now a ``Protocol`` (previously an alias for
  ``Any``), so ``configure(binder)`` is type-checked against the real
  ``bind()`` overloads and the rest of the binder DSL. An abstract class or
  ``Protocol`` interface type-checks today when bound with ``to=``; binding
  one through ``to_provider=`` or ``to_instance=`` doesn't yet - that needs
  its own overload.
