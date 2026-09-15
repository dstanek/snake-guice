Release Notes
=============

Unreleased
----------

- Resolution is much faster: parameter extraction is memoised per function
  (~30x on a small dependency graph), method-injection order is computed once
  per class, and ``bind()`` no longer re-validates a provider class per call.
- ``@inject`` methods now run in declaration order within each class (they
  ran in reverse). Base classes still go first, and an overridden method
  runs once, at the overriding class's position.
- A subclass of ``Injector`` asked for ``Injector`` (or any base) now returns
  itself instead of silently building a new, empty injector.
- Scanning a module for ``@provides`` no longer evaluates its ``@property``
  attributes.
- An abstract class or ``Protocol`` interface now type-checks with every
  ``bind()`` form, not just ``to=``. The ``to_provider=``/``to_instance=``
  overloads never actually enforced that the provider/instance matched
  ``_class`` (both are duck-typed against it at runtime instead - see
  ``test_to_instance_accepts_a_duck_typed_stand_in``), so widening them to
  ``type[Any]`` to accept abstract interfaces doesn't give up any checking
  that existed before.
- A configuration error from ``PrivateModule.expose()`` (an exposed key with
  no matching private binding) now points at the ``expose()`` call itself,
  not somewhere inside snakeguice. ``Binder.add_error()`` also no longer
  builds a full ``inspect.stack()`` (every frame, with source context) for a
  single-frame lookup - roughly 115x faster per call in a microbenchmark
  (0.27ms vs. 0.002ms).

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
  ``bind()`` overloads and the rest of the binder DSL.
