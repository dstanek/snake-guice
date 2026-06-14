"""
"""


class ParameterInterceptor:
    def __init__(self, injector) -> None:
        self._injector = injector

    def __call__(self, annotation=None, **kwargs):
        if len(kwargs) != 1:
            raise TypeError("ParameterInterceptor expects exactly one name=Type kwarg")
        (param_name, param_type) = next(iter(kwargs.items()))

        def callback(method):
            def _callback(*args, **kwargs):
                kwargs[param_name] = self._injector.get_instance(param_type, annotation)
                return method(*args, **kwargs)

            return _callback

        return callback
