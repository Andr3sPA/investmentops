"""Orquestador mínimo — disparo de la consulta al proveedor de datos, paso
de esos datos crudos a la capa de normalización, invocación secuencial de
los agentes de análisis, ensamblado del "Resultado de investigación"
final, manejo de fallos parciales sin detener el resto del flujo,
generación de reportes (Markdown/HTML) tras ensamblar ese resultado,
obtención/normalización de la serie histórica de ingresos y beneficios, y
registro de la invocación del motor de evolución de ingresos y beneficios
(Fase 3).

Cubre nueve tareas:

Fase 1, "Orquestador mínimo" (TASKS.md):
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
  resultado." (`investigate`, ya completada, ver PROGRESS.md).

Fase 2, "Orquestador y CLI" (TASKS.md):
- "Extender el orquestador para invocar los generadores de reporte tras
  ensamblar el resultado de investigación." (`generate_reports`,
  `investigate_and_generate_reports`, ya completada, ver PROGRESS.md).
- "Añadir al comando CLI la opción de formato de salida (markdown, html,
  o ambos)." — Esta tarea extiende `generate_reports`/
  `investigate_and_generate_reports` con un parámetro `formats` opcional,
  consumido por `investmentops.cli.dispatch` (ver ese módulo) para
  generar solo el/los formato(s) que el usuario pidió por CLI.

Fase 3, "Orquestador" (TASKS.md):
- "Implementar en el orquestador la función que obtiene y normaliza la
  serie histórica de una empresa para un ticker (encadenando
  `FMPFundamentalsProvider.fetch_historical` con
  `financial_statement_series_from_raw`), como pieza reutilizable
  análoga a `fetch_and_normalize`." (`fetch_raw_historical_data`,
  `fetch_and_normalize_historical`, ya completada, ver PROGRESS.md).
- "Registrar la invocación de `assemble_trend_analysis` en el flujo de
  análisis del orquestador, conforme a la decisión de integración ya
  tomada, sin modificar los motores existentes (salud financiera,
  valoración)." (`run_trend_analysis_engine`,
  `_trend_analysis_result_to_analysis_result`, esta tarea).

Las siete primeras funciones viven en el mismo módulo porque son piezas
consecutivas del mismo pipeline descrito en ARCHITECTURE.md ("Resumen
del flujo de una investigación", pasos 3-8). Las de esta tarea se suman
al mismo módulo por el mismo motivo, y porque es aquí -no en
`investmentops.analysis_engines.trends`- donde vive el adaptador
decidido en `investmentops/core/TREND_INTEGRATION.md` (ver esa sección
más abajo).

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
   identifier=<ticker normalizado>, reason=<mensaje del error>)`.
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
`fetch_and_normalize`: ambas se mantienen sin cambios. Tampoco invoca
todavía `run_trend_analysis_engine` (ver más abajo): esa integración es
la tarea siguiente y separada de esta misma sección de TASKS.md.

## Generación de reportes (`generate_reports` / `investigate_and_generate_reports`)

Conecta el orquestador con los generadores de reporte ya implementados
en Fase 2 (`investmentops.reports`: `render_markdown` /
`save_markdown_report` y `render_html` / `save_html_report`), sin
modificar el contrato ya existente de `investigate(ticker, ...) ->
ResearchResult`: muchas piezas del sistema (CLI, pruebas de Fase 1) ya
dependen de que `investigate` devuelva únicamente un `ResearchResult`,
sin efectos secundarios de E/S. Reescribir esa función para que también
escriba archivos habría sido un cambio de contrato innecesario.

En su lugar, existen dos funciones separadas:

- **`generate_reports(result, ...)`**: recibe un `ResearchResult` ya
  ensamblado (típicamente la salida de `investigate`) y genera + guarda
  los formatos de reporte solicitados, reutilizando sin modificarlas las
  funciones ya existentes de `investmentops.reports`. Devuelve las rutas
  de los archivos escritos, siempre en el orden `[markdown_path,
  html_path]` cuando ambos se solicitan (el orden nunca depende del
  orden en que se pidan los formatos, ver parámetro `formats` abajo).
- **`investigate_and_generate_reports(ticker, ...)`**: función de
  conveniencia que encadena `investigate(ticker, ...)` →
  `generate_reports(result, ...)`, devolviendo la tupla `(result,
  report_paths)`.

### Parámetro `formats`

Ambas funciones aceptan un parámetro opcional `formats: Sequence[str]
| None`, con valores válidos `"markdown"` y `"html"`:

- **`formats=None` (por defecto):** genera **ambos** formatos, en el
  mismo orden `[markdown_path, html_path]` ya usado desde que estas
  funciones existen.
- **`formats=("markdown",)` / `("html",)`:** genera únicamente ese
  formato, devolviendo una lista de un solo elemento.
- **`formats=("html", "markdown")` (o cualquier orden):** el orden de
  salida de `generate_reports` sigue siendo `[markdown_path, html_path]`
  si ambos están presentes en `formats` — el orden de la lista de
  entrada no determina el orden de salida, solo qué formatos se
  incluyen.
- Un valor desconocido en `formats` o una lista vacía levantan
  `ValueError`.

## Obtención y normalización de la serie histórica (`fetch_raw_historical_data` / `fetch_and_normalize_historical`)

Siguen exactamente el mismo patrón de dos capas ya usado por
`fetch_raw_data`/`fetch_and_normalize` (Fase 1), aplicado a la variante
histórica:

- **`fetch_raw_historical_data(ticker, ...)`**: dispara la consulta al
  proveedor de datos fundamentales, pero invocando
  `fetch_historical(ticker, period=..., limit=...)` (ver
  `investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch_historical`)
  en vez de `fetch(ticker)`. Por defecto construye un
  `FMPFundamentalsProvider` (mismo proveedor ya elegido para el MVP),
  pero acepta un `provider` inyectado.
- **`fetch_and_normalize_historical(ticker, ...)`**: encadena
  `fetch_raw_historical_data(ticker, ...)` con
  `investmentops.data_layer.normalization.financial_statement_series_from_raw`,
  devolviendo un `FinancialStatementSeries` ya listo para el motor de
  análisis de evolución de ingresos y beneficios
  (`investmentops.analysis_engines.trends.assemble_trend_analysis`).

Ninguna de las dos captura `DataProviderError` ni `NormalizationError`:
las propagan tal cual, mismo criterio que `fetch_raw_data`/
`fetch_and_normalize`.

## Registro de la invocación del motor de evolución de ingresos y beneficios (`run_trend_analysis_engine`)

Cubre la tarea "Registrar la invocación de `assemble_trend_analysis` en
el flujo de análisis del orquestador, conforme a la decisión de
integración ya tomada, sin modificar los motores existentes" (TASKS.md,
Fase 3, "Orquestador"), sobre la decisión ya documentada en
`investmentops/core/TREND_INTEGRATION.md`.

`investmentops.analysis_engines.trends.TrendAnalysisResult` (a
diferencia de `AnalysisResult`, usado por los motores de salud
financiera y valoración) no lleva `provenance`: ese motor no invoca
ningún proveedor de IA, sus hallazgos se generan por plantilla
determinista. `TREND_INTEGRATION.md` decidió, para no tener que
modificar `AnalysisResult`/`ResearchResult` ni los consumidores ya
estables (`render_markdown`, `render_html`, `format_research_result`),
envolver el resultado del motor en un `AnalysisResult` normal con una
`AnalysisProvenance` **centinela** explícita:

- `ai_provider = "none"`
- `ai_model = "deterministic"`
- `generated_at`: el momento en que se ensambló *este* análisis (mismo
  criterio ya usado por los demás agentes).

Esta tarea implementa esa conversión (`_trend_analysis_result_to_analysis_result`)
y la pieza que "registra la invocación" del motor dentro del flujo de
análisis del orquestador (`run_trend_analysis_engine`), análoga en
espíritu a `analyze_financial_health`/`analyze_valuation` (calcula
→ produce resultado), pero encadenando en su lugar
`fetch_and_normalize_historical` (obtención + normalización de la serie)
→ `assemble_trend_analysis` (cálculo determinístico + síntesis de
tendencia, ya implementado en `investmentops.analysis_engines.trends`)
→ la conversión centinela.

`run_trend_analysis_engine` **no captura** ninguna excepción de las
piezas que invoca (`DataProviderError`, `NormalizationError`): las
propaga tal cual, mismo criterio ya aplicado por
`fetch_and_normalize`/`fetch_and_normalize_historical`. Incorporar su
resultado al `ResearchResult` ensamblado por `investigate`, con manejo
de fallos parciales (serie histórica no disponible, error de
normalización) sin detener el resto del flujo, es la tarea siguiente y
separada de esta misma sección de TASKS.md — esta tarea únicamente deja
lista y disponible la pieza que produce el `AnalysisResult` del motor de
tendencias, sin conectarla todavía a `investigate`/`ResearchResult`.

Esta tarea tampoco modifica `run_analysis_engines`, `analyze_financial_health`
ni `analyze_valuation`: ninguno de los motores existentes cambia.

Fuera de alcance de este módulo (aún):
- Completar `Company.name`/`sector`/`market` con datos reales: no hay
  hoy una fuente de datos que los provea (ver docstring de
  `assemble_research_result`).
- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): fuera de alcance.
- Incluir el resultado de `run_trend_analysis_engine` en el
  `ResearchResult` ensamblado por `investigate`, con manejo de fallos
  parciales: tarea separada y siguiente de esta misma sección de
  TASKS.md.
- La presentación de este resultado en los reportes Markdown/HTML: tarea
  separada y posterior (ver TASKS.md, Fase 3, "Reportes").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from investmentops.ai_providers import AgentProviderSelectionError, AIProviderError
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.financial_health import (
    AGENT_ID as FINANCIAL_HEALTH_AGENT_ID,
    analyze_financial_health,
)
from investmentops.analysis_engines.prompts import PromptError
from investmentops.analysis_engines.trends import (
    AGENT_ID as TREND_AGENT_ID,
    TrendAnalysisResult,
    assemble_trend_analysis,
)
from investmentops.analysis_engines.valuation import (
    AGENT_ID as VALUATION_AGENT_ID,
    analyze_valuation,
)
from investmentops.core.research_result import ResearchFailure, ResearchResult
from investmentops.data_layer.domain import Company
from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_from_raw,
    financial_statement_series_from_raw,
    market_data_from_raw,
)
from investmentops.data_providers.contracts import (
    DataProvider,
    DataProviderError,
    RawProviderData,
)
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider
from investmentops.reports import (
    render_html,
    render_markdown,
    save_html_report,
    save_markdown_report,
)

#: Formatos de reporte soportados por `generate_reports`/
#: `investigate_and_generate_reports`, en el orden en que deben aparecer
#: en la lista de rutas devuelta cuando se solicita más de uno. Añadir un
#: formato nuevo (ej. JSON, ver ROADMAP.md) implica sumar una entrada aquí
#: y su correspondiente rama en `generate_reports`, sin modificar el
#: orden ya establecido para markdown/html.
ALL_REPORT_FORMATS: tuple[str, ...] = ("markdown", "html")

#: Procedencia centinela usada para el `AnalysisResult` que envuelve el
#: resultado del motor de evolución de ingresos y beneficios (ver
#: "Registro de la invocación del motor..." en el docstring del módulo, y
#: la decisión completa en `investmentops/core/TREND_INTEGRATION.md`).
#: Etiqueta honestamente que esta interpretación NO fue generada por un
#: modelo de lenguaje, a diferencia de salud financiera/valoración.
TREND_ANALYSIS_AI_PROVIDER = "none"
TREND_ANALYSIS_AI_MODEL = "deterministic"


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


def fetch_raw_historical_data(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPFundamentalsProvider | None = None,
    period: str = "annual",
    limit: int = 5,
) -> RawProviderData:
    """Consulta al proveedor de datos fundamentales la serie histórica de `ticker`.

    Equivalente histórico de `fetch_raw_data`: en vez de invocar
    `DataProvider.fetch(ticker)` (un único corte, el más reciente),
    invoca `fetch_historical(ticker, period=..., limit=...)` (ver
    `investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch_historical`),
    que conserva varios periodos históricos.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se pasa
        tal cual al proveedor, que es quien valida/normaliza su formato.
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), usada para construir el
        proveedor por defecto si no se indica `provider` explícitamente.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco. Se ignora si `provider` ya se indica.
    provider:
        Proveedor de datos ya construido a usar en vez del proveedor por
        defecto. A diferencia de `fetch_raw_data` (que acepta cualquier
        `DataProvider`), aquí se requiere un objeto con un método
        `fetch_historical(ticker, period=..., limit=...)` — hoy solo
        `FMPFundamentalsProvider` lo implementa. Si no se indica, se
        construye un `FMPFundamentalsProvider`.
    period:
        Granularidad de los periodos a solicitar (``"annual"`` o
        ``"quarter"``), propagada tal cual a `fetch_historical`. Por
        defecto, ``"annual"``.
    limit:
        Número máximo de periodos históricos a solicitar, propagado tal
        cual a `fetch_historical`. Por defecto, ``5``.

    Returns
    -------
    RawProviderData
        Los datos crudos históricos obtenidos (varios periodos en
        `payload["income_statement"]`/`payload["balance_sheet_statement"]`,
        cada punto ya con su propia procedencia), junto con los
        metadatos de procedencia de la consulta completa.

    Raises
    ------
    DataProviderError
        Si el proveedor no responde, el ticker no existe, `period`/
        `limit` son inválidos, o la respuesta no se puede interpretar
        (ver `FMPFundamentalsProvider.fetch_historical`). Esta función no
        captura ni traduce esa excepción.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    data_provider = provider if provider is not None else FMPFundamentalsProvider(config=config)
    return data_provider.fetch_historical(ticker, period=period, limit=limit)


def fetch_and_normalize_historical(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPFundamentalsProvider | None = None,
    period: str = "annual",
    limit: int = 5,
) -> FinancialStatementSeries:
    """Consulta al proveedor de datos y normaliza la serie histórica de `ticker`.

    Equivalente histórico de `fetch_and_normalize`: encadena
    `fetch_raw_historical_data(ticker, ...)` con
    `investmentops.data_layer.normalization.financial_statement_series_from_raw`,
    devolviendo un `FinancialStatementSeries` (ver
    `investmentops.data_layer.FinancialStatementSeries`) listo para el
    motor de análisis de evolución de ingresos y beneficios
    (`investmentops.analysis_engines.trends.assemble_trend_analysis`).

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``).
    config:
        Configuración ya cargada, propagada a `fetch_raw_historical_data`.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco.
    provider:
        Proveedor de datos ya construido, propagado a
        `fetch_raw_historical_data`. Pensado sobre todo para pruebas.
    period:
        Granularidad de los periodos a solicitar, propagada tal cual a
        `fetch_raw_historical_data`.
    limit:
        Número máximo de periodos históricos a solicitar, propagado tal
        cual a `fetch_raw_historical_data`.

    Returns
    -------
    FinancialStatementSeries
        La serie normalizada de estados financieros, ordenada del
        periodo más reciente al más antiguo (mismo orden que ya entrega
        FMP y que ya asume `FinancialStatementSeries`).

    Raises
    ------
    DataProviderError
        Ver `fetch_raw_historical_data`.
    NormalizationError
        Si los datos crudos obtenidos no traen los campos imprescindibles
        para construir cada `FinancialStatement` de la serie (ver
        `financial_statement_series_from_raw`). Esta función no captura
        ni traduce esa excepción: el manejo de fallos parciales sin
        detener el resto del flujo es responsabilidad de quien integre
        esta pieza en `investigate` (tarea separada y siguiente de esta
        misma sección de TASKS.md), mismo criterio ya aplicado por
        `fetch_and_normalize` para el corte único.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    raw = fetch_raw_historical_data(
        ticker, config=config, provider=provider, period=period, limit=limit
    )
    return financial_statement_series_from_raw(raw)


def _trend_analysis_result_to_analysis_result(
    trend_result: TrendAnalysisResult,
    *,
    generated_at: datetime | None = None,
) -> AnalysisResult:
    """Convierte un `TrendAnalysisResult` en un `AnalysisResult` normal.

    Implementa el adaptador decidido en
    `investmentops/core/TREND_INTEGRATION.md`: el motor de evolución de
    ingresos y beneficios (`investmentops.analysis_engines.trends`) no
    invoca ningún proveedor de IA, por lo que su resultado
    (`TrendAnalysisResult`) no lleva `provenance`. Esta función lo
    envuelve en un `AnalysisResult` (el contrato común de
    `investmentops.analysis_engines.contracts`, ya usado por salud
    financiera y valoración) con una `AnalysisProvenance` **centinela**
    (`ai_provider="none"`, `ai_model="deterministic"`) que etiqueta
    honestamente que esta interpretación es determinística, no generada
    por un modelo de lenguaje.

    No modifica `TrendAnalysisResult` ni `AnalysisResult`/
    `AnalysisProvenance`: es puramente un adaptador entre ambos tipos ya
    existentes.

    Parameters
    ----------
    trend_result:
        El `TrendAnalysisResult` ya producido por
        `investmentops.analysis_engines.trends.assemble_trend_analysis`.
    generated_at:
        Momento en que se generó esta interpretación. Si no se indica,
        se usa el momento de la llamada (mismo criterio ya usado por
        `assemble_research_result` para su propio `generated_at`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: `trend_result.analysis_id` (siempre
          `TREND_AGENT_ID`, ``"trend_analysis"``).
        - `findings`, `supporting_metrics`, `limitations`: tomados
          directamente de `trend_result`, sin transformarlos.
        - `provenance`: `AnalysisProvenance(ai_provider="none",
          ai_model="deterministic", generated_at=...)`.
    """
    provenance = AnalysisProvenance(
        ai_provider=TREND_ANALYSIS_AI_PROVIDER,
        ai_model=TREND_ANALYSIS_AI_MODEL,
        generated_at=generated_at if generated_at is not None else datetime.now(timezone.utc),
    )

    return AnalysisResult(
        analysis_id=trend_result.analysis_id,
        findings=list(trend_result.findings),
        supporting_metrics=trend_result.supporting_metrics,
        limitations=list(trend_result.limitations),
        provenance=provenance,
    )


def run_trend_analysis_engine(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPFundamentalsProvider | None = None,
    period: str = "annual",
    limit: int = 5,
) -> AnalysisResult:
    """Registra la invocación del motor de evolución de ingresos y beneficios.

    Cubre la tarea "Registrar la invocación de `assemble_trend_analysis`
    en el flujo de análisis del orquestador, conforme a la decisión de
    integración ya tomada, sin modificar los motores existentes"
    (TASKS.md, Fase 3, "Orquestador").

    Encadena, para `ticker`:

    1. `fetch_and_normalize_historical(ticker, ...)`: obtiene y normaliza
       la serie histórica de estados financieros.
    2. `investmentops.analysis_engines.trends.assemble_trend_analysis(series)`:
       calcula la variación periodo a periodo y sintetiza la tendencia
       agregada de ingresos y beneficios (motor ya implementado, sin
       modificar).
    3. `_trend_analysis_result_to_analysis_result(...)`: envuelve ese
       resultado en un `AnalysisResult` con procedencia centinela (ver
       docstring de esa función y `TREND_INTEGRATION.md`).

    No modifica `run_analysis_engines`, `analyze_financial_health` ni
    `analyze_valuation`: ningún motor existente cambia. Tampoco se
    invoca todavía desde `investigate`/`assemble_research_result`: esa
    incorporación al `ResearchResult`, con manejo de fallos parciales
    (serie histórica no disponible, error de normalización) sin detener
    el resto del flujo, es la tarea siguiente y separada de esta misma
    sección de TASKS.md.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a analizar (ej. ``"AAPL"``).
    config:
        Configuración ya cargada, propagada a
        `fetch_and_normalize_historical`. Útil para pruebas, para no
        depender de un `config.local.toml` real en disco.
    provider:
        Proveedor de datos ya construido, propagado a
        `fetch_and_normalize_historical`. Pensado sobre todo para
        pruebas.
    period:
        Granularidad de los periodos a solicitar, propagada tal cual a
        `fetch_and_normalize_historical`. Por defecto, ``"annual"``.
    limit:
        Número máximo de periodos históricos a solicitar, propagado tal
        cual a `fetch_and_normalize_historical`. Por defecto, ``5``.

    Returns
    -------
    AnalysisResult
        El resultado del motor de evolución de ingresos y beneficios,
        ya envuelto en el contrato común (ver
        `_trend_analysis_result_to_analysis_result`).

    Raises
    ------
    DataProviderError
        Ver `fetch_and_normalize_historical`. Esta función no captura ni
        traduce esa excepción: el manejo de fallos parciales queda para
        la tarea siguiente de integración en `investigate`.
    NormalizationError
        Ver `fetch_and_normalize_historical`.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    series = fetch_and_normalize_historical(
        ticker, config=config, provider=provider, period=period, limit=limit
    )
    trend_result = assemble_trend_analysis(series)
    return _trend_analysis_result_to_analysis_result(trend_result)


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
    agente por separado en vez de usar esta función. No incluye el motor
    de evolución de ingresos y beneficios (`run_trend_analysis_engine`):
    su incorporación al flujo de análisis es la tarea siguiente y
    separada de TASKS.md, Fase 3, "Orquestador".
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
    parcial de una fuente o un agente concretos. Esta función todavía no
    invoca `run_trend_analysis_engine`: esa integración es la tarea
    siguiente y separada de TASKS.md, Fase 3, "Orquestador".
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


def generate_reports(
    result: ResearchResult,
    *,
    output_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
    formats: Sequence[str] | None = None,
) -> list[Path]:
    """Genera y guarda los reportes de un `ResearchResult`, en el/los
    formato(s) solicitado(s).

    Reutiliza, sin modificarlas, las funciones ya implementadas en Fase 2
    (`investmentops.reports`): `render_markdown`/`save_markdown_report` y
    `render_html`/`save_html_report`. Esta función es solo el punto de
    conexión entre el orquestador y los generadores de reporte ya
    existentes (ver docstring del módulo, "Generación de reportes").

    Parameters
    ----------
    result:
        El `ResearchResult` ya ensamblado (típicamente la salida de
        `investigate(...)`), a partir del cual se renderizan los reportes.
    output_dir:
        Ruta al directorio donde guardar los reportes. Si no se indica,
        cada generador la resuelve por su cuenta desde `config.local.toml`
        (sección `[output].output_dir`, ver CONFIGURATION.md), igual
        criterio ya usado por `save_markdown_report`/`save_html_report`.
    config:
        Configuración ya cargada, propagada a los generadores que se
        invoquen. Útil para pruebas, para no depender de un
        `config.local.toml` real en disco.
    formats:
        Qué formato(s) generar: cualquier subconjunto no vacío de
        ``{"markdown", "html"}``. Si no se indica (``None``, valor por
        defecto), se generan **ambos**, preservando el comportamiento
        histórico de esta función. El orden de la lista devuelta siempre
        es `[markdown_path, html_path]` cuando ambos formatos están
        presentes, sin importar el orden en que aparezcan en `formats`.

    Returns
    -------
    list[Path]
        Las rutas de los archivos escritos, uno por formato solicitado,
        en el orden fijo `[markdown_path, html_path]` cuando ambos se
        piden (o una lista de un solo elemento si solo se pide uno).

    Raises
    ------
    ValueError
        Si `formats` es una secuencia vacía, o si contiene algún valor
        que no sea `"markdown"` ni `"html"`.
    ReportError
        Si el ticker de `result.company` está vacío, o si ocurre un
        fallo de E/S al crear el directorio de salida o al escribir
        alguno de los archivos (ver
        `investmentops.reports.markdown.ReportError`).
    ConfigError
        Si `output_dir` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    selected_formats = tuple(formats) if formats is not None else ALL_REPORT_FORMATS

    if not selected_formats:
        raise ValueError(
            "Debe indicarse al menos un formato de reporte "
            f"(valores admitidos: {', '.join(ALL_REPORT_FORMATS)})."
        )

    unknown_formats = sorted(set(selected_formats) - set(ALL_REPORT_FORMATS))
    if unknown_formats:
        raise ValueError(
            f"Formato(s) de reporte desconocido(s): {unknown_formats}. "
            f"Valores admitidos: {', '.join(ALL_REPORT_FORMATS)}."
        )

    ticker = result.company.ticker
    paths: list[Path] = []

    if "markdown" in selected_formats:
        markdown_content = render_markdown(result)
        paths.append(
            save_markdown_report(ticker, markdown_content, output_dir=output_dir, config=config)
        )

    if "html" in selected_formats:
        html_content = render_html(result)
        paths.append(
            save_html_report(ticker, html_content, output_dir=output_dir, config=config)
        )

    return paths


def investigate_and_generate_reports(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
    output_dir: str | Path | None = None,
    formats: Sequence[str] | None = None,
) -> tuple[ResearchResult, list[Path]]:
    """Ejecuta `investigate(...)` y genera+guarda sus reportes.

    Función de conveniencia que encadena `investigate(ticker, ...)` con
    `generate_reports(result, ...)`, pensada para que la use la CLI (ver
    `investmentops.cli.dispatch`). No modifica el comportamiento de
    `investigate(...)` en sí mismo: quien ya depende de esa función (ej.
    otras llamadas a `investigate` en este mismo módulo) sigue recibiendo
    únicamente un `ResearchResult`, sin efectos secundarios de E/S.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a investigar, propagado tal cual a
        `investigate(...)`.
    config:
        Configuración ya cargada, propagada tanto a `investigate(...)`
        como a `generate_reports(...)`.
    provider:
        Proveedor de datos ya construido, propagado a `investigate(...)`.
    output_dir:
        Ruta al directorio donde guardar los reportes, propagada a
        `generate_reports(...)`.
    formats:
        Qué formato(s) generar, propagado tal cual a `generate_reports(...)`
        (ver ese docstring). Si no se indica, se generan ambos formatos
        (comportamiento histórico, sin cambios para llamadores existentes).

    Returns
    -------
    tuple[ResearchResult, list[Path]]
        El `ResearchResult` ensamblado (incluyendo cualquier
        `ResearchFailure` parcial, ver `investigate`) y las rutas de los
        reportes generados a partir de él (ver `generate_reports`).

    Raises
    ------
    ValueError, ReportError, ConfigError
        Ver `generate_reports`. `investigate(...)` en sí mismo no deja
        escapar `DataProviderError`, `NormalizationError`, `PromptError`,
        `AgentProviderSelectionError` ni `AIProviderError` (ver su propio
        docstring).
    """
    result = investigate(ticker, config=config, provider=provider)
    report_paths = generate_reports(
        result, output_dir=output_dir, config=config, formats=formats
    )
    return result, report_paths