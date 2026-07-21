# investmentops/reports/markdown.py
"""Generador de reportes en Markdown.

Cubre, hasta ahora, ocho tareas de TASKS.md, Fase 2 ("Generador Markdown"),
Fase 3 ("Reportes") y Fase 4 ("Reportes"):

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
  Markdown." (esta tarea).

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

## Sección "Noticias recientes relevantes" (esta tarea)

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
  tarea, todavía pendiente, de añadir esta misma sección de noticias).
- Conectar `save_markdown_report` con el orquestador o con la CLI para
  que se invoque automáticamente tras ensamblar el resultado de
  investigación: ya conectado desde Fase 2 (ver
  `investmentops.core.orchestrator.generate_reports`).
- Gráficos o visualizaciones: fuera de alcance del MVP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    ``"trend_analysis"``, ``"news_relevance"``): no está acoplada a
    ningún agente concreto.
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
    beneficios" ni "Noticias recientes relevantes": esas secciones
    reemplazan el volcado plano de `supporting_metrics` por una tabla o
    una lista (ver `_render_trend_analysis_body`,
    `_render_news_relevance_body`).
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


def render_markdown(result: ResearchResult) -> str:
    """Renderiza un `ResearchResult` como reporte Markdown.

    Construye el encabezado (identidad de la empresa investigada y fecha
    de ensamblado) y las secciones "Salud financiera", "Valoración",
    "Evolución de ingresos y beneficios" y "Noticias recientes
    relevantes", conforme al orden fijado en
    `investmentops/reports/REPORT_SECTIONS.md` (las dos primeras) y a la
    ubicación ya usada por `investmentops.core.orchestrator.investigate`
    para los resultados de los motores de tendencia y noticias
    relevantes (agregados después de valoración, en ese orden, en
    `ResearchResult.analysis_results`).

    Las cuatro secciones ya vuelcan su contenido completo cuando el
    `AnalysisResult` correspondiente está presente. "Salud financiera" y
    "Valoración" vuelcan hallazgos, métricas de soporte (lista plana),
    limitaciones y procedencia de la interpretación de IA. "Evolución de
    ingresos y beneficios" vuelca hallazgos, una tabla de variación
    periodo a periodo, limitaciones y procedencia (centinela). "Noticias
    recientes relevantes" vuelca hallazgos, una lista de noticias
    relevantes (una por ítem), limitaciones y procedencia (centinela).
    Todavía no se incluye la sección condicional de "Fallos parciales"
    (tarea separada, fuera del alcance definido para "Generador
    Markdown" en `TASKS.md`; ya cubierta en texto plano de consola por
    `investmentops.cli.format_research_result`, Fase 1).

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