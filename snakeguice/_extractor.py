from collections import namedtuple

Param = namedtuple("Param", ["name", "dtype", "annotation"])


def extract_params(method):
    types = getattr(method, "__guice_types__", {})
    annotations = getattr(method, "__guice_annotations__", {})
    for name, dtype in types.items():
        annotation = annotations.get(name)
        yield Param(name, dtype, annotation)
