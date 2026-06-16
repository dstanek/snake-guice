from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, eq=False)
class Annotation:
    """Base class for all annotations."""

    value: Any

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Annotation) or type(self) is not type(other):
            return NotImplemented
        return bool(self.value == other.value)


UNANNOTATED = Annotation(None)

# Bindings are most commonly disambiguated with a plain string (e.g.
# `annotated_with="left"`), but an `Annotation` subclass instance (e.g.
# `config.Config(...)`, or `UNANNOTATED` itself) works too.
AnnotationLike = Annotation | str
