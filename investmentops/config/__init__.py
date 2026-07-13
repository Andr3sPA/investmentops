"""Carga de la configuración local (Config Loader).

Responsabilidad (ver ARCHITECTURE.md, sección "Manejo de configuración y
credenciales", y CONFIGURATION.md):
- Leer y parsear el archivo de configuración local (`config.local.toml`,
  en la raíz del proyecto) al iniciar el sistema.
- Devolver su contenido como un diccionario anidado, sin transformarlo,
  validarlo ni completarlo con valores por defecto.
- Fallar de forma clara (con un mensaje legible, no una traza críptica)
  cuando el archivo no existe o no es TOML válido.

Explícitamente fuera de alcance de este módulo (ver CONFIGURATION.md,
"Fuera de alcance de esta tarea"):
- La validación de que las claves requeridas estén presentes.
- Cualquier lógica de negocio que consuma estos valores (eso corresponde
  a investmentops.data_providers, investmentops.ai_providers y
  investmentops.data_layer).

El formato (TOML) y la ubicación (`config.local.toml` en la raíz del
proyecto, junto a la plantilla versionada `config.example.toml`) ya están
definidos en CONFIGURATION.md; este módulo solo implementa la lectura.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "config.local.toml"


class ConfigError(RuntimeError):
    """Error al localizar o parsear el archivo de configuración local."""


def _default_config_path() -> Path:
    """Ruta esperada de `config.local.toml` en la raíz del proyecto.

    Este archivo vive en `investmentops/config/__init__.py`, es decir dos
    niveles por debajo de la raíz del proyecto
    (`investmentops/config/` -> `investmentops/` -> raíz).
    """
    return Path(__file__).resolve().parent.parent.parent / CONFIG_FILENAME


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Carga y parsea el archivo de configuración local.

    Parameters
    ----------
    path:
        Ruta opcional al archivo de configuración. Si no se indica, se
        busca `config.local.toml` en la raíz del proyecto (junto a
        `config.example.toml` y `pyproject.toml`).

    Returns
    -------
    dict
        El contenido del archivo TOML como diccionario anidado, tal como
        lo produce `tomllib`. Se devuelve tal cual, sin validar claves
        requeridas ni aplicar valores por defecto — eso queda para una
        tarea posterior (ver CONFIGURATION.md).

    Raises
    ------
    ConfigError
        Si el archivo no existe en la ruta esperada, o si existe pero no
        se puede parsear como TOML válido.
    """
    config_path = Path(path) if path is not None else _default_config_path()

    if not config_path.is_file():
        raise ConfigError(
            "No se encontró el archivo de configuración local en "
            f"'{config_path}'. Antes de usar InvestmentOps, copia la "
            "plantilla y completa tus credenciales:\n"
            f"    cp config.example.toml {CONFIG_FILENAME}"
        )

    try:
        with config_path.open("rb") as config_file:
            return tomllib.load(config_file)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(
            f"El archivo de configuración '{config_path}' no es TOML "
            f"válido: {exc}"
        ) from exc
