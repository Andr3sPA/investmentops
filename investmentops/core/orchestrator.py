"""Orquestador mínimo — disparo de la consulta al proveedor de datos, paso
de esos datos crudos a la capa de normalización, invocación secuencial de
los agentes de análisis, ensamblado del "Resultado de investigación"
final, y manejo de fallos parciales sin detener el resto del flujo.

Cubre cinco tareas de TASKS.md, Fase 1, "Orquestador mínimo":

- "Implementar la función que recibe un ticker y dispara la consulta al
  proveedor de Fase 1." (`fetch_raw_data`, ya completada, ver PROGRESS.md).
- "Implementar el paso de datos crudos a la capa de normalización."
  (`fetch_and_normalize`, ya completada, ver PROGRESS.md).
- "Implementar la invocación secuencial de los dos agentes de análisis
  (salud financiera, valoración) sobre el modelo normalizado."
  (`run_analysis_engines`, ya completada, ver PROGRESS.md).
- "Implementar el ensamblado de ambos resultados en un 'Resultado de
  investigación' único." (`assemble_research_result`, ya completada, ver
  PROGRESS.md).
- "Implementar el manejo de fallo del proveedor de datos o del proveedor
  de IA sin detener el resto del flujo, dejándolo explícito en el
  resultado." (`investigate`, esta tarea).

Las cinco funciones viven en el mismo módulo porque son piezas
consecutivas del mismo pipeline descrito en ARCHITECTURE.md ("Resumen
del flujo de una investigación", pasos 3-6).

## Manejo de fallos parciales (`investigate`)

`fetch_and_normalize` y `run_analysis_engines` documentan explícitamente
que **no** capturan las excepciones de sus propias piezas (`DataProviderError`,
`NormalizationError`, `PromptError`, `AgentProviderSelectionError`,
`AIProviderError`): las propagan tal cual, y `run_analysis_engines` en
particular detiene el flujo si el primer agente (salud financiera)
falla, sin llegar a invocar el segundo (valoración). Esa fue una decisión
deliberada de esas tareas, dejando explícitamente esta tarea (la última
de "Orquestador mínimo") como la responsable de envolver el flujo
completo y decidir qué pasa ante cada tipo de fallo sin detener el
resto (ver ARCHITECTURE.md, "Manejo de errores y limitaciones").

`investigate(ticker, ...)` es esa función de flujo completo:

1. **Consulta y normalización** (`fetch_and_normalize`): si falla con
   `DataProviderError` (la fuente de datos no respondió, el ticker no
   existe) o `NormalizationError` (el payload crudo no trae los campos
   imprescindibles), **no tiene sentido invocar ningún agente** — ambos
   agentes de análisis necesitan el modelo normalizado como entrada. En
   este caso se devuelve de inmediato un `ResearchResult` con
   `analysis_results=[]` y un único `ResearchFailure(stage="data_provider",
   identifier=<ticker normalizado>, reason=<mensaje del error>)`. Esto
   responde explícitamente la pregunta que `PROGRESS.md` dejó abierta
   ("¿tiene sentido producir un `ResearchResult` en absoluto?"): sí, con
   la etapa de datos marcada como fallida y ningún análisis disponible,
   en vez de no devolver nada — conforme a ARCHITECTURE.md, "el reporte
   final debe reflejar explícitamente qué información no pudo
   obtenerse, en vez de fallar silenciosamente".
2. **Agentes de análisis, uno por uno**: si la normalización tuvo éxito,
   se invoca `analyze_financial_health` y, en un `try/except` **separado**,
   `analyze_valuation`. Un fallo de cualquiera de los dos
   (`PromptError`, `AgentProviderSelectionError` o `AIProviderError`) se
   captura y se traduce a `ResearchFailure(stage="analysis_engine",
   identifier=<AGENT_ID del agente que falló>, reason=<mensaje>)`, sin
   impedir que el otro agente se ejecute — a diferencia de
   `run_analysis_engines`, que se detiene ante el primer fallo. Los
   resultados exitosos (puede haber cero, uno o dos) se recolectan en
   orden.
3. **Ensamblado final**: se llama a `assemble_research_result(ticker,
   <resultados exitosos>, failures=<fallos capturados>)`, reutilizando
   la función ya existente sin modificarla.

`investigate` no reemplaza a `run_analysis_engines` ni a
`fetch_and_normalize`: ambas se mantienen sin cambios, con su
comportamiento "se detiene ante el primer fallo" documentado, para
quien lo necesite explícitamente (ej. un script que sí quiera fallar
rápido). `investigate` es la nueva pieza que sí ofrece resiliencia ante
fallos parciales, componiendo las piezas ya existentes de una forma
distinta (agente por agente, en vez de vía `run_analysis_engines`).

Fuera de alcance de este módulo (aún):
- Completar `Company.name`/`sector`/`market` con datos reales: no hay
  hoy una fuente de datos que los provea (ver docstring de
  `assemble_research_result`).
- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): fuera de alcance, igual que ya se
  documentó para `fetch_raw_data`/`fetch_and_normalize`.
- Conectar `investigate` con la CLI: tarea separada y posterior (ver
  TASKS.md, sección "CLI").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from investmentops.ai_providers import AgentProviderSelectionError, AIProviderError
from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.analysis_engines.financial_health import (
    AGENT_ID as FINANCIAL_HEALTH_AGENT_ID,
    analyze_financial_health,
)
from investmentops.analysis_engines.prompts import PromptError
from investmentops.analysis_engines.valuation import (
    AGENT_ID as VALUATION_AGENT_ID,
    analyze_valuation,
)
from investmentops.core.research_result import ResearchFailure, ResearchResult
from investmentops.data_layer.domain import Company
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_from_raw,
    market_data_from_raw,
)
from investmentops.data_providers.contracts import (
    DataProvider,
    DataProviderError,
    RawProviderData,
)
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
        (investmentops.data_providers.contracts). Si no se indica, se usa
        `FMPFundamentalsProvider`, el proveedor concreto ya elegido para
        el MVP.

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
        no captura ni traduce esa excepción; ver `investigate` para el
        manejo de fallos sin detener el resto del flujo.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    data_provider = provider if provider is not None else FMPFundamentalsProvider(config=config)
    return data_provider.fetch(ticker)


@dataclass(frozen=True)
class NormalizedCompanyData:
    """Datos normalizados de una empresa, listos para los agentes de análisis.

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
    y `...market_data_from_raw`.

    Raises
    ------
    DataProviderError
        Ver `fetch_raw_data`.
    NormalizationError
        Si los datos crudos obtenidos no traen los campos imprescindibles
        para construir `FinancialStatement` o `MarketData`. Esta función
        no captura ni traduce esa excepción; ver `investigate` para el
        manejo de fallos sin detener el resto del flujo.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
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

    Notes
    -----
    Esta función no captura ninguna excepción de los agentes: si el
    agente de salud financiera falla, el agente de valoración no llega a
    invocarse. Ese comportamiento "todo o nada" se mantiene intacto para
    quien lo necesite explícitamente; `investigate` (en este mismo
    módulo) ofrece en cambio manejo de fallos parciales, invocando cada
    agente por separado en vez de usar esta función.
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


def assemble_research_result(
    ticker: str,
    analysis_results: Sequence[AnalysisResult],
    *,
    failures: Sequence[ResearchFailure] = (),
    generated_at: datetime | None = None,
) -> ResearchResult:
    """Ensambla los resultados de análisis de una empresa en un `ResearchResult`.

    La `Company` incluida en el resultado es **mínima**: solo lleva el
    `ticker` recibido (normalizado a mayúsculas), con `name`, `sector` y
    `market` vacíos, porque ningún dato normalizado disponible en la Fase
    1 (`FinancialStatement`, `MarketData`) expone esos campos.
    """
    company = Company(ticker=ticker.strip().upper(), name="", sector="", market="")

    return ResearchResult(
        company=company,
        analysis_results=list(analysis_results),
        failures=list(failures),
        generated_at=generated_at if generated_at is not None else datetime.now(timezone.utc),
    )


def investigate(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> ResearchResult:
    """Ejecuta el flujo completo de investigación para `ticker`, sin que un
    fallo parcial (fuente de datos o proveedor de IA de un agente) detenga
    el resto del flujo.

    Ver el docstring del módulo, sección "Manejo de fallos parciales
    (`investigate`)", para la explicación completa de las tres etapas
    (consulta+normalización, agentes por separado, ensamblado) y de por
    qué un fallo en la primera etapa impide continuar (ningún agente
    tiene datos con los que trabajar) mientras que un fallo en un agente
    de la segunda etapa no impide que el otro se ejecute.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a investigar (ej. ``"AAPL"``).
    config:
        Configuración ya cargada, propagada a `fetch_and_normalize` y a
        cada agente de análisis. Útil para pruebas, para no depender de
        un `config.local.toml` real en disco.
    provider:
        Proveedor de datos ya construido, propagado a `fetch_and_normalize`.
        Pensado sobre todo para pruebas.

    Returns
    -------
    ResearchResult
        - Si `fetch_and_normalize` falla (`DataProviderError` o
          `NormalizationError`): `analysis_results=[]` y un único
          `ResearchFailure(stage="data_provider", identifier=<ticker
          normalizado>, reason=<mensaje del error>)`.
        - Si la normalización tiene éxito: `analysis_results` contiene
          los resultados de los agentes que sí completaron su análisis
          (cero, uno o dos, en el orden salud financiera → valoración), y
          `failures` contiene un `ResearchFailure(stage="analysis_engine",
          identifier=<analysis_id del agente>, reason=<mensaje del
          error>)` por cada agente que falló
          (`PromptError`, `AgentProviderSelectionError` o
          `AIProviderError`).

    Notes
    -----
    Esta función nunca deja escapar `DataProviderError`,
    `NormalizationError`, `PromptError`, `AgentProviderSelectionError` ni
    `AIProviderError`: todas se capturan y se traducen a
    `ResearchFailure`. Otras excepciones (ej. `ConfigError` si no se
    puede cargar `config.local.toml` en absoluto) sí se propagan, ya que
    representan un problema de configuración del entorno, no un fallo
    parcial de una fuente o un agente concretos.
    """
    try:
        company_data = fetch_and_normalize(ticker, config=config, provider=provider)
    except (DataProviderError, NormalizationError) as exc:
        failure = ResearchFailure(
            stage="data_provider",
            identifier=ticker.strip().upper() if ticker else ticker,
            reason=str(exc),
        )
        return assemble_research_result(ticker, [], failures=[failure])

    analysis_results: list[AnalysisResult] = []
    failures: list[ResearchFailure] = []

    try:
        analysis_results.append(
            analyze_financial_health(company_data.financial_statement, config=config)
        )
    except (PromptError, AgentProviderSelectionError, AIProviderError) as exc:
        failures.append(
            ResearchFailure(
                stage="analysis_engine",
                identifier=FINANCIAL_HEALTH_AGENT_ID,
                reason=str(exc),
            )
        )

    try:
        analysis_results.append(
            analyze_valuation(
                company_data.market_data,
                company_data.financial_statement,
                config=config,
            )
        )
    except (PromptError, AgentProviderSelectionError, AIProviderError) as exc:
        failures.append(
            ResearchFailure(
                stage="analysis_engine",
                identifier=VALUATION_AGENT_ID,
                reason=str(exc),
            )
        )

    return assemble_research_result(ticker, analysis_results, failures=failures)
