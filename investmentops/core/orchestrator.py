"""Orquestador mínimo — disparo de la consulta al proveedor de datos y
paso de esos datos crudos a la capa de normalización.

Cubre dos tareas de TASKS.md, Fase 1, "Orquestador mínimo":

- "Implementar la función que recibe un ticker y dispara la consulta al
  proveedor de Fase 1." (`fetch_raw_data`, ya completada en una
  conversación anterior, ver PROGRESS.md).
- "Implementar el paso de datos crudos a la capa de normalización."
  (`fetch_and_normalize`, esta tarea).

Ambas funciones viven en el mismo módulo porque son la primera y segunda
pieza del mismo pipeline secuencial descrito en ARCHITECTURE.md
("Resumen del flujo de una investigación", pasos 3-4): el orquestador
consulta la fuente de datos y luego pasa esos datos crudos a la capa de
normalización, antes de invocar a los agentes de análisis.

`fetch_and_normalize` es intencionalmente una función pequeña que
encadena piezas ya existentes y ya probadas por separado:

1. `fetch_raw_data(ticker, ...)` (este mismo módulo) — obtiene
   `RawProviderData` desde el proveedor de datos fundamentales.
2. `investmentops.data_layer.normalization.financial_statement_from_raw`
   y `...market_data_from_raw` — transforman ese `RawProviderData` a los
   modelos de dominio normalizados `FinancialStatement` y `MarketData`.

Alcance deliberadamente mínimo, conforme al desglose de TASKS.md en esta
misma sección ("Orquestador mínimo"). Esta función NO incluye (tareas
separadas y posteriores):

- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): decidir cuándo evitar la llamada al
  proveedor por tener ya un dato normalizado reciente en caché es una
  decisión de una tarea posterior que también involucra esta pieza, no
  algo que deba resolverse aquí de forma implícita.
- La invocación de los agentes de análisis (salud financiera, valoración).
- El ensamblado en un `ResearchResult` (investmentops.core.research_result).
- El manejo de fallos del proveedor de datos o de normalización sin
  detener el resto del flujo (esta función deja propagar
  `DataProviderError` y `NormalizationError` tal cual, sin capturarlas ni
  traducirlas a un `ResearchFailure`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.normalization import (
    financial_statement_from_raw,
    market_data_from_raw,
)
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


@dataclass(frozen=True)
class NormalizedCompanyData:
    """Datos normalizados de una empresa, listos para los agentes de análisis.

    Es el tipo de salida de `fetch_and_normalize`: agrupa los dos modelos
    de dominio normalizados que hoy consumen los agentes de análisis ya
    implementados (`investmentops.analysis_engines.financial_health.
    analyze_financial_health` y `...valuation.analyze_valuation`), para
    que quien invoque el orquestador no tenga que manejar dos valores
    sueltos.

    Attributes
    ----------
    financial_statement:
        Estados financieros normalizados de la empresa (ver
        `investmentops.data_layer.FinancialStatement`).
    market_data:
        Datos de mercado normalizados de la misma empresa (ver
        `investmentops.data_layer.MarketData`).
    """

    financial_statement: FinancialStatement
    market_data: MarketData


def fetch_and_normalize(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> NormalizedCompanyData:
    """Consulta al proveedor de datos y normaliza el resultado para `ticker`.

    Encadena `fetch_raw_data(ticker, ...)` con
    `investmentops.data_layer.normalization.financial_statement_from_raw`
    y `...market_data_from_raw`, de forma que quien invoque esta función
    reciba directamente los modelos de dominio normalizados, sin tener
    que conocer la forma del `payload` crudo que entrega el proveedor de
    datos fundamentales.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se
        propaga tal cual a `fetch_raw_data`.
    config:
        Configuración ya cargada, propagada a `fetch_raw_data` para
        construir el proveedor por defecto si no se indica `provider`.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco.
    provider:
        Proveedor de datos ya construido, propagado a `fetch_raw_data`.
        Pensado sobre todo para pruebas (inyectar un proveedor mínimo de
        prueba), sin depender de una llamada de red real.

    Returns
    -------
    NormalizedCompanyData
        Los `FinancialStatement` y `MarketData` normalizados de la
        empresa, listos para pasarse a los agentes de análisis ya
        implementados (`analyze_financial_health`, `analyze_valuation`).

    Raises
    ------
    DataProviderError
        Si `fetch_raw_data` no puede obtener los datos crudos (proveedor
        caído, ticker inexistente, respuesta no interpretable). Ver
        `fetch_raw_data`.
    NormalizationError
        Si los datos crudos obtenidos no traen los campos imprescindibles
        para construir `FinancialStatement` o `MarketData` (ver
        `investmentops.data_layer.normalization`). Esta función no
        captura ni traduce esa excepción: el manejo de fallos sin
        detener el resto del flujo es una tarea separada y posterior
        (ver TASKS.md, "Orquestador mínimo").
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml` (propagado desde `fetch_raw_data`).
    """
    raw = fetch_raw_data(ticker, config=config, provider=provider)
    financial_statement = financial_statement_from_raw(raw)
    market_data = market_data_from_raw(raw)

    return NormalizedCompanyData(
        financial_statement=financial_statement,
        market_data=market_data,
    )
