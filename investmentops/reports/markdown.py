# investmentops/reports/markdown.py
# investmentops/reports/markdown.py
"""Generador de reportes en Markdown.

Cubre, hasta ahora, diez tareas de TASKS.md, Fase 2 ("Generador Markdown"),
Fase 3 ("Reportes"), Fase 4 ("Reportes") y Fase 5 ("Reportes"):

- "Implementar la plantilla base de reporte en Markdown (encabezados,
  secciones vacías)." (ya completada, ver PROGRESS.md).
- "Implementar el volcado de los hallazgos de salud financiera en la
  sección correspondiente." (ya completada, ver PROGRESS.md).
- "Implementar el volcado de los hallazgos de valoración en la sección
  correspondiente." (ya completada, ver PROGRESS.md).
- "Implementar la sección de fuentes/procedencia (qué proveedor, qué
  fecha) al final del reporte." (ya completada, ver PROGRESS.md).
- "Implementar el guardado del archivo Markdown generado en una ruta
  local configurable." (ya completada, ver PROGRESS.md).
- "Añadir la sección 'Evolución de ingresos y beneficios' a la plantilla
  Markdown, conforme al formato ya decidido." (ya completada, ver
  PROGRESS.md).
- "Añadir la sección 'Noticias recientes relevantes' a la plantilla
  Markdown." (ya completada, ver PROGRESS.md).
- "Añadir la sección 'Comparables del sector' a la plantilla Markdown."
  (ya completada, ver PROGRESS.md).
- "Adaptar el generador Markdown para soportar un reporte de comparación
  (varias empresas) además del reporte individual." (esta tarea).

## Dónde vive la procedencia de IA

`investmentops/reports/REPORT_SECTIONS.md` ya fija, para cada sección de
análisis ("Salud financiera", "Valoración"), un orden de cuatro partes:
hallazgos → métricas de soporte → limitaciones → **procedencia de la
interpretación de IA** (`provenance`: proveedor y modelo). Esta tarea
implementa exactamente esa cuarta parte, dentro de `_render_analysis_body`
(reutilizada, sin cambios de firma, por ambas secciones), en vez de
introducir una sección nueva y separada al final del documento: el título
de la tarea en `TASKS.md` ("al final del reporte") se satisface en el
sentido de "al final de cada bloque de análisis", que es el diseño ya
documentado y más específico de `REPORT_SECTIONS.md`.

Además del proveedor y modelo (`ai_provider`, `ai_model`), se incluye la
fecha de generación (`generated_at`), conforme a lo que pide literalmente
la tarea en `TASKS.md` ("qué proveedor, qué fecha"): `AnalysisProvenance`
ya expone ese dato y no hay razón para omitirlo del reporte.

Si el agente correspondiente no completó su análisis, la sección sigue
sin ningún contenido (ni hallazgos, ni métricas, ni procedencia): mismo
comportamiento ya usado en las tareas anteriores.

## Sección "Evolución de ingresos y beneficios"

Cubre la tarea "Añadir la sección 'Evolución de ingresos y beneficios' a
la plantilla Markdown, conforme al formato ya decidido" (TASKS.md, Fase
3, "Reportes"), sobre el formato ya fijado en
`investmentops/reports/TREND_PRESENTATION.md`.

`_find_analysis` (ya generalizada, no acoplada a ningún `analysis_id`
concreto) ahora también se usa para buscar, dentro de
`ResearchResult.analysis_results`, el `AnalysisResult` con
`analysis_id == "trend_analysis"` (ver
`investmentops.analysis_engines.trends.AGENT_ID` y su conversión en
`investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`).
Este resultado sigue siendo un `AnalysisResult` normal (con una
`AnalysisProvenance` centinela, `ai_provider="none"`,
`ai_model="deterministic"`, ver `TREND_INTEGRATION.md`), por lo que no
requiere ningún tipo ni contrato nuevo.

A diferencia de "Salud financiera"/"Valoración" (que vuelcan
`supporting_metrics` como una lista plana `- clave: valor`), esta
sección reemplaza esa lista por una **tabla Markdown** para las dos
claves que son mapeos por periodo
(`revenue_growth_by_period`/`net_income_growth_by_period`, ver
`TREND_PRESENTATION.md`, "Decisión: tabla simple, una fila por
periodo").

Orden dentro de la sección (mismo orden fijado en `TREND_PRESENTATION.md`):
hallazgos → tabla (omitida si ambos mapeos están vacíos) → limitaciones →
procedencia.

## Sección "Noticias recientes relevantes"

Cubre la tarea "Añadir la sección 'Noticias recientes relevantes' a la
plantilla Markdown" (TASKS.md, Fase 4, "Reportes"). A diferencia de la
sección de tendencia, `TASKS.md` no desglosó una tarea de diseño previa
y separada para el formato de esta sección (solo existen las dos tareas
de implementación, Markdown y HTML); la decisión de formato se toma aquí
mismo, documentada en este docstring.

`NEWS_RELEVANCE_AGENT_ID` (``"news_relevance"``, el mismo identificador
usado en `investmentops.analysis_engines.news_relevance.AGENT_ID` y
propagado tal cual por
`investmentops.core.orchestrator._news_relevance_result_to_analysis_result`
al convertir su resultado a `AnalysisResult`) se reutiliza junto con
`_find_analysis` (ya genérica) para localizar el `AnalysisResult`
correspondiente. Es un `AnalysisResult` normal, con una
`AnalysisProvenance` centinela (`ai_provider="none"`,
`ai_model="deterministic"`, mismo criterio ya justificado en
`TREND_INTEGRATION.md` y reutilizado sin una nueva decisión de diseño
para este motor).

`supporting_metrics["relevant_news"]` es una lista de dicts (`title`,
`summary`, `source`, `published_at`, `url`), no un mapeo de escalares
por periodo (a diferencia de la tabla de tendencia) ni un puñado de
escalares sueltos (a diferencia de salud financiera/valoración): cada
noticia trae demasiado texto libre (título + resumen + fuente + fecha +
URL) para caber legiblemente en una fila de tabla. Por eso esta sección
usa una **lista Markdown**, un ítem por noticia relevante:

    - **<título>** (<fuente>, <fecha ISO 8601>): <resumen> ([Leer más](<url>))

- Un ítem por elemento de `relevant_news`, en el mismo orden en que ya
  vienen (preservado desde `filter_relevant_news`, ver
  `investmentops.analysis_engines.news_relevance`).
- La lista se omite por completo si `relevant_news` está vacía (ninguna
  noticia relevante, o ninguna noticia en absoluto): en ese caso basta
  con el hallazgo ya generado por `_describe_relevant_news_count`
  ("No se encontraron noticias recientes relevantes en los últimos N
  día(s).").
- Los `findings` (un único hallazgo con la cantidad de noticias
  encontradas) y la procedencia (línea "Generado por: ...") reutilizan
  exactamente el mismo formato de texto ya usado por las demás
  secciones.

Orden dentro de la sección: hallazgos → lista de noticias relevantes
(omitida si está vacía) → limitaciones → procedencia.

## Sección "Comparables del sector"

Cubre la tarea "Añadir la sección 'Comparables del sector' a la
plantilla Markdown" (TASKS.md, Fase 5, "Reportes"). Mismo criterio que
"Noticias recientes relevantes": `TASKS.md` no desglosó una tarea de
diseño separada para el formato de esta sección; la decisión se toma
aquí mismo.

`COMPARABLES_AGENT_ID` (``"comparables"``, el mismo identificador usado
en `investmentops.analysis_engines.comparables.AGENT_ID` y propagado tal
cual por
`investmentops.core.orchestrator._comparables_analysis_result_to_analysis_result`
al convertir su resultado a `AnalysisResult`) se reutiliza junto con
`_find_analysis` (ya genérica) para localizar el `AnalysisResult`
correspondiente. Es un `AnalysisResult` normal, con una
`AnalysisProvenance` centinela (`ai_provider="none"`,
`ai_model="deterministic"`, mismo criterio ya usado por los motores de
tendencia y noticias relevantes: este motor tampoco invoca ningún
proveedor de IA, ver `investmentops.analysis_engines.comparables`, "Por
qué no se usa AnalysisResult/AnalysisProvenance").

`supporting_metrics` de este motor tiene una forma distinta a las demás
secciones: `{"company": {...}, "comparisons": {...}}` (ver
`investmentops.analysis_engines.comparables.assemble_comparables_analysis`).
Esta sección la vuelca en dos partes:

1. **Métricas de la empresa** (`supporting_metrics["company"]`, sin la
   clave `"ticker"`): un puñado de escalares (`net_margin`,
   `debt_to_revenue`, `price_to_earnings`, `price_to_sales`), volcados
   como lista plana `- clave: valor`, mismo formato ya usado por "Salud
   financiera"/"Valoración" — a diferencia de la tendencia (que no
   repite su agregado escalar porque ya está en el texto de los
   hallazgos), aquí sí aporta información nueva: el valor concreto de
   cada métrica de la empresa investigada, que los hallazgos no
   detallan explícitamente (solo narran cuántos pares quedan por
   encima/debajo).
2. **Tabla comparativa** (`supporting_metrics["comparisons"]`, un mapeo
   de nombre de métrica a una lista de comparaciones por par): se
   combina en una única tabla Markdown, una fila por combinación
   (métrica, par), mismo criterio de "tabla en vez de lista plana para
   datos multidimensionales" ya aplicado por la tabla de variación
   periodo a periodo de tendencia:
    Métrica     | Par  | Valor empresa | Valor par | Posición
    ------------+------+---------------+-----------+------------
    net_margin  | MSFT | 0.15          | 0.2       | por_debajo
Los valores `None` (métrica no calculable para la empresa o el par)
   y las posiciones `None` (no comparable) se muestran como `"—"`, mismo
   símbolo ya usado por la tabla de tendencia para variaciones no
   calculables. La tabla se omite por completo si `comparisons` no tiene
   ninguna entrada en ninguna métrica (la empresa no tiene pares, ver
   `investmentops.analysis_engines.comparables.NO_PEERS_LIMITATION`): en
   ese caso basta con el hallazgo ya generado y la limitación
   correspondiente.

Orden dentro de la sección: hallazgos → métricas de la empresa (omitida
si no hay ninguna) → tabla comparativa (omitida si no hay pares) →
limitaciones → procedencia.

## Reporte de comparación (varias empresas, esta tarea)

Cubre la tarea "Adaptar el generador Markdown para soportar un reporte
de comparación (varias empresas) además del reporte individual"
(TASKS.md, Fase 5, "Reportes"). No hay una tarea de diseño previa y
separada para el formato de este reporte; la decisión se toma aquí
mismo, mismo criterio ya aplicado a "Noticias recientes relevantes"/
"Comparables del sector".

### Decisión de formato: reutilizar `render_markdown` por empresa, anidado bajo un encabezado de comparación

`render_markdown_comparison(tickers, results)` no define una estructura
nueva y paralela para el reporte comparativo (ej. una tabla única con
todas las métricas de todas las empresas lado a lado). En su lugar,
reutiliza, sin modificarlo, `render_markdown` para producir el reporte
individual completo de cada empresa (`ResearchResult`), y los anida bajo
un único documento de comparación, desplazando un nivel cada encabezado
Markdown de nivel 1 o 2 que produce `render_markdown` (`# ` -> `## `,
`## ` -> `### `, vía `_shift_markdown_headings`) para que la jerarquía
del documento quede correcta:

    # Comparación: AAPL, MSFT
    ## Investigación: AAPL
    ### Salud financiera
    ...
    ## Investigación: MSFT
    ### Salud financiera
    ...

Se elige esta reutilización, en vez de una tabla comparativa
escalar-por-escalar (ya cubierta, para una única empresa frente a sus
pares, por la sección "Comparables del sector" del reporte individual),
por dos motivos:

- **No hay ningún cálculo comparativo nuevo que ensamblar en esta
  tarea.** `investmentops.core.orchestrator.compare` ya deja explícito
  que no calcula ningún posicionamiento relativo entre las empresas
  comparadas — solo ejecuta `investigate(...)` para cada una. El
  posicionamiento relativo ya existe, por separado, como el motor de
  comparables (`run_comparables_engine`), y no está conectado a este
  flujo (ver PROGRESS.md). Reproducir aquí una tabla comparativa
  escalar-por-escalar duplicaría, sin ninguna fuente de datos nueva,
  algo que ese motor ya hace mejor (con posición relativa explícita, no
  solo el valor crudo de cada empresa).
- **Ninguna empresa pierde ninguna sección de su reporte individual.**
  Un usuario que compara dos empresas normalmente quiere ver el análisis
  completo de cada una (salud financiera, valoración, tendencia,
  noticias, comparables), no solo un resumen recortado — reutilizar
  `render_markdown` tal cual garantiza eso sin reimplementar ninguna de
  sus cinco secciones.

### Por qué recibe `tickers`/`results` sueltos y no un `ComparisonResult`

`investmentops.core.orchestrator.ComparisonResult` no se importa aquí:
`investmentops.core.orchestrator` ya importa `investmentops.reports`
(`render_markdown`, `render_html`, `save_markdown_report`,
`save_html_report`) para `generate_reports`/
`investigate_and_generate_reports`, por lo que importar `ComparisonResult`
desde este módulo crearía un ciclo de importación
(`core.orchestrator` -> `reports` -> `reports.markdown` ->
`core.orchestrator`). Esta función acepta en su lugar los dos campos que
expone `ComparisonResult` (`tickers`, `results`) como parámetros
sueltos: quien la invoque (el orquestador, la CLI) puede pasarle
`comparison.tickers`/`comparison.results` directamente, sin que este
módulo dependa del tipo concreto que los agrupa.

### Manejo de listas vacías o desalineadas

Esta función no valida que `len(tickers) == len(results)` ni que los
tickers coincidan con `result.company.ticker` de cada `ResearchResult`:
`ComparisonResult` ya garantiza esa correspondencia por construcción
(`compare(...)` produce un `ResearchResult` por cada ticker, en el mismo
orden). El título del documento (`# Comparación: ...`) usa `tickers`
(los solicitados originalmente, sin normalizar, ver
`ComparisonResult.tickers`); el cuerpo usa `results` (uno por empresa,
cada uno ya con su propio ticker normalizado en `result.company.ticker`,
visible en su propio encabezado `## Investigación: <ticker>` ya
producido por `render_markdown`).

Fuera de alcance de esta tarea:
- El generador HTML: tarea separada y posterior de la misma sección de
  `TASKS.md`.
- Conectar este generador con el orquestador o la CLI (ej. un nuevo
  `--format` para `compare`, o un `generate_comparison_reports`
  análogo a `generate_reports`): no forma parte de esta tarea.
- Cualquier tabla comparativa escalar-por-escalar entre las empresas
  comparadas: ya existe, por separado, como el motor de comparables
  (Fase 5), no conectado a este flujo (ver arriba).

## Guardado del archivo Markdown generado (`save_markdown_report`)

`save_markdown_report` escribe el texto ya renderizado por
`render_markdown` a un archivo local, en una ruta configurable. Sigue
exactamente el mismo patrón ya usado por
`investmentops.data_layer.cache._save_section` / `_resolve_cache_dir`
para la caché de datos normalizados:

1. **Resolución de la ruta de destino**, en este orden de prioridad:
   - `output_dir` recibido explícitamente (útil sobre todo para pruebas,
     sin depender de `config.local.toml` real en disco).
   - `[output].output_dir` en la configuración ya cargada (`config`) o,
     si tampoco se indica, en `investmentops.config.load_config()`. Esta
     clave ya está documentada en `CONFIGURATION.md` y presente en
     `config.example.toml` (`output_dir = "reports/"`) desde la Fase 1,
     pero hasta ahora no tenía ningún consumidor real.
   - `DEFAULT_OUTPUT_DIR` (``"reports/"``, el mismo valor de ejemplo ya
     usado en `config.example.toml`) si ninguna de las anteriores aplica.
2. **Creación del directorio** si no existe (`Path.mkdir(parents=True,
   exist_ok=True)`), igual criterio que la caché.
3. **Nombre del archivo:** `<TICKER>.md`, con el ticker normalizado a
   mayúsculas, consistente con la convención ya usada por la caché de
   datos normalizados (`<TICKER>.json`, ver
   `investmentops/data_layer/CACHE.md`) — un archivo por empresa, fácil
   de ubicar y de sobrescribir en investigaciones sucesivas del mismo
   ticker.
4. **Escritura del archivo** en UTF-8, sobrescribiendo por completo
   cualquier contenido previo del mismo ticker (una investigación nueva
   reemplaza el reporte anterior, sin necesidad de versionado: no hay
   evidencia todavía de un caso de uso que lo requiera).

Cualquier fallo (ticker vacío, fallo de E/S al crear el directorio o al
escribir el archivo) se señala mediante `ReportError`, nunca dejando
escapar una excepción específica de `pathlib`/E/S sin traducir, mismo
criterio ya aplicado por `CacheError` en
`investmentops.data_layer.cache`.

Fuera de alcance de este módulo:
- El generador HTML: sección separada de `TASKS.md` (incluida su propia
  tarea, todavía pendiente, de añadir el equivalente de este reporte de
  comparación).
- Conectar el motor de comparables (`run_comparables_engine`) con
  `investigate()`: no forma parte de esta tarea de plantilla; hoy ningún
  `ResearchResult` real incluye un `AnalysisResult` con
  `analysis_id="comparables"` (ver `investmentops/core/orchestrator.py`).
- Conectar `render_markdown_comparison`/`save_markdown_report` con el
  orquestador o con la CLI para un nuevo formato de salida de `compare`:
  tarea separada y posterior de `TASKS.md`.
- Gráficos o visualizaciones: fuera de alcance del MVP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.config import load_config
from investmentops.core.research_result import ResearchResult

#: Identificador del agente de salud financiera, el mismo usado en
#: `investmentops.analysis_engines.financial_health.AGENT_ID`. No se
#: importa directamente desde ese módulo para no acoplar este generador
#: a la implementación concreta del agente (basta con el identificador
#: de texto, ya estable como parte de `AnalysisResult.analysis_id`).
FINANCIAL_HEALTH_AGENT_ID = "financial_health"

#: Identificador del agente de valoración, el mismo usado en
#: `investmentops.analysis_engines.valuation.AGENT_ID`. Mismo criterio
#: que `FINANCIAL_HEALTH_AGENT_ID`: no se importa desde el módulo del
#: agente para no acoplar este generador a su implementación concreta.
VALUATION_AGENT_ID = "valuation"

#: Identificador del motor de evolución de ingresos y beneficios, el
#: mismo usado en `investmentops.analysis_engines.trends.AGENT_ID` (y
#: propagado tal cual por
#: `investmentops.core.orchestrator._trend_analysis_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: dos identificadores anteriores: no se importa desde el módulo del
#: motor para no acoplar este generador a su implementación concreta.
TREND_ANALYSIS_AGENT_ID = "trend_analysis"

#: Identificador del motor de noticias relevantes, el mismo usado en
#: `investmentops.analysis_engines.news_relevance.AGENT_ID` (y propagado
#: tal cual por
#: `investmentops.core.orchestrator._news_relevance_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: identificadores anteriores: no se importa desde el módulo del motor
#: para no acoplar este generador a su implementación concreta.
NEWS_RELEVANCE_AGENT_ID = "news_relevance"

#: Identificador del motor de posicionamiento relativo, el mismo usado
#: en `investmentops.analysis_engines.comparables.AGENT_ID` (y propagado
#: tal cual por
#: `investmentops.core.orchestrator._comparables_analysis_result_to_analysis_result`
#: al convertir su resultado a `AnalysisResult`). Mismo criterio que los
#: identificadores anteriores: no se importa desde el módulo del motor
#: para no acoplar este generador a su implementación concreta.
COMPARABLES_AGENT_ID = "comparables"

#: Valor por defecto si no se indica una ruta de salida explícita ni se
#: puede leer `[output].output_dir` desde `config.local.toml` (mismo
#: valor documentado como ejemplo en `config.example.toml`, sección
#: `[output]`).
DEFAULT_OUTPUT_DIR = "reports/"


class ReportError(RuntimeError):
    """Error al guardar un reporte generado en disco.

    Cubre el caso de un ticker vacío (para el que no existe un nombre de
    archivo válido) y cualquier fallo de E/S al crear el directorio de
    salida configurado o al escribir el archivo del reporte. Mismo
    criterio ya aplicado por `investmentops.data_layer.cache.CacheError`
    para la caché de datos normalizados.
    """


def _find_analysis(
    result: ResearchResult, analysis_id: str
) -> AnalysisResult | None:
    """Busca, dentro de `result.analysis_results`, el análisis con `analysis_id`.

    Devuelve ``None`` si ese agente no completó su análisis (no aparece
    en la lista), en cuyo caso la sección correspondiente del reporte
    conserva solo su encabezado vacío. Funciona igual para cualquier
    `analysis_id` (``"financial_health"``, ``"valuation"``,
    ``"trend_analysis"``, ``"news_relevance"``, ``"comparables"``): no
    está acoplada a ningún agente concreto.
    """
    return next(
        (analysis for analysis in result.analysis_results if analysis.analysis_id == analysis_id),
        None,
    )


def _render_analysis_body(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas de hallazgos, métricas, limitaciones y
    procedencia de IA de un análisis.

    Orden fijado en `REPORT_SECTIONS.md`: hallazgos → métricas de
    soporte → limitaciones → procedencia de la interpretación de IA
    (proveedor, modelo y fecha de generación). Reutilizada tanto para
    "Salud financiera" como para "Valoración" (no depende del
    `analysis_id` concreto). No se usa para "Evolución de ingresos y
    beneficios", "Noticias recientes relevantes" ni "Comparables del
    sector": esas secciones reemplazan el volcado plano de
    `supporting_metrics` por una tabla o una lista (ver
    `_render_trend_analysis_body`, `_render_news_relevance_body`,
    `_render_comparables_body`).
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(finding)
    lines.append("")

    if analysis.supporting_metrics:
        lines.append("**Métricas de soporte:**")
        lines.append("")
        for key, value in analysis.supporting_metrics.items():
            lines.append(f"- {key}: {value}")
        lines.append("")

    if analysis.limitations:
        lines.append("**Limitaciones:**")
        lines.append("")
        for limitation in analysis.limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    provenance = analysis.provenance
    lines.append(
        f"**Generado por:** {provenance.ai_provider} ({provenance.ai_model}) "
        f"el {provenance.generated_at.isoformat()}"
    )
    lines.append("")

    return lines


def _format_growth_percentage(value: Any) -> str:
    """Formatea una variación relativa (ej. ``0.083``) como porcentaje con signo.

    Devuelve ``"—"`` si `value` es ``None`` (periodo base en cero, ver
    `TREND_METRICS.md`), conforme a `TREND_PRESENTATION.md`, "Formato del
    valor". El signo siempre se muestra explícitamente (``+`` o ``-``),
    con un decimal.
    """
    if value is None:
        return "—"
    return f"{value * 100:+.1f}%"


def _render_trend_analysis_body(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas de la sección "Evolución de ingresos y beneficios".

    Orden fijado en `TREND_PRESENTATION.md`: hallazgos → tabla de
    variación periodo a periodo (omitida si no hay datos) → limitaciones
    → procedencia de IA (centinela). A diferencia de
    `_render_analysis_body`, `supporting_metrics` no se vuelca como lista
    plana: las claves `revenue_growth_by_period`/
    `net_income_growth_by_period` (mapeos con un elemento por periodo) se
    combinan en una única tabla Markdown, una fila por periodo. Las
    claves `revenue_trend`/`net_income_trend` (tendencia agregada) no se
    repiten aparte: ya están incluidas en el texto de `findings` (ver
    `investmentops.analysis_engines.trends._describe_trend`).
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(finding)
    lines.append("")

    revenue_by_period: dict[str, Any] = analysis.supporting_metrics.get(
        "revenue_growth_by_period", {}
    )
    net_income_by_period: dict[str, Any] = analysis.supporting_metrics.get(
        "net_income_growth_by_period", {}
    )

    if revenue_by_period or net_income_by_period:
        lines.append("| Periodo | Ingresos (var.) | Beneficios (var.) |")
        lines.append("|---|---|---|")
        for period_end in revenue_by_period:
            revenue_growth = revenue_by_period.get(period_end)
            net_income_growth = net_income_by_period.get(period_end)
            lines.append(
                f"| {period_end} | {_format_growth_percentage(revenue_growth)} "
                f"| {_format_growth_percentage(net_income_growth)} |"
            )
        lines.append("")

    if analysis.limitations:
        lines.append("**Limitaciones:**")
        lines.append("")
        for limitation in analysis.limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    provenance = analysis.provenance
    lines.append(
        f"**Generado por:** {provenance.ai_provider} ({provenance.ai_model}) "
        f"el {provenance.generated_at.isoformat()}"
    )
    lines.append("")

    return lines


def _render_news_relevance_body(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas de la sección "Noticias recientes relevantes".

    Orden: hallazgos → lista de noticias relevantes (omitida si no hay
    ninguna) → limitaciones → procedencia de IA (centinela). A diferencia
    de `_render_analysis_body`, `supporting_metrics` no se vuelca como
    lista plana: la clave `relevant_news` (una lista de dicts, no un
    escalar ni un mapeo por periodo) se vuelca como una lista Markdown,
    un ítem por noticia, ver "Sección 'Noticias recientes relevantes'"
    en el docstring del módulo.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(finding)
    lines.append("")

    relevant_news: list[dict[str, Any]] = analysis.supporting_metrics.get(
        "relevant_news", []
    )

    if relevant_news:
        for item in relevant_news:
            title = item.get("title", "")
            source = item.get("source", "")
            published_at = item.get("published_at", "")
            summary = item.get("summary", "")
            url = item.get("url", "")
            lines.append(
                f"- **{title}** ({source}, {published_at}): {summary} "
                f"([Leer más]({url}))"
            )
        lines.append("")

    if analysis.limitations:
        lines.append("**Limitaciones:**")
        lines.append("")
        for limitation in analysis.limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    provenance = analysis.provenance
    lines.append(
        f"**Generado por:** {provenance.ai_provider} ({provenance.ai_model}) "
        f"el {provenance.generated_at.isoformat()}"
    )
    lines.append("")

    return lines


def _format_comparable_value(value: Any) -> str:
    """Formatea el valor de una métrica en la tabla comparativa.

    Devuelve ``"—"`` si `value` es ``None`` (métrica no calculable para
    la empresa o el par, ver
    `investmentops.analysis_engines.comparables.calculate_entity_metrics`),
    mismo símbolo ya usado por `_format_growth_percentage` para
    variaciones no calculables. A diferencia de esa función, aquí no se
    convierte a porcentaje: las cuatro métricas comparadas
    (`net_margin`, `debt_to_revenue`, `price_to_earnings`,
    `price_to_sales`) tienen unidades distintas (ratios, múltiplos), por
    lo que se muestra el valor crudo, igual que ya hace el volcado plano
    de `supporting_metrics` en `_render_analysis_body`.
    """
    if value is None:
        return "—"
    return str(value)


def _format_comparable_position(position: Any) -> str:
    """Formatea la posición relativa de una comparación en la tabla.

    Devuelve ``"—"`` si `position` es ``None`` (comparación no posible
    por falta de datos, ver
    `investmentops.analysis_engines.comparables.compare_metric`).
    """
    if position is None:
        return "—"
    return str(position)


def _render_comparables_body(analysis: AnalysisResult) -> list[str]:
    """Construye las líneas de la sección "Comparables del sector".

    Orden: hallazgos → métricas propias de la empresa investigada (lista
    plana, igual criterio que "Salud financiera"/"Valoración") → tabla
    comparativa por métrica y par (omitida si no hay ningún par) →
    limitaciones → procedencia de IA (centinela). Ver "Sección
    'Comparables del sector'" en el docstring del módulo para el
    criterio completo de formato.
    """
    lines: list[str] = []

    for finding in analysis.findings:
        lines.append(finding)
    lines.append("")

    company_metrics: dict[str, Any] = analysis.supporting_metrics.get("company", {})
    company_metric_items = [
        (key, value) for key, value in company_metrics.items() if key != "ticker"
    ]
    if company_metric_items:
        lines.append("**Métricas de la empresa:**")
        lines.append("")
        for key, value in company_metric_items:
            lines.append(f"- {key}: {value}")
        lines.append("")

    comparisons: dict[str, list[dict[str, Any]]] = analysis.supporting_metrics.get(
        "comparisons", {}
    )
    has_any_comparison = any(comparisons.get(name) for name in comparisons)

    if has_any_comparison:
        lines.append("| Métrica | Par | Valor empresa | Valor par | Posición |")
        lines.append("|---|---|---|---|---|")
        for metric_name, entries in comparisons.items():
            for entry in entries:
                lines.append(
                    f"| {metric_name} | {entry.get('peer_ticker', '')} | "
                    f"{_format_comparable_value(entry.get('company_value'))} | "
                    f"{_format_comparable_value(entry.get('peer_value'))} | "
                    f"{_format_comparable_position(entry.get('position'))} |"
                )
        lines.append("")

    if analysis.limitations:
        lines.append("**Limitaciones:**")
        lines.append("")
        for limitation in analysis.limitations:
            lines.append(f"- {limitation}")
        lines.append("")

    provenance = analysis.provenance
    lines.append(
        f"**Generado por:** {provenance.ai_provider} ({provenance.ai_model}) "
        f"el {provenance.generated_at.isoformat()}"
    )
    lines.append("")

    return lines


def render_markdown(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte Markdown.

    Construye el encabezado (identidad de la empresa investigada y fecha
    de ensamblado) y las secciones "Salud financiera", "Valoración",
    "Evolución de ingresos y beneficios", "Noticias recientes
    relevantes" y "Comparables del sector", conforme al orden fijado en
    `investmentops/reports/REPORT_SECTIONS.md` (las dos primeras) y a la
    ubicación ya usada por `investmentops.core.orchestrator.investigate`
    para los resultados de los motores de tendencia y noticias
    relevantes (agregados después de valoración, en ese orden, en
    `ResearchResult.analysis_results`); "Comparables del sector" se
    agrega al final, ya que su motor (`run_comparables_engine`) todavía
    no se invoca desde `investigate` (ver docstring del módulo).

    Las cinco secciones ya vuelcan su contenido completo cuando el
    `AnalysisResult` correspondiente está presente. "Salud financiera" y
    "Valoración" vuelcan hallazgos, métricas de soporte (lista plana),
    limitaciones y procedencia de la interpretación de IA. "Evolución de
    ingresos y beneficios" vuelca hallazgos, una tabla de variación
    periodo a periodo, limitaciones y procedencia (centinela). "Noticias
    recientes relevantes" vuelca hallazgos, una lista de noticias
    relevantes (una por ítem), limitaciones y procedencia (centinela).
    "Comparables del sector" vuelca hallazgos, las métricas propias de
    la empresa, una tabla comparativa por métrica y par, limitaciones y
    procedencia (centinela). Todavía no se incluye la sección condicional
    de "Fallos parciales" (tarea separada, fuera del alcance definido
    para "Generador Markdown" en `TASKS.md`; ya cubierta en texto plano
    de consola por `investmentops.cli.format_research_result`, Fase 1).

    Parameters
    ----------
    result:
        El `ResearchResult` ya ensamblado (ver
        `investmentops.core.orchestrator.investigate`).

    Returns
    -------
    str
        Texto Markdown del reporte, terminado en un único salto de línea
        final.
    """
    lines: list[str] = []

    lines.append(f"# Investigación: {result.company.ticker}")
    lines.append("")

    identity_details = [
        detail
        for detail in (result.company.name, result.company.sector, result.company.market)
        if detail
    ]
    if identity_details:
        lines.append(" · ".join(identity_details))
        lines.append("")

    lines.append(f"Generado: {result.generated_at.isoformat()}")
    lines.append("")

    lines.append("## Salud financiera")
    lines.append("")
    financial_health_result = _find_analysis(result, FINANCIAL_HEALTH_AGENT_ID)
    if financial_health_result is not None:
        lines.extend(_render_analysis_body(financial_health_result))

    lines.append("## Valoración")
    lines.append("")
    valuation_result = _find_analysis(result, VALUATION_AGENT_ID)
    if valuation_result is not None:
        lines.extend(_render_analysis_body(valuation_result))

    lines.append("## Evolución de ingresos y beneficios")
    lines.append("")
    trend_analysis_result = _find_analysis(result, TREND_ANALYSIS_AGENT_ID)
    if trend_analysis_result is not None:
        lines.extend(_render_trend_analysis_body(trend_analysis_result))

    lines.append("## Noticias recientes relevantes")
    lines.append("")
    news_relevance_result = _find_analysis(result, NEWS_RELEVANCE_AGENT_ID)
    if news_relevance_result is not None:
        lines.extend(_render_news_relevance_body(news_relevance_result))

    lines.append("## Comparables del sector")
    lines.append("")
    comparables_result = _find_analysis(result, COMPARABLES_AGENT_ID)
    if comparables_result is not None:
        lines.extend(_render_comparables_body(comparables_result))

    return "\n".join(lines).rstrip("\n") + "\n"


def _shift_markdown_headings(markdown_text: str) -> str:
    """Desplaza un nivel cada encabezado Markdown de nivel 1 o 2.

    Usada por `render_markdown_comparison` para anidar el reporte
    individual completo de cada empresa (ya renderizado por
    `render_markdown`, que solo usa encabezados `# ` y `## `) bajo el
    encabezado de nivel superior del documento de comparación
    (`# Comparación: ...`), ver "Reporte de comparación" en el docstring
    del módulo.

    Solo transforma líneas que empiezan exactamente con ``"# "`` (nivel
    1) o ``"## "`` (nivel 2) — las únicas dos profundidades que produce
    `render_markdown` — sumando un ``#`` adicional a cada una
    (``"# "`` -> ``"## "``, ``"## "`` -> ``"### "``). Ambos prefijos son
    mutuamente excluyentes (una línea que empieza con ``"## "`` no
    empieza con ``"# "``, ya que el segundo carácter es ``#``, no un
    espacio), por lo que no hay ambigüedad sobre cuál aplicar. El resto
    del texto (párrafos, listas, tablas, líneas en blanco) queda
    intacto.

    Parameters
    ----------
    markdown_text:
        Texto Markdown ya renderizado (típicamente la salida de
        `render_markdown(result)`).

    Returns
    -------
    str
        El mismo texto, con cada encabezado de nivel 1 o 2 desplazado un
        nivel hacia abajo.
    """
    shifted_lines: list[str] = []
    for line in markdown_text.split("\n"):
        if line.startswith("## ") or line.startswith("# "):
            shifted_lines.append("#" + line)
        else:
            shifted_lines.append(line)
    return "\n".join(shifted_lines)


def render_markdown_comparison(
    tickers: Sequence[str], results: Sequence[ResearchResult]
) -> str:
    """Renderiza un reporte de comparación (varias empresas) en Markdown.

    Ver "Reporte de comparación (varias empresas, esta tarea)" en el
    docstring del módulo para la decisión de formato completa: reutiliza
    `render_markdown` para el reporte individual completo de cada
    empresa, anidándolos bajo un único documento de comparación
    (`# Comparación: <tickers>`), con los encabezados de cada reporte
    individual desplazados un nivel (vía `_shift_markdown_headings`) para
    que la jerarquía del documento quede correcta.

    Parameters
    ----------
    tickers:
        Los tickers solicitados para la comparación, en el mismo orden
        recibido (ej. `ComparisonResult.tickers`), usados únicamente
        para el título del documento.
    results:
        Un `ResearchResult` por empresa, en el mismo orden (ej.
        `ComparisonResult.results`), cada uno renderizado íntegramente
        vía `render_markdown` y anidado bajo su propio subtítulo
        (`## Investigación: <ticker>`, ya producido por `render_markdown`
        y desplazado un nivel).

    Returns
    -------
    str
        Texto Markdown del reporte comparativo, terminado en un único
        salto de línea final. Si `results` está vacío, el documento
        contiene únicamente el título de comparación.
    """
    lines: list[str] = []
    lines.append(f"# Comparación: {', '.join(tickers)}")
    lines.append("")

    for result in results:
        individual_report = render_markdown(result)
        lines.append(_shift_markdown_headings(individual_report))
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


def _resolve_output_dir(
    output_dir: str | Path | None, config: dict[str, Any] | None
) -> Path:
    """Resuelve el directorio de salida a usar para guardar reportes.

    Prioriza `output_dir` si se indica explícitamente (útil para
    pruebas); en caso contrario, lee `[output].output_dir` desde la
    configuración ya cargada (`config`) o, si tampoco se indica, desde
    `investmentops.config.load_config()`. Si la configuración no define
    una ruta, cae de vuelta a `DEFAULT_OUTPUT_DIR`.
    """
    if output_dir is not None:
        return Path(output_dir)

    cfg = config if config is not None else load_config()
    configured_path = cfg.get("output", {}).get("output_dir")
    return Path(configured_path or DEFAULT_OUTPUT_DIR)


def save_markdown_report(
    ticker: str,
    content: str,
    *,
    output_dir: str | Path | None = None,
    config: dict[str, Any] | None = None,
) -> Path:
    """Guarda el texto Markdown ya renderizado (`render_markdown`) en disco.

    Parameters
    ----------
    ticker:
        Identificador de la empresa investigada (ej. ``"AAPL"``). Se
        normaliza a mayúsculas para el nombre del archivo, mismo criterio
        ya usado por la caché de datos normalizados (ver
        `investmentops.data_layer.cache`).
    content:
        El texto Markdown ya generado (típicamente la salida de
        `render_markdown(result)`), escrito tal cual, sin modificarlo.
    output_dir:
        Ruta al directorio donde guardar el reporte. Si no se indica, se
        resuelve desde `config.local.toml` (sección `[output]`, clave
        `output_dir`, ver CONFIGURATION.md).
    config:
        Configuración ya cargada, útil para pruebas sin depender de un
        `config.local.toml` real en disco (ver `investmentops.config`).

    Returns
    -------
    Path
        La ruta del archivo `<TICKER>.md` escrito.

    Raises
    ------
    ReportError
        Si el ticker está vacío (o son solo espacios), o si ocurre un
        fallo de E/S al crear el directorio de salida o al escribir el
        archivo.
    ConfigError
        Si `output_dir` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml`.
    """
    if not ticker or not ticker.strip():
        raise ReportError("El ticker no puede estar vacío.")

    resolved_dir = _resolve_output_dir(output_dir, config)

    try:
        resolved_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportError(
            f"No se pudo crear el directorio de reportes '{resolved_dir}': {exc}"
        ) from exc

    file_path = resolved_dir / f"{ticker.strip().upper()}.md"

    try:
        file_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise ReportError(
            f"No se pudo escribir el archivo de reporte '{file_path}': {exc}"
        ) from exc

    return file_path