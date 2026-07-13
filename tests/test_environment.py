"""Prueba de humo del entorno del proyecto.

No prueba lógica de negocio (todavía no existe, ver TASKS.md). Su único
propósito es confirmar que el paquete `investmentops` y sus subpaquetes
se pueden importar correctamente una vez instalado el entorno de
desarrollo (`pip install -e ".[dev]"`), como forma de verificar que la
configuración del gestor de dependencias (pyproject.toml) es correcta.
"""

import importlib


def test_top_level_package_imports():
    module = importlib.import_module("investmentops")
    assert module is not None


def test_all_subpackages_import():
    subpackages = [
        "investmentops.cli",
        "investmentops.core",
        "investmentops.data_providers",
        "investmentops.data_layer",
        "investmentops.analysis_engines",
        "investmentops.ai_providers",
        "investmentops.reports",
    ]
    for name in subpackages:
        module = importlib.import_module(name)
        assert module is not None
