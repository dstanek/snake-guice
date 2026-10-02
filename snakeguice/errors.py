"""Errors used by snake-guice"""


class SnakeGuiceError(Exception):
    """Base for all of our errors."""


class BindingError(SnakeGuiceError):
    """Raised when an issue in the binding rules is found."""


class CreationError(BindingError):
    """Raised when configuration errors are found while creating an injector."""


class CircularDependencyError(BindingError):
    """Raised at resolution time (get_instance()) when a binding depends on
    itself, directly or transitively. Unlike CreationError, this can surface
    long after create_injector() has already succeeded, for a single key
    rather than a batch of configuration problems."""


class MissingBindingError(BindingError):
    """Raised at resolution time (get_instance()) when an annotated key has
    no matching binding. Like CircularDependencyError, this is a single-key
    resolution-time failure rather than a batch of configuration problems
    caught up front -- an annotation names one specific binding among
    several, so falling back to implicit construction would silently return
    the wrong object instead of the requested one."""


class ImplicitConstructionError(BindingError):
    """Raised at resolution time (create_object()/inject_members()) when an
    unannotated, unbound parameter's type is a builtin or standard-library
    type -- or isn't a type at all, e.g. a `Foo | None` union, which used to
    reach this same fallback and fail with a confusing `TypeError: ... not
    callable`. A zero-argument str()/int()/list()/pathlib.Path() is a
    vacuous *value*, never the specific one a forgotten binding should have
    produced, unlike an application's own concrete class, where a zero-arg
    constructor still produces a working object. Third-party and in-app
    classes are left to implicitly construct as before -- they almost
    always need real configuration and get an explicit binding anyway, so
    being wrong there costs a loud error rather than a silent one."""


class AssistError(SnakeGuiceError):
    """Raised when an issue with assisted injection is found."""


class MultiBindingError(SnakeGuiceError):
    """Raised when a issue with multi-binding is found."""
