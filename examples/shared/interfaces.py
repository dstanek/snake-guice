from typing import Any, Protocol


class Template(Protocol):
    """A template is an object that can be rendered."""

    def render(self, **kwargs: Any) -> str:
        ...


class TemplateLoader(Protocol):
    """Loads templates."""

    def load(self, name: str) -> Template:
        ...
