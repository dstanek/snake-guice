# Guice Basics

## What is Dependency Injection

The Dependency Injection (DI) is an essential pattern when building large systems. It forces classes to be more modular and reusable by making them depend on an interface instead of a concrete class. Simply put classes favor instances passed into the init instead of creating new instances.

snake-guice is a Python framework, based of the popular [Google Guice](https://github.com/google/guice) framework, makes building applications using DI a breeze.

## Basic Concepts

interface
: a class representing the interface to an object. snake-guice uses the term interface in a much looser way than traditional OOP. The interface and implementation classes don't have to be related in any way or even have the same methods. It's simply a way of identifying what type of implementation is needed.

implementation
: a concrete class. snake-guice will be creating an instance of this class.

injector
: builds object graphs. The entry point of your application will create an Injector instance and use it to bootstrap the application.

binding
: a mapping of interface to implementation within the current application. Different applications can change this mapping.

binder
: the object containing a collection of bindings. snake-guice uses the binder to find bindings whenever it needs to create an object. This is also what you will use to notify snake-guice about your bindings.

module:: a

scope::

provider::

annotation::

dependency::

### Injectors

### Modules and Binders

Note: please excuse our mess - the docs are not pretty and may be inconsistent while we're hacking away at them

### Simple Example
Dependencies must be declared in order for SG to create your object.

```python
from snakeguice import inject


class IEngine:
    """This will be used an the interface when creating a binding."""


class SmallBlockEngine:
    """Implementation of a small block engine."""


class Car:
    """An implementation of a car."""

    @inject
    def __init__(self, engine: IEngine):
        self.engine = engine
```

There are a couple of odd things here. For one developers with a background in Java may be wondering why there is no relationship between IEngine and SmallBlockEngine. To retain the full flexibility we get with duck-typing no inheritence heirarchy is enforced. The interface is just a clue to the developer and SG to let us know what we should expect.

The @inject annotion feels a little unnatural. This will pass as it's value surfaces. The @inject decoration adds some meta data to your class. It doesn't effect the method's runtime in anyway. It really does two things: declared types and shows snake-guice what it should call to create an instance. (You can use @inject on methods as well - more on that later.)

A module is used to associate the correct implementation to the interface.

```python
from snakeguice.interfaces import Binder

class AutoModule:

    def configure(self, binder: Binder):
        binder.bind(IEngine, to=SmallBlockEngine)
```

Your module's configure method will be called by the framework. Using the binder's DSL you are able to wire up your object graph.

Getting the object graph out of snake-guice:

```python
from snakeguice import Injector


def main(args):
    injector = Injector(AutoModule())
    car = injector.get_instance(Car)

    assert isinstance(car, Car)
    assert isinstance(car.engine, SmallBlockEngine)
```

Um what? How did snake-guice know to create a Car when there was no explicit binding? Well, snake-guice will try to construct the class passed into get\_instance when no binding is found. As you can see when snake-guice constructs the Car it passes in the correct IEngine implementation.

### Multiple Bindings Using Annotations

In the previous example we bound SmallBlockEngine to IEngine when constructing our car. What happens when we need to inject multiple doors into our car? We definitely need both a left and a right door. Consider this code::

```python
class Car:
    """An implementation of a car."""

    @inject(engine=IEngine, left_door=IDoor, right_door=IDoor)
    @annotate(left_door="left", right_door="right")
    def __init__(self, engine, left_door, right_door):
        self.engine = engine
```

We needed to tell snake-guice how to differentiate the instances of door. We do this by annotating the method.

The module for this car would look like:

```python
class AutoModule(object):

    def configure(self, binder):
        binder.bind(IEngine, to=SmallBlockEngine)
        binder.bind(IDoor, annotated_with='left', to=LeftDoor)
        binder.bind(IDoor, annotated_with='right', to=RightDoor)
```

The combination of an interface and an annotation make a unique key in the binder. Each key can only have a single implementation bound to it.