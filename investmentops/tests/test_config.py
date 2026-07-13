"""Pruebas para investmentops.config: carga de config.local.toml.

Cubre el trabajo de la tarea "Implementar la carga de ese archivo de
configuración al iniciar el sistema" (TASKS.md, Fase 1, "Setup del
proyecto"). No prueba validación de claves ni lógica de negocio: eso está
fuera de alcance de esta tarea (ver CONFIGURATION.md).
"""

from pathlib import Path

import pytest

from investmentops.config import ConfigError, _default_config_path, load_config


def test_load_config_reads_valid_toml(tmp_path: Path) -> None:
    config_file = tmp_path / "config.local.toml"
    config_file.write_text(
        '[cache]\n'
        'path = ".cache/"\n'
        "\n"
        "[ai_providers.default]\n"
        'provider = "anthropic"\n'
        'model = "claude"\n'
    )

    config = load_config(config_file)

    assert config["cache"]["path"] == ".cache/"
    assert config["ai_providers"]["default"]["provider"] == "anthropic"
    assert config["ai_providers"]["default"]["model"] == "claude"


def test_load_config_missing_file_raises_config_error(tmp_path: Path) -> None:
    missing_path = tmp_path / "config.local.toml"

    with pytest.raises(ConfigError, match="No se encontró"):
        load_config(missing_path)


def test_load_config_invalid_toml_raises_config_error(tmp_path: Path) -> None:
    config_file = tmp_path / "config.local.toml"
    config_file.write_text("esto no es toml valido [[[")

    with pytest.raises(ConfigError, match="no es TOML"):
        load_config(config_file)


def test_default_config_path_points_to_project_root() -> None:
    project_root = Path(__file__).resolve().parent.parent

    assert _default_config_path() == project_root / "config.local.toml"
