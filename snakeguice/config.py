from configparser import ConfigParser
from pathlib import Path
from typing import Iterable

from snakeguice.annotation import Annotation
from snakeguice.interfaces import Binder


class Config(Annotation):
    """Annotation for ConfigParser style config files."""


class ConfigParserLoader:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.short_name = Path(filename).name

    def bind_configuration(self, binder: Binder) -> None:
        parser = ConfigParser()
        loaded = parser.read(self.filename)
        if not loaded:
            raise FileNotFoundError(f"Config file not found: {self.filename}")
        for section, option, value in _iterate_parser(parser):
            annotation = Config(f"{self.short_name}:{section}:{option}")
            binder.bind(annotation, to_instance=value)


def _iterate_parser(parser: ConfigParser) -> Iterable[tuple[str, str, str]]:
    for section in parser.sections():
        for option in parser.options(section):
            value = parser.get(section, option)
            yield section, option, value
