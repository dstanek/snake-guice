from collections import namedtuple

Param = namedtuple("Param", ["name", "dtype", "annotation"])


def extract_params(method):
    types = getattr(method, "__annotations__", {})
    annotations = getattr(method, "__guice_annotations__", {})
    for name, dtype in types.items():
        if name == "return":
            continue
        annotation = annotations.get(name)
        yield Param(name, dtype, annotation)
