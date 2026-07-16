"""Orquestador mínimo — disparo de la consulta al proveedor de datos, paso
de esos datos crudos a la capa de normalización, e invocación secuencial
de los agentes de análisis.

Cubre tres tareas de TASKS.md, Fase 1, "Orquestador mínimo":

- "Implementar la función que recibe un ticker y dispara la consulta al
  proveedor de Fase 1." (`fetch_raw_data`, ya completada en una
  conversación anterior, ver PROGRESS.md).
- "Implementar el paso de datos crudos a la capa de normalización."
  (`fetch_and_normalize`, ya completada en una conversación anterior, ver
  PROGRESS.md).
- "Implementar la invocación secuencial de los dos agentes de análisis
  (salud financiera, valoración) sobre el modelo normalizado."
  (`run_analysis_engines`, esta tarea).

Las tres funciones viven en el mismo módulo porque son piezas
consecutivas del mismo pipeline descrito en ARCHITECTURE.md ("Resumen
del flujo de una investigación", pasos 3-5): el orquestador consulta la
fuente de datos, pasa esos datos crudos a la capa de normalización, y
luego pasa el modelo normalizado a los motores de análisis.

## Invocación secuencial de los agentes de análisis

`run_analysis_engines` es intencionalmente una función pequeña que
encadena piezas ya existentes y ya probadas por separado:

1. `investmentops.analysis_engines.financial_health.analyze_financial_health`
   — recibe el `FinancialStatement` normalizado, calcula sus propias
   métricas deterministas, invoca al proveedor de IA configurado para
   `"financial_health"` y devuelve un `AnalysisResult`.
2. `investmentops.analysis_engines.valuation.analyze_valuation` — recibe
   el `MarketData` y el `FinancialStatement` normalizados, calcula sus
   propias métricas deterministas, invoca al proveedor de IA configurado
   para `"valuation"` y devuelve otro `AnalysisResult`.

Ambos agentes ya calculan sus propias métricas internamente a partir de
`company_data` si no se les pasan precalculadas (ver
`analyze_financial_health`/`analyze_valuation`, parámetro `metrics`
opcional); esta función no recalcula nada ni duplica esa lógica, solo
invoca ambos agentes en el orden en que aparecen en `TASKS.md` (salud
financiera, luego valoración) y agrupa sus resultados.

Alcance deliberadamente mínimo, conforme al desglose de TASKS.md en esta
misma sección ("Orquestador mínimo"). Esta función NO incluye (tareas
separadas y posteriores):

- El ensamblado de ambos resultados en un `ResearchResult`
  (investmentops.core.research_result): esta función devuelve una lista
  simple de `AnalysisResult`, no la estructura final de "Resultado de
  investigación" (que además requiere la `Company` investigada y una
  `generated_at`, ninguna de las cuales es responsabilidad de esta
  pieza).
- El manejo de fallos de cualquiera de los dos agentes sin detener el
  resto del flujo: si `analyze_financial_health` o `analyze_valuation`
  levantan una excepción (`PromptError`, `AgentProviderSelectionError`,
  `AIProviderError`), esta función la deja propagar tal cual, sin
  capturarla ni traducirla a un `ResearchFailure`. Ese manejo es
  explícitamente la tarea siguiente de esta misma sección de TASKS.md.
- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): fuera de alcance, igual que ya se
  documentó para `fetch_raw_data`/`fetch_and_normalize`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.analysis_engines.financial_health import analyze_financial_health
from investmentops.analysis_engines.valuation import analyze_valuation
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


def run_analysis_engines(
    company_data: NormalizedCompanyData,
    *,
    config: dict[str, Any] | None = None,
) -> list[AnalysisResult]:
    """Invoca secuencialmente los agentes de salud financiera y valoración.

    Encadena, en este orden, `analyze_financial_health` (sobre
    `company_data.financial_statement`) y `analyze_valuation` (sobre
    `company_data.market_data` y `company_data.financial_statement`),
    devolviendo los dos `AnalysisResult` obtenidos. Cada agente calcula
    sus propias métricas deterministas internamente (no se le pasan
    precalculadas): esta función no duplica ese cálculo, solo encadena la
    invocación de ambos agentes ya completos.

    Parameters
    ----------
    company_data:
        El `NormalizedCompanyData` de la empresa a analizar (típicamente
        el resultado de `fetch_and_normalize(ticker, ...)`), con el
        `FinancialStatement` y el `MarketData` ya normalizados.
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), propagada tal cual a ambos
        agentes para resolver su proveedor de IA configurado (ver
        `investmentops.ai_providers.selection.resolve_agent_provider`).
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco. Si no se indica, cada agente llama internamente a
        `load_config()`.

    Returns
    -------
    list[AnalysisResult]
        Una lista con exactamente dos elementos, en este orden: el
        resultado del agente de salud financiera
        (`analysis_id="financial_health"`) y el resultado del agente de
        valoración (`analysis_id="valuation"`).

    Raises
    ------
    PromptError
        Si no se puede cargar el archivo de prompt de alguno de los dos
        agentes (ver `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para alguno de los
        dos agentes según la configuración.
    AIProviderError
        Si el proveedor de IA resuelto para alguno de los dos agentes no
        tiene una integración concreta implementada, faltan credenciales
        imprescindibles, o la invocación al modelo de lenguaje falla.
    ConfigError
        Si `config` no se indica y no se puede cargar
        `config.local.toml`.

    Notes
    -----
    Esta función no captura ninguna de las excepciones anteriores: si el
    agente de salud financiera falla, el agente de valoración no llega a
    invocarse. Detener el flujo ante un fallo parcial de uno de los dos
    agentes (en vez de continuar con el otro y dejarlo explícito) es, de
    forma deliberada, el comportamiento de esta tarea; capturar esos
    fallos para no detener el resto del flujo es la tarea siguiente de
    esta misma sección de TASKS.md ("Orquestador mínimo").
    """
    financial_health_result = analyze_financial_health(
        company_data.financial_statement, config=config
    )
    valuation_result = analyze_valuation(
        company_data.market_data,
        company_data.financial_statement,
        config=config,
    )

    return [financial_health_result, valuation_result]
