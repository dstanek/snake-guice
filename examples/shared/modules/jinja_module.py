from examples.shared.interfaces import TemplateLoader
from examples.shared.template_engines.jinja_engine import JinjaTemplateLoader
from snakeguice.interfaces import Binder


class JinjaTemplateModule:
    def configure(self, binder: Binder):
        binder.bind(TemplateLoader, to=JinjaTemplateLoader)
