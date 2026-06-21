``snake-guice`` is a simple, lightweight Python dependency injection framework
based on ``google-guice``. The Guice way of doing things is quite a bit different
than the current breed of XML IoC containers.

- **Repository**: https://github.com/dstanek/snake-guice
- **Documentation**: https://snake-guice.readthedocs.io/

Quick Start
-----------

Declare dependencies with ``@inject`` and type annotations, wire them up in a
module, then let the injector build your object graph:

.. code-block:: python

   from snakeguice import create_injector, inject
   from snakeguice.interfaces import Binder


   class IEngine:
       """Interface for an engine."""


   class SmallBlockEngine(IEngine):
       pass


   class Car:
       @inject
       def __init__(self, engine: IEngine) -> None:
           self.engine = engine


   class AutoModule:
       def configure(self, binder: Binder) -> None:
           binder.bind(IEngine, to=SmallBlockEngine)


   injector = create_injector([AutoModule()])
   car = injector.get_instance(Car)

   assert isinstance(car.engine, SmallBlockEngine)

Going Further
-------------

- `User Guide <https://snake-guice.readthedocs.io/en/latest/userguide.html>`_ — bindings, scopes, child injectors
- `Using Providers <https://snake-guice.readthedocs.io/en/latest/using_providers.html>`_ — per-call construction and lazy resolution
- `Multibinding <https://snake-guice.readthedocs.io/en/latest/multibinder.html>`_ — collecting multiple implementations of one interface
- `Private Modules <https://snake-guice.readthedocs.io/en/latest/private_modules.html>`_ — scoping bindings to a subsystem

Sharp Edges
-----------

- ``scopes.SINGLETON`` is process-global. For per-test or per-injector isolation,
  create your own ``scopes.Singleton()`` instance and pass it to ``in_scope=``.
- Method injection (``@inject`` on methods other than ``__init__``) only runs for
  implicitly constructed classes, not for classes bound with ``to=``.
