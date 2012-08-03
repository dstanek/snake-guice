"""Providers used in the binding process."""

# pylint: disable-msg=C0111
#         providers are so small that we can safely omit doc comments

from snakeguice.decorators import inject
from snakeguice.interfaces import Injector


def create_simple_provider(cls):
    class DynamicSimpleProvider(object):

        @inject(injector=Injector)
        def __init__(self, injector):
            self._injector = injector

        def get(self):
            return self._injector.create_object(cls)

    return DynamicSimpleProvider

class __InstanceProvider(object):
    __slots__ = ['__obj']
    def __init__(self, obj):
        self.__obj = obj
    def get(self):
        return self.__obj
    
def create_instance_provider(obj):
    """
    Snake Guice internal note:
    Providers can be dynamically instantiated by the injector
    but there is no reason to delay that when binding directly
    to instances.
    """
    return __InstanceProvider(obj)
