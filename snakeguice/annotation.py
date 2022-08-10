class Annotation:
    """Base class for all annotations."""

    def __init__(self, value) -> None:
        self._value = value

    def __hash__(self) -> int:
        return hash((self.__class__, self._value))

    def __eq__(self, other: object) -> bool:
        return self.__hash__() == other.__hash__()

    def __ne__(self, other: object) -> bool:
        return not self == other
