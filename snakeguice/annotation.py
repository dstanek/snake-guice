from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True, eq=False)
class Annotation:
    """Base class for all annotations."""

    value: Any

    def __hash__(self) -> int:
        return hash((self.__class__, self.value))

    def __eq__(self, other: object) -> bool:
        return hash(self) == hash(other)

    def __ne__(self, other: object) -> bool:
        return not self == other


UNANNOTATED = Annotation(None)

# Bindings are most commonly disambiguated with a plain string (e.g.
# `annotated_with="left"`), but an `Annotation` subclass instance (e.g.
# `config.Config(...)`, or `UNANNOTATED` itself) works too.
AnnotationLike = Annotation | str
