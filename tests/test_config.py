#!/usr/bin/env python

"""Tests for the ConfigParserLoader."""

from pathlib import Path

import pytest

from snakeguice import config, create_injector
from snakeguice.interfaces import Binder


def test_config_parser_loader_raises_on_missing_file() -> None:
    class ConfigModule:
        def configure(self, binder: Binder) -> None:
            config.ConfigParserLoader(
                "/tmp/does-not-exist-snake-guice.ini"
            ).bind_configuration(binder)

    with pytest.raises(FileNotFoundError) as exc_info:
        create_injector([ConfigModule()])

    assert "does-not-exist-snake-guice.ini" in str(exc_info.value)


def test_config_parser_loader_binds_ini_values_to_config_annotations(
    tmp_path: Path,
) -> None:
    ini_path = tmp_path / "settings.ini"
    ini_path.write_text("[server]\nhost = example.com\nport = 8080\n")

    class ConfigModule:
        def configure(self, binder: Binder) -> None:
            config.ConfigParserLoader(str(ini_path)).bind_configuration(binder)

    injector = create_injector([ConfigModule()])

    host = injector.get_instance(config.Config("settings.ini:server:host"))
    port = injector.get_instance(config.Config("settings.ini:server:port"))

    assert host == "example.com"
    assert port == "8080"
