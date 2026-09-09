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


class AssistError(SnakeGuiceError):
    """Raised when an issue with assisted injection is found."""


class MultiBindingError(SnakeGuiceError):
    """Raised when a issue with multi-binding is found."""
