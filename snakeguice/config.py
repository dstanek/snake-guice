import os
from configparser import SafeConfigParser
from typing import Iterable, Tuple, Type

from snakeguice.annotation import Annotation
from snakeguice.interfaces import Binder


class Config(Annotation):
    """Annotation for ConfigParser style config files."""


class ConfigParserLoader:
    def __init__(self, filename: str) -> None:  # TODO: pathlib
        self.filename = filename
        self.short_name = os.path.basename(filename)

    def bind_configuration(self, binder: Binder) -> None:
        parser = SafeConfigParser()
        parser.read(self.filename)
        for section, option, value in _iterate_parser(parser):
            annotation = Config("%s:%s:%s" % (self.short_name, section, option))
            binder.bind(annotation, to_instance=value)


def _iterate_parser(parser) -> Iterable[Tuple[str, str, Type]]:
    for section in parser.sections():
        for option in parser.options(section):
            value = parser.get(section, option)
            yield section, option, value
