from configparser import ConfigParser
from pathlib import Path
from typing import Iterable

from snakeguice.annotation import UNANNOTATED, Annotation
from snakeguice.binder import Key
from snakeguice.interfaces import Binder


class Config(Annotation):
    """Annotation for ConfigParser style config files."""


class ConfigParserLoader:
    def __init__(self, filename: str, namespace: str | None = None) -> None:
        self.filename = filename
        self.namespace = namespace if namespace is not None else Path(filename).name

    def bind_configuration(self, binder: Binder) -> None:
        parser = ConfigParser()
        loaded = parser.read(self.filename)
        if not loaded:
            raise FileNotFoundError(f"Config file not found: {self.filename}")
        for section, option, value in _iterate_parser(parser):
            annotation = Config(f"{self.namespace}:{section}:{option}")
            if binder.get_own_binding(Key(annotation, UNANNOTATED)) is not None:  # type: ignore[arg-type]
                binder.add_error(
                    f"config key '{annotation}' is already bound; "
                    "if two files share the same basename, pass namespace= "
                    "to give each loader a distinct key prefix"
                )
            else:
                binder.bind(annotation, to_instance=value)


def _iterate_parser(parser: ConfigParser) -> Iterable[tuple[str, str, str]]:
    for section in parser.sections():
        for option in parser.options(section):
            value = parser.get(section, option)
            yield section, option, value
