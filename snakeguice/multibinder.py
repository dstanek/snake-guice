from snakeguice import providers
from snakeguice.annotation import Annotation
from snakeguice.binder import Key
from snakeguice.decorators import inject
from snakeguice.interfaces import Injector
from snakeguice.errors import MultiBindingError
import itertools

class _RealElement(object):
    """
    This helper class exists to help construct unique annotation names for MultiBinder generating bindings.
    """
    unique = itertools.count()
    def __init__(self, name, type):
        self._name = name
        self._type = type
        # Thanks to the global interpreter lock
        # this line is perfectly thread safe.
        self._uniqueId = self.unique.next()
        
    def __str__(self):
        return "<Element(setName=%s, type=%s, uniqueId=%s>" % (self._name, self._type, self._uniqueId)

    def __hash__(self):
        return (127 * (hash("setName") ^ hash(self._name)) \
                + 127 * (hash("uniqueId") ^ hash(self._uniqueId)) \
                + 127 * (hash("type") ^ hash(self._type))) & 0xFFFFFFFF
    
    def __eq__(self, other):
        return self._name == other._name \
            and self._type == other._type \
            and self._uniqueId == other._uniqueId
    
    def __ne__(self, other):
        return not self == other
    

class _MultiBinder(object):

    def __init__(self, binder, interface, annotated_with=None):
        self._binder = binder
        self._interface = interface
        self._multiBindingType = self.multibinding_type(self._interface)
        self._cls = self._multiBindingType
        self._annotation = annotated_with
        self._name = self.name_of(self._cls, self._annotation)
        self._provider = self._get_or_create_provider()

    def name_of(self, cls, annotated_with):
        annotation = annotated_with
        if annotation is not None:
            return str(annotation)
        else:
            return ""

    def _get_or_create_provider(self):
        binding = self._binder.get_binding(self._cls, self._annotation)
        if not binding:
            # The key binding the MultiBinder subclass is Key(self.multibinding_type(<iface>), annotation)
            self._binder.bind(self._cls,
                    to_provider=self._create_provider(), annotated_with=self._annotation)
            binding = self._binder.get_binding(self._cls, self._annotation)
        return binding.provider

    def _dsl_to_binding(self, to, to_provider, to_instance, in_scope):
        """
        This method registers bindings for each item in the _MultiBinder subclass.
        The binding key is Key(<itemInterface>, <computedAnnotationName based on self.multibinding_type>)
        Registering items with the binder allows the items to exist inside of scopes if necessary.
        """
        itemCls = self._interface
        itemAnnotation = _RealElement(self._name, self.multibinding_type.__name__)
        if to:
            #TODO: add some validation
            self._binder.bind(itemCls, to=to, in_scope=in_scope, annotated_with=itemAnnotation)
        elif to_provider:
            #TODO: add some validation
            self._binder.bind(itemCls, to_provider=to_provider, in_scope=in_scope, annotated_with=itemAnnotation)
        elif to_instance:
            self._binder.bind(itemCls, to_instance=to_instance, in_scope=in_scope, annotated_with=itemAnnotation)
        else:
            raise MultiBindingError('incorrect arguments to %s.add_binding'
                    % self.__class__.__name__)
        return self._binder.get_binding(itemCls, itemAnnotation)

class List(Annotation):
    """Used for binding lists."""


class ListBinder(_MultiBinder):

    multibinding_type = List

    def add_binding(self, to=None, to_provider=None, to_instance=None, in_scope=None):
        binding = self._dsl_to_binding(to, to_provider, to_instance, in_scope)
        self._provider.add_binding(binding)

    def _create_provider(self):
        class DynamicMultiBindingProvider(object):
            bindings = []

            @inject(injector=Injector)
            def __init__(self, injector):
                self._injector = injector

            @classmethod
            def add_binding(cls, binding):
                cls.bindings.append(binding)

            def get(self):
                return [self._injector.get_provider(b.key._interface, b.key._annotation).get()
                        for b in self.bindings]

        return DynamicMultiBindingProvider


class Dict(Annotation):
    """Used for binding dictionaries."""


class DictBinder(_MultiBinder):

    multibinding_type = Dict

    def add_binding(self, key, to=None, to_provider=None, to_instance=None, in_scope=None):
        binding = self._dsl_to_binding(to, to_provider, to_instance, in_scope)
        self._provider.add_binding(key, binding)

    def _create_provider(self):
        binder_self = self

        class DynamicMultiBindingProvider(object):
            bindings = {}

            @inject(injector=Injector)
            def __init__(self, injector):
                self._injector = injector

            @classmethod
            def add_binding(cls, key, binding):
                if key in cls.bindings:
                    msg = ('duplicate binding for %r in Dict(%s) found'
                            % (key, binder_self.interface.__class__.__name__))
                    raise MultiBindingError(msg)
                cls.bindings[key] = binding

            def get(self):
                return dict([(k, self._injector.get_provider(b.key._interface, b.key._annotation).get())
                        for k, b in self.bindings.items()])

        return DynamicMultiBindingProvider
