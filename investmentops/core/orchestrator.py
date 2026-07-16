"""Orquestador mínimo — disparo de la consulta al proveedor de datos.

Cubre la tarea "Implementar la función que recibe un ticker y dispara la
consulta al proveedor de Fase 1" (TASKS.md, Fase 1, "Orquestador
mínimo"). Es la primera pieza del orquestador (ver ARCHITECTURE.md,
componente 2): recibe un ticker y consulta al proveedor de datos
fundamentales ya elegido para el MVP (Financial Modeling Prep, ver
TASKS.md, "Fuente de datos fundamentales" y PROGRESS.md).

Alcance deliberadamente mínimo, conforme al desglose de TASKS.md en esta
misma sección ("Orquestador mínimo"): esta función solo dispara la
consulta cruda al proveedor. NO incluye (tareas separadas y
posteriores):

- El paso de esos datos crudos a la capa de normalización
  (investmentops.data_layer.normalization).
- La invocación de los agentes de análisis (salud financiera, valoración).
- El ensamblado en un `ResearchResult` (investmentops.core.research_result).
- El manejo de fallos del proveedor de datos o de IA sin detener el
  resto del flujo (esta función deja propagar `DataProviderError` tal
  cual, sin capturarla ni traducirla).

No verifica primero la caché de datos normalizados
(investmentops.data_layer.cache): esa caché guarda modelos ya
normalizados (`FinancialStatement`, `MarketData`), no datos crudos, por
lo que decidir si se usa el dato cacheado en vez de llamar al proveedor
es una decisión que corresponde a una tarea posterior que también
involucre el paso de normalización, no a esta tarea aislada.
"""

from __future__ import annotations

from typing import Any

from investmentops.data_providers.contracts import DataProvider, RawProviderData
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider


def fetch_raw_data(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> RawProviderData:
    """Consulta al proveedor de datos fundamentales de Fase 1 para `ticker`.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se pasa
        tal cual al proveedor, que es quien valida/normaliza su formato
        (ver `FMPFundamentalsProvider.fetch`).
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), usada para construir el
        proveedor por defecto si no se indica `provider` explícitamente.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco. Se ignora si `provider` ya se indica.
    provider:
        Proveedor de datos ya construido a usar en vez del proveedor por
        defecto. Cumple el contrato `DataProvider`
        (investmentops.data_providers.contracts). Pensado sobre todo para
        pruebas (inyectar un proveedor mínimo de prueba, ver
        `investmentops/tests/test_data_providers_contracts.py`), pero
        también deja la puerta abierta a que una tarea futura del
        orquestador elija entre varios proveedores sin modificar esta
        función. Si no se indica, se usa `FMPFundamentalsProvider`, el
        proveedor concreto ya elegido para el MVP.

    Returns
    -------
    RawProviderData
        Los datos crudos obtenidos, junto con sus metadatos de
        procedencia (ver `investmentops.data_providers.contracts`).

    Raises
    ------
    DataProviderError
        Si el proveedor no responde, el ticker no existe, o la respuesta
        no se puede interpretar (ver `DataProvider.fetch`). Esta función
        no captura ni traduce esa excepción: el manejo de fallos sin
        detener el resto del flujo es una tarea separada y posterior
        (ver TASKS.md, "Orquestador mínimo").
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml` (ver
        `investmentops.config.load_config`, invocado internamente por
        `FMPFundamentalsProvider` cuando no se le pasan credenciales
        explícitas).
    """
    data_provider = provider if provider is not None else FMPFundamentalsProvider(config=config)
    return data_provider.fetch(ticker)
