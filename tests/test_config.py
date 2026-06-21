#!/usr/bin/env python

"""Tests for the ConfigParserLoader."""

from pathlib import Path

import pytest

from snakeguice import config, create_injector
from snakeguice.errors import CreationError
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


def test_config_parser_loader_same_basename_collides(tmp_path: Path) -> None:
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir()
    d2.mkdir()
    (d1 / "settings.ini").write_text("[x]\na = 1\n")
    (d2 / "settings.ini").write_text("[x]\na = 2\n")

    class ConfigModule:
        def configure(self, binder: Binder) -> None:
            config.ConfigParserLoader(str(d1 / "settings.ini")).bind_configuration(
                binder
            )
            config.ConfigParserLoader(str(d2 / "settings.ini")).bind_configuration(
                binder
            )

    with pytest.raises(CreationError, match="namespace="):
        create_injector([ConfigModule()])


def test_config_parser_loader_same_namespace_different_keys_can_mingle(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.ini").write_text("[x]\na = 1\n")
    (tmp_path / "b.ini").write_text("[x]\nb = 2\n")

    class ConfigModule:
        def configure(self, binder: Binder) -> None:
            config.ConfigParserLoader(
                str(tmp_path / "a.ini"), namespace="merged"
            ).bind_configuration(binder)
            config.ConfigParserLoader(
                str(tmp_path / "b.ini"), namespace="merged"
            ).bind_configuration(binder)

    injector = create_injector([ConfigModule()])
    assert injector.get_instance(config.Config("merged:x:a")) == "1"
    assert injector.get_instance(config.Config("merged:x:b")) == "2"


def test_config_parser_loader_namespace_avoids_collision(tmp_path: Path) -> None:
    d1, d2 = tmp_path / "a", tmp_path / "b"
    d1.mkdir()
    d2.mkdir()
    (d1 / "settings.ini").write_text("[x]\na = 1\n")
    (d2 / "settings.ini").write_text("[x]\na = 2\n")

    class ConfigModule:
        def configure(self, binder: Binder) -> None:
            config.ConfigParserLoader(
                str(d1 / "settings.ini"), namespace="primary"
            ).bind_configuration(binder)
            config.ConfigParserLoader(
                str(d2 / "settings.ini"), namespace="replica"
            ).bind_configuration(binder)

    injector = create_injector([ConfigModule()])
    assert injector.get_instance(config.Config("primary:x:a")) == "1"
    assert injector.get_instance(config.Config("replica:x:a")) == "2"
