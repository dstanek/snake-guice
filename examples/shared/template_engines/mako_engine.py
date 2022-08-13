from pathlib import Path

from mako.lookup import TemplateLookup

from examples.shared.interfaces import Template


class MakoTemplateLoader:
    def __init__(self) -> None:
        template_path = Path(__file__) / "../../../templates"
        self._lookup = TemplateLookup(directories=[template_path])

    def load(self, name) -> Template:
        return self._lookup.get_template(f"{name}.mako")
