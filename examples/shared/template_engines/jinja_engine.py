from jinja2 import Environment, PackageLoader, select_autoescape

from examples.shared.interfaces import Template


class JinjaTemplateLoader:
    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("examples"), autoescape=select_autoescape()
        )

        def object_id(obj: object) -> str:
            return str(id(obj))

        self._env.filters["id"] = object_id

    def load(self, name: str) -> Template:
        return self._env.get_template(f"{name}.html.j2")
