from typing import Any


class Annotation:
    """Base class for all annotations."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def __hash__(self) -> int:
        return hash((self.__class__, self._value))

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other: object) -> bool:
        return not self == other


UNANNOTATED = Annotation(None)

# Bindings are most commonly disambiguated with a plain string (e.g.
# `annotated_with="left"`), but an `Annotation` subclass instance (e.g.
# `config.Config(...)`, or `UNANNOTATED` itself) works too.
AnnotationLike = Annotation | str
