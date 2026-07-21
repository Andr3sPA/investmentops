# investmentops/core/orchestrator.py
"""Orquestador mínimo — disparo de la consulta al proveedor de datos, paso
de esos datos crudos a la capa de normalización, invocación secuencial de
los agentes de análisis, ensamblado del "Resultado de investigación"
final, manejo de fallos parciales sin detener el resto del flujo,
generación de reportes (Markdown/HTML) tras ensamblar ese resultado,
obtención/normalización de la serie histórica de ingresos y beneficios,
registro de la invocación del motor de evolución de ingresos y beneficios,
su inclusión en el "Resultado de investigación" ensamblado (Fase 3),
obtención/normalización de noticias recientes de una empresa, y registro
de la invocación del motor de noticias relevantes (Fase 4).

Cubre doce tareas:

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
  `_trend_analysis_result_to_analysis_result`, ya completada, ver
  PROGRESS.md).
- "Incluir el resultado de evolución de ingresos y beneficios en el
  `ResearchResult` ensamblado, incluyendo el manejo de fallos parciales
  (serie histórica no disponible, error de normalización) sin detener
  el resto del flujo, siguiendo el mismo criterio ya usado por
  `investigate` para los demás agentes." (`investigate` ahora también
  invoca `run_trend_analysis_engine`, ya completada, ver PROGRESS.md).

Fase 4, "Orquestador" (TASKS.md):
- "Registrar el nuevo proveedor de noticias sin modificar los
  proveedores existentes." (`fetch_raw_news_data`,
  `fetch_and_normalize_news`, ya completada, ver PROGRESS.md).
- "Registrar el nuevo motor de análisis sin modificar los motores
  existentes." (`run_news_relevance_engine`,
  `_news_relevance_result_to_analysis_result`, esta tarea). Sigue
  exactamente el mismo patrón ya usado por `run_trend_analysis_engine`/
  `_trend_analysis_result_to_analysis_result` (Fase 3):
  `investmentops.analysis_engines.news_relevance.NewsRelevanceResult`
  tampoco lleva `provenance` (este motor no invoca ningún proveedor de
  IA, ver docstring de `news_relevance.py`), por lo que se envuelve en
  un `AnalysisResult` normal con una `AnalysisProvenance` centinela
  (`ai_provider="none"`, `ai_model="deterministic"`) — mismo criterio ya
  documentado y justificado en `investmentops/core/TREND_INTEGRATION.md`
  para el motor de tendencias, reutilizado aquí sin necesidad de una
  nueva decisión de diseño (el problema y su solución ya son idénticos).
  `run_news_relevance_engine` encadena `fetch_and_normalize_news`
  (Fase 4, ya implementada) → `assemble_news_relevance_analysis`
  (Fase 4, ya implementada) → la conversión centinela. No modifica
  `run_analysis_engines`, `analyze_financial_health`, `analyze_valuation`
  ni `run_trend_analysis_engine`, y **todavía no se invoca desde
  `investigate`**: incorporar su resultado al `ResearchResult` ensamblado
  (con manejo de fallos parciales) es la tarea siguiente y separada de
  esta misma sección de `TASKS.md`.

Las funciones de Fase 1-3 viven en el mismo módulo porque son piezas
consecutivas del mismo pipeline descrito en ARCHITECTURE.md ("Resumen
del flujo de una investigación", pasos 3-8). Las de Fase 4 se suman al
mismo módulo por el mismo motivo.

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
3. **Motor de evolución de ingresos y beneficios** (ver "Inclusión del
   motor de tendencia" más abajo): se intenta a continuación, también en
   su propio `try/except` independiente, sin afectar a los dos agentes
   anteriores ni ser afectado por sus fallos.
4. **Ensamblado final**: se llama a `assemble_research_result(ticker,
   <resultados exitosos>, failures=<fallos capturados>)`, reutilizando
   la función ya existente sin modificarla.

`investigate` no reemplaza a `run_analysis_engines` ni a
`fetch_and_normalize`: ambas se mantienen sin cambios.

## Inclusión del motor de tendencia en `investigate`

Cubre la tarea "Incluir el resultado de evolución de ingresos y
beneficios en el `ResearchResult` ensamblado, incluyendo el manejo de
fallos parciales (serie histórica no disponible, error de
normalización) sin detener el resto del flujo, siguiendo el mismo
criterio ya usado por `investigate` para los demás agentes" (TASKS.md,
Fase 3, "Orquestador").

`investigate` ahora invoca también `run_trend_analysis_engine(ticker,
config=config, provider=provider)` (ya implementada en la tarea
anterior de esta misma sección), en un `try/except` independiente de los
dos ya existentes para salud financiera y valoración, capturando
`DataProviderError`/`NormalizationError` (las mismas excepciones que ya
puede levantar `fetch_and_normalize_historical`, encadenada dentro de
`run_trend_analysis_engine`) y traduciéndolas a
`ResearchFailure(stage="data_provider", identifier="trend_analysis",
reason=<mensaje>)`, sin detener el resto del flujo ya ensamblado.

### Por qué esta invocación es condicional a la capacidad del proveedor

El parámetro `provider` de `investigate` está tipado como `DataProvider`
(`investmentops.data_providers.contracts`), cuyo contrato solo exige un
método `fetch(ticker)`. `run_trend_analysis_engine`, en cambio, necesita
un proveedor que también exponga `fetch_historical(ticker, period=...,
limit=...)` (hoy, únicamente `FMPFundamentalsProvider` lo implementa).
No todo objeto que cumple `DataProvider` cumple también esa capacidad
adicional — de hecho, varios proveedores mínimos de prueba ya existentes
en el proyecto (ver `investmentops/tests/test_core_orchestrator.py`,
`test_cli_dispatch.py`, etc.) solo implementan `fetch`.

Para no romper ese uso ya establecido del contrato `DataProvider` (un
proveedor mínimo con solo `fetch` sigue siendo, por diseño, un
`DataProvider` válido, ver `investmentops/data_providers/contracts.py`),
`investigate` solo intenta el motor de tendencia cuando:

- **`provider is None`**: no se inyectó ningún proveedor, por lo que
  tanto el flujo principal como `run_trend_analysis_engine` construyen,
  cada uno por su cuenta, el mismo proveedor real por defecto
  (`FMPFundamentalsProvider`, que sí implementa `fetch_historical`).
- **`hasattr(provider, "fetch_historical")`**: el proveedor inyectado sí
  expone esa capacidad adicional (ej. `FMPFundamentalsProvider`, o un
  proveedor de prueba que implemente ambos métodos deliberadamente).

Si el proveedor inyectado **no** expone `fetch_historical`, `investigate`
simplemente **no incluye** ningún análisis de tendencia para esa
investigación, sin registrarlo como `ResearchFailure`: es una limitación
de capacidad del proveedor usado (una decisión de quien construye ese
proveedor de prueba/alternativo), no un fallo en tiempo de ejecución de
una consulta real. Esto es distinto de una `DataProviderError` real (ej.
el ticker no tiene datos históricos, o la fuente no respondió), que sí
se captura y se refleja como fallo parcial, tal como exige esta tarea.

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

`_trend_analysis_result_to_analysis_result` implementa esa conversión, y
`run_trend_analysis_engine` es la pieza que "registra la invocación" del
motor dentro del flujo de análisis del orquestador, análoga en espíritu
a `analyze_financial_health`/`analyze_valuation` (calcula → produce
resultado), pero encadenando en su lugar
`fetch_and_normalize_historical` (obtención + normalización de la serie)
→ `assemble_trend_analysis` (cálculo determinístico + síntesis de
tendencia, ya implementado en `investmentops.analysis_engines.trends`)
→ la conversión centinela.

`run_trend_analysis_engine` **no captura** ninguna excepción de las
piezas que invoca (`DataProviderError`, `NormalizationError`): las
propaga tal cual, mismo criterio ya aplicado por
`fetch_and_normalize`/`fetch_and_normalize_historical`. Es `investigate`
(ver "Inclusión del motor de tendencia en `investigate`" arriba) quien
captura esas excepciones para reflejarlas como `ResearchFailure` sin
detener el resto del flujo.

Esta tarea tampoco modifica `run_analysis_engines`, `analyze_financial_health`
ni `analyze_valuation`: ninguno de los motores existentes cambia.

## Obtención y normalización de noticias (`fetch_raw_news_data` / `fetch_and_normalize_news`)

Cubre la tarea "Registrar el nuevo proveedor de noticias sin modificar
los proveedores existentes" (TASKS.md, Fase 4, "Orquestador"). Sigue
exactamente el mismo patrón de dos capas ya usado por
`fetch_raw_data`/`fetch_and_normalize` (Fase 1) y
`fetch_raw_historical_data`/`fetch_and_normalize_historical` (Fase 3):

- **`fetch_raw_news_data(ticker, ...)`**: dispara la consulta al
  proveedor de noticias (ver
  `investmentops.data_providers.news.FMPNewsProvider.fetch`). Por
  defecto construye un `FMPNewsProvider` (el proveedor ya elegido en
  `investmentops/data_providers/NEWS_PROVIDER.md`), pero acepta un
  `provider` inyectado para pruebas.
- **`fetch_and_normalize_news(ticker, ...)`**: encadena
  `fetch_raw_news_data(ticker, ...)` con
  `investmentops.data_layer.normalization.news_from_raw`, devolviendo
  una `list[News]` (lista vacía si la empresa no tiene noticias
  recientes: no es un error, ver `investmentops.data_providers.news`).

Ninguna de las dos captura `DataProviderError` ni `NormalizationError`:
las propagan tal cual, mismo criterio ya aplicado por las funciones
equivalentes de Fase 1 y Fase 3. No se modifica `FMPFundamentalsProvider`
ni ninguna función ya existente de este módulo: es un cambio puramente
aditivo.

## Registro de la invocación del motor de noticias relevantes (`run_news_relevance_engine`, esta tarea)

Cubre la tarea "Registrar el nuevo motor de análisis sin modificar los
motores existentes" (TASKS.md, Fase 4, "Orquestador"). Mismo problema y
misma solución ya resueltos para el motor de tendencias (ver "Registro
de la invocación del motor de evolución de ingresos y beneficios"
arriba y `investmentops/core/TREND_INTEGRATION.md`, cuya justificación
aplica aquí sin cambios): `investmentops.analysis_engines.news_relevance.NewsRelevanceResult`
tampoco lleva `provenance` (este motor no invoca ningún proveedor de
IA), por lo que se envuelve en un `AnalysisResult` normal con la misma
procedencia centinela (`ai_provider="none"`, `ai_model="deterministic"`).

`_news_relevance_result_to_analysis_result` implementa esa conversión
(misma forma que `_trend_analysis_result_to_analysis_result`), y
`run_news_relevance_engine` "registra la invocación" del motor,
encadenando `fetch_and_normalize_news` (obtención + normalización de las
noticias, ya implementada) → `assemble_news_relevance_analysis` (filtrado
por ventana de tiempo + resumen breve + ensamblado, ya implementado en
`investmentops.analysis_engines.news_relevance`) → la conversión
centinela.

`run_news_relevance_engine` **no captura** ninguna excepción de las
piezas que invoca (`DataProviderError`, `NormalizationError`): las
propaga tal cual, mismo criterio ya aplicado por `run_trend_analysis_engine`.
**Todavía no se invoca desde `investigate`**: incorporar su resultado al
`ResearchResult` ensamblado, con manejo de fallos parciales, es la tarea
siguiente y separada de esta misma sección de `TASKS.md` ("Incluir el
nuevo resultado en el 'Resultado de investigación'").

Esta tarea no modifica `run_analysis_engines`, `analyze_financial_health`,
`analyze_valuation` ni `run_trend_analysis_engine`: ningún motor
existente cambia.

Fuera de alcance de este módulo (aún):
- Completar `Company.name`/`sector`/`market` con datos reales: no hay
  hoy una fuente de datos que los provea (ver docstring de
  `assemble_research_result`).
- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): fuera de alcance.
- La presentación del resultado de tendencia o de noticias relevantes
  en los reportes Markdown/HTML: tareas separadas y posteriores (ver
  TASKS.md, Fase 3/Fase 4, "Reportes").
- Incluir el resultado del motor de noticias relevantes en
  `ResearchResult` (vía `investigate`): tarea separada y siguiente de
  "Fase 4 > Orquestador" (ver TASKS.md).
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
from investmentops.analysis_engines.news_relevance import (
    AGENT_ID as NEWS_RELEVANCE_AGENT_ID,
    DEFAULT_RELEVANCE_WINDOW_DAYS,
    DEFAULT_SUMMARY_MAX_LENGTH,
    NewsRelevanceResult,
    assemble_news_relevance_analysis,
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
from investmentops.data_layer.news import News
from investmentops.data_layer.normalization import (
    NormalizationError,
    financial_statement_from_raw,
    financial_statement_series_from_raw,
    market_data_from_raw,
    news_from_raw,
)
from investmentops.data_providers.contracts import (
    DataProvider,
    DataProviderError,
    RawProviderData,
)
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider
from investmentops.data_providers.news import FMPNewsProvider
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

#: Procedencia centinela usada para el `AnalysisResult` que envuelve el
#: resultado del motor de noticias relevantes (ver "Registro de la
#: invocación del motor de noticias relevantes" en el docstring del
#: módulo). Mismos valores y misma justificación que
#: `TREND_ANALYSIS_AI_PROVIDER`/`TREND_ANALYSIS_AI_MODEL`: este motor
#: tampoco invoca ningún proveedor de IA.
NEWS_RELEVANCE_AI_PROVIDER = "none"
NEWS_RELEVANCE_AI_MODEL = "deterministic"


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
        detener el resto del flujo es responsabilidad de `investigate`
        (ver docstring del módulo).
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    raw = fetch_raw_historical_data(
        ticker, config=config, provider=provider, period=period, limit=limit
    )
    return financial_statement_series_from_raw(raw)


def fetch_raw_news_data(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPNewsProvider | None = None,
) -> RawProviderData:
    """Consulta al proveedor de noticias (Fase 4) para `ticker`.

    Análoga a `fetch_raw_data` (Fase 1) y `fetch_raw_historical_data`
    (Fase 3), aplicada al proveedor de noticias registrado en esta tarea
    (TASKS.md, Fase 4, "Orquestador" > "Registrar el nuevo proveedor de
    noticias sin modificar los proveedores existentes"): el orquestador
    aprende a invocar `FMPNewsProvider.fetch(ticker)` sin tocar
    `FMPFundamentalsProvider` ni ninguna de las funciones ya existentes
    de este módulo, un cambio puramente aditivo (ver ARCHITECTURE.md,
    "Extensibilidad sin reescritura").

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se pasa
        tal cual al proveedor, que es quien valida/normaliza su formato
        (ver `FMPNewsProvider.fetch`).
    config:
        Configuración ya cargada, usada para construir el proveedor por
        defecto si no se indica `provider` explícitamente. Útil para
        pruebas, para no depender de un `config.local.toml` real en
        disco. Se ignora si `provider` ya se indica.
    provider:
        Proveedor de noticias ya construido a usar en vez del proveedor
        por defecto. Si no se indica, se construye un `FMPNewsProvider`
        (el proveedor ya elegido para noticias, ver
        `investmentops/data_providers/NEWS_PROVIDER.md`).

    Returns
    -------
    RawProviderData
        Los datos crudos de noticias obtenidos (lista de noticias, cada
        una ya con su propia procedencia), junto con los metadatos de
        procedencia de la consulta completa.

    Raises
    ------
    DataProviderError
        Si el proveedor no responde, el ticker está vacío, o la
        respuesta no tiene la forma esperada (ver `FMPNewsProvider.fetch`).
        Esta función no captura ni traduce esa excepción.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    news_provider = provider if provider is not None else FMPNewsProvider(config=config)
    return news_provider.fetch(ticker)


def fetch_and_normalize_news(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPNewsProvider | None = None,
) -> list[News]:
    """Consulta al proveedor de noticias y normaliza el resultado para `ticker`.

    Encadena `fetch_raw_news_data(ticker, ...)` con
    `investmentops.data_layer.normalization.news_from_raw`, mismo patrón
    de dos capas ya usado por `fetch_and_normalize`/
    `fetch_and_normalize_historical`.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar.
    config:
        Configuración ya cargada, propagada a `fetch_raw_news_data`.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco.
    provider:
        Proveedor de noticias ya construido, propagado a
        `fetch_raw_news_data`. Pensado sobre todo para pruebas.

    Returns
    -------
    list[News]
        Las noticias normalizadas de la empresa, en el mismo orden en
        que las entrega el proveedor. Lista vacía si la empresa no tiene
        noticias recientes (no es un error, ver
        `investmentops.data_providers.news`).

    Raises
    ------
    DataProviderError
        Ver `fetch_raw_news_data`.
    NormalizationError
        Si alguna noticia cruda no trae los campos imprescindibles o su
        fecha de publicación no es interpretable (ver
        `investmentops.data_layer.normalization.news_from_raw`). Esta
        función no captura ni traduce esa excepción: el manejo de
        fallos parciales sin detener el resto del flujo queda para una
        tarea separada y posterior de esta misma sección (ver TASKS.md,
        Fase 4, "Orquestador").
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    raw = fetch_raw_news_data(ticker, config=config, provider=provider)
    return news_from_raw(raw)


def _news_relevance_result_to_analysis_result(
    news_result: NewsRelevanceResult,
    *,
    generated_at: datetime | None = None,
) -> AnalysisResult:
    """Convierte un `NewsRelevanceResult` en un `AnalysisResult` normal.

    Mismo adaptador ya usado por `_trend_analysis_result_to_analysis_result`
    para el motor de tendencias (ver ese docstring y
    `investmentops/core/TREND_INTEGRATION.md` para la justificación
    completa, reutilizada aquí sin cambios): el motor de noticias
    relevantes (`investmentops.analysis_engines.news_relevance`) tampoco
    invoca ningún proveedor de IA, por lo que su resultado
    (`NewsRelevanceResult`) no lleva `provenance`. Esta función lo
    envuelve en un `AnalysisResult` con una `AnalysisProvenance`
    **centinela** (`ai_provider="none"`, `ai_model="deterministic"`).

    No modifica `NewsRelevanceResult` ni `AnalysisResult`/
    `AnalysisProvenance`: es puramente un adaptador entre ambos tipos ya
    existentes.

    Parameters
    ----------
    news_result:
        El `NewsRelevanceResult` ya producido por
        `investmentops.analysis_engines.news_relevance.assemble_news_relevance_analysis`.
    generated_at:
        Momento en que se generó esta interpretación. Si no se indica,
        se usa el momento de la llamada (mismo criterio ya usado por
        `_trend_analysis_result_to_analysis_result`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: `news_result.analysis_id` (siempre
          `NEWS_RELEVANCE_AGENT_ID`, ``"news_relevance"``).
        - `findings`, `supporting_metrics`, `limitations`: tomados
          directamente de `news_result`, sin transformarlos.
        - `provenance`: `AnalysisProvenance(ai_provider="none",
          ai_model="deterministic", generated_at=...)`.
    """
    provenance = AnalysisProvenance(
        ai_provider=NEWS_RELEVANCE_AI_PROVIDER,
        ai_model=NEWS_RELEVANCE_AI_MODEL,
        generated_at=generated_at if generated_at is not None else datetime.now(timezone.utc),
    )

    return AnalysisResult(
        analysis_id=news_result.analysis_id,
        findings=list(news_result.findings),
        supporting_metrics=news_result.supporting_metrics,
        limitations=list(news_result.limitations),
        provenance=provenance,
    )


def run_news_relevance_engine(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: FMPNewsProvider | None = None,
    days: int = DEFAULT_RELEVANCE_WINDOW_DAYS,
    now: datetime | None = None,
    summary_max_length: int = DEFAULT_SUMMARY_MAX_LENGTH,
) -> AnalysisResult:
    """Registra la invocación del motor de noticias relevantes.

    Encadena, para `ticker`:

    1. `fetch_and_normalize_news(ticker, ...)`: obtiene y normaliza las
       noticias recientes de la empresa.
    2. `investmentops.analysis_engines.news_relevance.assemble_news_relevance_analysis(...)`:
       filtra por ventana de tiempo reciente, selecciona un resumen breve
       por noticia relevante, y ensambla el resultado del motor (ya
       implementado, sin modificar).
    3. `_news_relevance_result_to_analysis_result(...)`: envuelve ese
       resultado en un `AnalysisResult` con procedencia centinela (ver
       docstring de esa función).

    No modifica `run_analysis_engines`, `analyze_financial_health`,
    `analyze_valuation` ni `run_trend_analysis_engine`: ningún motor
    existente cambia.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a analizar (ej. ``"AAPL"``).
    config:
        Configuración ya cargada, propagada a `fetch_and_normalize_news`.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco.
    provider:
        Proveedor de noticias ya construido, propagado a
        `fetch_and_normalize_news`. Pensado sobre todo para pruebas.
    days:
        Tamaño de la ventana de relevancia, en días, propagado tal cual a
        `assemble_news_relevance_analysis`. Por defecto,
        `DEFAULT_RELEVANCE_WINDOW_DAYS` (7).
    now:
        Momento de referencia contra el que se calcula la ventana,
        propagado tal cual a `assemble_news_relevance_analysis`. Si no se
        indica, se usa el reloj real. Pensado sobre todo para pruebas.
    summary_max_length:
        Longitud máxima del resumen breve de cada noticia relevante,
        propagada tal cual a `assemble_news_relevance_analysis`. Por
        defecto, `DEFAULT_SUMMARY_MAX_LENGTH` (280).

    Returns
    -------
    AnalysisResult
        El resultado del motor de noticias relevantes, ya envuelto en el
        contrato común (ver `_news_relevance_result_to_analysis_result`).

    Raises
    ------
    DataProviderError
        Ver `fetch_and_normalize_news`. Esta función no captura ni
        traduce esa excepción: el manejo de fallos parciales queda para
        una tarea separada y posterior de esta misma sección (ver
        TASKS.md, Fase 4, "Orquestador").
    NormalizationError
        Ver `fetch_and_normalize_news`.
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    news_items = fetch_and_normalize_news(ticker, config=config, provider=provider)
    news_result = assemble_news_relevance_analysis(
        news_items, days=days, now=now, summary_max_length=summary_max_length
    )
    return _news_relevance_result_to_analysis_result(news_result)


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
    `analyze_valuation`: ningún motor existente cambia.

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
        traduce esa excepción: el manejo de fallos parciales es
        responsabilidad de `investigate` (ver docstring del módulo).
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
    de evolución de ingresos y beneficios (`run_trend_analysis_engine`)
    ni el de noticias relevantes (`run_news_relevance_engine`): ninguno
    de los dos se invoca desde esta función (ver docstring del módulo).
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

    Ver el docstring del módulo, secciones "Manejo de fallos parciales
    (`investigate`)" e "Inclusión del motor de tendencia en
    `investigate`", para la explicación completa de las etapas
    (consulta+normalización, agentes por separado, motor de tendencia,
    ensamblado) y de por qué un fallo en la primera etapa impide
    continuar (ningún agente tiene datos con los que trabajar) mientras
    que un fallo en un agente o en el motor de tendencia no impide que
    los demás se ejecuten.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a investigar (ej. ``"AAPL"``).
    config:
        Configuración ya cargada, propagada a `fetch_and_normalize`, a
        cada agente de análisis y al motor de tendencia. Útil para
        pruebas, para no depender de un `config.local.toml` real en
        disco.
    provider:
        Proveedor de datos ya construido, propagado a
        `fetch_and_normalize`. Si además expone `fetch_historical` (o si
        no se indica ninguno), también se propaga al motor de evolución
        de ingresos y beneficios (ver "Inclusión del motor de tendencia
        en `investigate`" en el docstring del módulo); si no la expone,
        el motor de tendencia simplemente no se intenta para esta
        investigación.

    Returns
    -------
    ResearchResult
        - Si `fetch_and_normalize` falla (`DataProviderError` o
          `NormalizationError`): `analysis_results=[]` y un único
          `ResearchFailure(stage="data_provider", identifier=<ticker
          normalizado>, reason=<mensaje del error>)`.
        - Si la normalización tiene éxito: `analysis_results` contiene
          los resultados de los agentes/motores que sí completaron su
          análisis (salud financiera, valoración, y evolución de
          ingresos/beneficios cuando el proveedor lo permite), en ese
          orden, y `failures` contiene un
          `ResearchFailure(stage="analysis_engine", identifier=<analysis_id>,
          ...)` por cada agente que falló (`PromptError`,
          `AgentProviderSelectionError` o `AIProviderError`), o un
          `ResearchFailure(stage="data_provider", identifier="trend_analysis",
          ...)` si el motor de tendencia falló (`DataProviderError` o
          `NormalizationError` al obtener/normalizar la serie histórica).

    Notes
    -----
    Esta función nunca deja escapar `DataProviderError`,
    `NormalizationError`, `PromptError`, `AgentProviderSelectionError` ni
    `AIProviderError`: todas se capturan y se traducen a
    `ResearchFailure`. Otras excepciones (ej. `ConfigError` si no se
    puede cargar `config.local.toml` en absoluto) sí se propagan, ya que
    representan un problema de configuración del entorno, no un fallo
    parcial de una fuente o un agente concretos. El motor de noticias
    relevantes (`run_news_relevance_engine`) todavía **no** se invoca
    desde esta función (ver docstring del módulo, "Registro de la
    invocación del motor de noticias relevantes"): esa incorporación es
    una tarea separada y posterior de la misma sección de `TASKS.md`.
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

    # Motor de evolución de ingresos y beneficios (Fase 3): solo se intenta
    # si el proveedor inyectado expone `fetch_historical` (o si no se
    # inyectó ninguno, en cuyo caso `run_trend_analysis_engine` construye
    # su propio `FMPFundamentalsProvider` por defecto, el mismo proveedor
    # real ya usado para el resto del flujo). Un proveedor de prueba
    # mínimo que solo cumple el contrato `DataProvider.fetch` (sin
    # `fetch_historical`) no rompe `investigate`: simplemente no se
    # incluye ningún análisis de tendencia para esa investigación, sin
    # registrarlo como fallo (ver "Inclusión del motor de tendencia en
    # investigate" en el docstring del módulo). Si el proveedor sí
    # soporta series históricas pero la consulta o la normalización
    # fallan (serie histórica no disponible para el ticker, datos
    # incompletos), se captura como
    # `ResearchFailure(stage="data_provider", identifier="trend_analysis")`,
    # sin detener el resto del flujo ya ensamblado.
    if provider is None or hasattr(provider, "fetch_historical"):
        try:
            analysis_results.append(
                run_trend_analysis_engine(ticker, config=config, provider=provider)
            )
        except (DataProviderError, NormalizationError) as exc:
            failures.append(
                ResearchFailure(
                    stage="data_provider",
                    identifier=TREND_AGENT_ID,
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