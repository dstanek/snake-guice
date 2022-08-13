from examples.shared.interfaces import TemplateLoader
from examples.shared.template_engines.mako_engine import MakoTemplateLoader
from snakeguice.interfaces import Binder


class MakoTemplateModule:
    def configure(self, binder: Binder):
        binder.bind(TemplateLoader, to=MakoTemplateLoader)
