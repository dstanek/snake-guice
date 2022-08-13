import formencode
from webob import Request, Response

from examples.shared.interfaces import TemplateLoader
from examples.wsgiapp.forms import MyForm
from snakeguice import inject


class BaseController:
    @inject
    def __init__(self, loader: TemplateLoader) -> None:
        self._loader = loader


class HomeController(BaseController):
    def index(self, request: Request) -> Response:
        kwargs = dict(name="", email="", errors={})
        template = self._loader.load("index")
        return Response(template.render(**kwargs))

    def form(self, request: Request) -> Response:
        errors = {}
        try:
            formdata = MyForm().to_python(request.POST)
        except formencode.Invalid as e:
            errors = e.unpack_errors()
            formdata = request.POST

        if errors:
            template = self._loader.load("index")
        else:
            template = self._loader.load("thanks")

        return Response(template.render(**formdata, errors=errors))
