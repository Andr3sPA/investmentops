"""Motor de análisis: noticias relevantes — filtrado por ventana de tiempo,
selección de un resumen breve por noticia relevante, y ensamblado del
resultado estructurado del motor.

Cubre tres tareas de TASKS.md, Fase 4, "Motor de análisis: noticias
relevantes":

- "Implementar el filtrado de noticias según ese criterio."
  (`filter_relevant_news`, ya completada, ver PROGRESS.md), sobre el
  criterio de relevancia ya fijado en
  `investmentops/analysis_engines/NEWS_RELEVANCE.md`: una noticia es
  relevante si su `published_at` cae dentro de una ventana de los
  últimos `N` días (por defecto 7) respecto al momento del filtrado.
- "Implementar un resumen breve por noticia relevante (o selección del
  resumen ya provisto por la fuente)." (`select_news_summary`, ya
  completada, ver PROGRESS.md).
- "Ensamblar el resultado estructurado del motor (hallazgos, lista de
  noticias relevantes, advertencias si no hay noticias)."
  (`assemble_news_relevance_analysis`, `NewsRelevanceResult`, esta
  tarea).

Ninguna de las tres funciones consulta ningún proveedor de datos ni
invoca ningún proveedor de IA: son cálculos puramente determinísticos,
conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un
accesorio... El cálculo determinístico de métricas... es una entrada
para el agente, no un sustituto de su interpretación").

## Criterio de filtrado (ver NEWS_RELEVANCE.md)

- **Ventana:** `days` días (por defecto `DEFAULT_RELEVANCE_WINDOW_DAYS`,
  7), parámetro explícito de `filter_relevant_news`, no una clave de
  `config.local.toml` (mismo criterio de no sobre-diseñar ya aplicado a
  `DEFAULT_MAX_AGE` en `investmentops.data_layer.cache`).
- **Referencia temporal:** el momento del filtrado (`now`), no
  `queried_at` (la fecha en que se consultó originalmente al proveedor).
  Esto asegura que una noticia cacheada y reutilizada días después se
  evalúe contra el momento real del análisis, no contra un instante
  pasado (ver NEWS_RELEVANCE.md, "Cálculo del límite de la ventana").
  Por defecto se usa `datetime.now()`: `News.published_at` (ver
  `investmentops.data_layer.news`) es un `datetime` *naive* (sin zona
  horaria, tal como lo entrega `datetime.fromisoformat` sobre el formato
  `"YYYY-MM-DD HH:MM:SS"` de FMP), por lo que la referencia por defecto
  también debe ser naive para poder compararse directamente sin asumir
  una zona horaria que el dato no expresa.
- **Inclusión del límite:** una noticia con `published_at` exactamente
  igual al límite de la ventana (`now - timedelta(days=days)`) se
  considera **dentro** de la ventana (comparación `>=`), evitando
  descartar por un margen de microsegundos una noticia publicada
  justo en el borde.
- **Sin reordenar ni deduplicar.** El resultado conserva el mismo orden
  relativo en que llegaron las noticias de entrada (ver
  NEWS_RELEVANCE.md, "Sin filtrado temático ni de sentimiento... Sin
  deduplicación").
- **Lista vacía de entrada o ninguna noticia dentro de la ventana:**
  ambos casos producen una lista vacía de salida, sin lanzar ninguna
  excepción (ver NEWS_RELEVANCE.md, "Manejo de casos degenerados"): no
  es responsabilidad de esta función declarar esa ausencia como
  limitación explícita en un resultado estructurado — eso corresponde a
  `assemble_news_relevance_analysis` (esta tarea).

## Resumen breve por noticia (`select_news_summary`)

`News.summary` (ya normalizado desde `"text"` de FMP, ver
`investmentops.data_layer.normalization.news_from_raw`) puede ser
arbitrariamente largo: es el cuerpo completo de la noticia tal como lo
entrega la fuente, no un resumen ya acotado. Esta función selecciona ese
mismo texto como base (no genera un resumen nuevo vía IA, ver "Decisión
de implementación" en PROGRESS.md) y lo recorta solo si excede una
longitud máxima:

- **Si `News.summary` ya cabe** dentro de `max_length` (por defecto
  `DEFAULT_SUMMARY_MAX_LENGTH`, 280 caracteres): se devuelve tal cual,
  sin modificar ni agregar puntos suspensivos.
- **Si excede `max_length`:** se recorta en el límite de palabra más
  cercano hacia atrás (el último espacio antes de `max_length`), para no
  cortar una palabra a la mitad, y se agrega `"..."` al final. Los
  espacios sobrantes justo antes del corte se eliminan
  (`str.rstrip()`) antes de agregar los puntos suspensivos.
- **Si no hay ningún espacio antes de `max_length`** (una sola palabra
  más larga que el límite, caso degenerado pero posible): se recorta de
  forma dura exactamente en `max_length` y se agrega `"..."`, en vez de
  devolver un texto más largo de lo pedido.
- **Resumen vacío:** se devuelve tal cual (`""`), sin lanzar ninguna
  excepción ni agregar puntos suspensivos a una cadena vacía.

`max_length` es un parámetro explícito con valor por defecto razonable
(280, longitud similar a la de un mensaje corto legible de un vistazo),
no una clave nueva de `config.local.toml`: mismo criterio de no
sobre-diseñar ya aplicado a `DEFAULT_MAX_AGE`/
`DEFAULT_RELEVANCE_WINDOW_DAYS` en este mismo proyecto.

## Ensamblado del resultado estructurado del motor (`assemble_news_relevance_analysis`, esta tarea)

Cubre la tarea "Ensamblar el resultado estructurado del motor
(hallazgos, lista de noticias relevantes, advertencias si no hay
noticias)" (TASKS.md, Fase 4). Dada una lista de `News` ya normalizadas
para una empresa, esta función encadena `filter_relevant_news` y
`select_news_summary` (ambas ya implementadas en este módulo) y produce
un `NewsRelevanceResult`:

- **`findings`**: un único hallazgo en lenguaje natural, generado por
  plantilla determinista (no por un modelo de lenguaje, mismo criterio
  ya aplicado por `_describe_trend` en
  `investmentops.analysis_engines.trends`), indicando cuántas noticias
  relevantes se encontraron dentro de la ventana, o su ausencia si no
  hay ninguna.
- **`supporting_metrics`**: un único mapeo con la clave
  `"relevant_news"`, cuyo valor es la lista de noticias relevantes ya
  filtradas, cada una serializada como un `dict` con `title`, `summary`
  (ya recortado vía `select_news_summary`), `source`, `published_at`
  (ISO 8601) y `url` — mismo criterio de serialización explícita ya
  usado por `revenue_growth_by_period`/`net_income_growth_by_period` en
  `assemble_trend_analysis`, en vez de dejar objetos `News` sin
  serializar dentro de `supporting_metrics` (que es
  `Mapping[str, Any]`, pero conviene mantenerlo JSON-serializable, mismo
  estándar ya seguido por el resto del proyecto para reportes/consola).
  Lista vacía si no hay ninguna noticia relevante.
- **`limitations`**: vacío si se encontró al menos una noticia relevante;
  contiene una única advertencia explícita, identificando el tamaño de
  la ventana usada, si no se encontró ninguna — cubre tanto el caso de
  una lista de entrada vacía como el de "ninguna dentro de la ventana"
  (ver NEWS_RELEVANCE.md, "Manejo de casos degenerados": ambos son el
  mismo caso desde la perspectiva de este ensamblado).

### Por qué no se usa `AnalysisResult`/`AnalysisProvenance`

Mismo criterio ya aplicado por `TrendAnalysisResult`
(`investmentops.analysis_engines.trends`, ver ese módulo para la
justificación completa): este motor, en las tareas ya definidas para él
en `TASKS.md`, no invoca ningún proveedor de IA — el "resumen breve" de
`select_news_summary` es una selección/recorte determinístico del texto
ya entregado por la fuente, no una interpretación generada por un
modelo de lenguaje. Forzar el contrato `AnalysisResult` (que exige una
`AnalysisProvenance` real) implicaría fabricar una procedencia de IA
inexistente. `NewsRelevanceResult` define, en su lugar, exactamente los
campos que pide la tarea (`findings`, `supporting_metrics`,
`limitations`) más un `analysis_id` para identificar este motor, sin
`provenance`. Cómo este resultado se incorpora al `ResearchResult` común
(que hoy solo acepta `AnalysisResult`) es una decisión que corresponde a
una futura tarea de "Orquestador" (TASKS.md, Fase 4: "Registrar el nuevo
motor de análisis sin modificar los motores existentes" / "Incluir el
nuevo resultado en el 'Resultado de investigación'"), no a esta.

Fuera de alcance de este módulo:
- El ensamblado del resultado estructurado del motor de tendencias
  (vive en `investmentops.analysis_engines.trends`).
- Registrar este motor en el orquestador e incorporar su resultado al
  `ResearchResult` (tarea separada y posterior, ver TASKS.md, "Fase 4 >
  Orquestador").
- La presentación de este resultado en los reportes Markdown/HTML (tarea
  separada y posterior, ver TASKS.md, "Fase 4 > Reportes").
- Cualquier resumen generado por un modelo de lenguaje: descartado
  explícitamente (ver "Decisión de implementación" en PROGRESS.md); este
  motor no invoca ningún proveedor de IA.
- Cualquier filtrado temático, de sentimiento, por fuente, o
  deduplicación: descartados explícitamente en `NEWS_RELEVANCE.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence

from investmentops.data_layer.news import News

#: Identificador de este motor de análisis, usado como
#: `NewsRelevanceResult.analysis_id`. No se usa para localizar un
#: archivo de prompt (este motor no invoca ningún proveedor de IA en las
#: tareas ya definidas para él, ver "Por qué no se usa
#: AnalysisResult/AnalysisProvenance" en el docstring del módulo).
AGENT_ID = "news_relevance"

#: Ventana de relevancia por defecto, en días, conforme a la decisión
#: tomada en `NEWS_RELEVANCE.md` ("N por defecto: 7 días").
DEFAULT_RELEVANCE_WINDOW_DAYS = 7

#: Longitud máxima por defecto (en caracteres) del resumen breve
#: devuelto por `select_news_summary`, si `News.summary` la excede. Ver
#: "Resumen breve por noticia" en el docstring del módulo.
DEFAULT_SUMMARY_MAX_LENGTH = 280


@dataclass(frozen=True)
class NewsRelevanceResult:
    """Resultado estructurado del motor de análisis de noticias relevantes
    (ver "Ensamblado del resultado estructurado del motor" en el
    docstring del módulo).

    A diferencia de `investmentops.analysis_engines.contracts.AnalysisResult`
    (usado por los motores de salud financiera y valoración, Fase 1), este
    tipo no lleva `provenance`: este motor no invoca ningún proveedor de
    IA en las tareas ya definidas para él (ver "Por qué no se usa
    AnalysisResult/AnalysisProvenance" en el docstring del módulo). Mismo
    patrón ya usado por `investmentops.analysis_engines.trends.TrendAnalysisResult`.

    Attributes
    ----------
    analysis_id:
        Identificador de este motor de análisis (siempre `AGENT_ID`,
        ``"news_relevance"``).
    findings:
        Hallazgos en lenguaje natural, generados por plantilla
        determinista (no por un modelo de lenguaje) a partir de la
        cantidad de noticias relevantes encontradas.
    supporting_metrics:
        Métricas de soporte: la lista de noticias relevantes ya
        filtradas y con su resumen ya recortado, bajo la clave
        ``"relevant_news"`` (ver `assemble_news_relevance_analysis`).
    limitations:
        Advertencia explícita si no se encontró ninguna noticia
        relevante dentro de la ventana configurada; vacío en caso
        contrario.
    """

    analysis_id: str
    findings: Sequence[str]
    supporting_metrics: Mapping[str, Any]
    limitations: Sequence[str]


def filter_relevant_news(
    news_items: list[News],
    *,
    days: int = DEFAULT_RELEVANCE_WINDOW_DAYS,
    now: datetime | None = None,
) -> list[News]:
    """Filtra `news_items` a las que caen dentro de la ventana de tiempo reciente.

    Parameters
    ----------
    news_items:
        Lista de `News` ya normalizadas (ver
        `investmentops.data_layer.normalization.news_from_raw`), en
        cualquier orden. Una lista vacía es una entrada válida (ver
        docstring del módulo).
    days:
        Tamaño de la ventana de relevancia, en días. Por defecto,
        `DEFAULT_RELEVANCE_WINDOW_DAYS` (7), conforme a
        `NEWS_RELEVANCE.md`.
    now:
        Momento de referencia contra el que se calcula la ventana
        (`now - timedelta(days=days)` es el límite inferior). Si no se
        indica, se usa `datetime.now()` (hora local, *naive*, misma
        convención que `News.published_at`). Pensado sobre todo para
        pruebas, para no depender del reloj real del sistema.

    Returns
    -------
    list[News]
        Las noticias de `news_items` cuyo `published_at` es mayor o
        igual al límite de la ventana, en el mismo orden relativo en que
        llegaron (sin reordenar). Lista vacía si ninguna noticia cae
        dentro de la ventana, o si `news_items` ya estaba vacía.
    """
    reference_time = now if now is not None else datetime.now()
    cutoff = reference_time - timedelta(days=days)

    return [item for item in news_items if item.published_at >= cutoff]


def select_news_summary(
    news: News,
    *,
    max_length: int = DEFAULT_SUMMARY_MAX_LENGTH,
) -> str:
    """Selecciona un resumen breve para `news`, a partir del ya provisto por la fuente.

    No genera un resumen nuevo vía IA (ver "Resumen breve por noticia" en
    el docstring del módulo): toma `news.summary` tal cual, recortándolo
    solo si excede `max_length`.

    Parameters
    ----------
    news:
        La `News` ya normalizada (ver `investmentops.data_layer.News`)
        de la que se selecciona el resumen breve.
    max_length:
        Longitud máxima (en caracteres) del resumen devuelto. Por
        defecto, `DEFAULT_SUMMARY_MAX_LENGTH` (280).

    Returns
    -------
    str
        - `news.summary` sin modificar, si ya cabe dentro de
          `max_length`.
        - `news.summary` recortado en el límite de palabra más cercano
          hacia atrás, con `"..."` agregado al final, si excede
          `max_length` y hay al menos un espacio antes del límite.
        - `news.summary` recortado de forma dura exactamente en
          `max_length`, con `"..."` agregado, si excede `max_length` y
          no hay ningún espacio antes del límite (una sola palabra larga).
        - `""` si `news.summary` está vacío.
    """
    summary = news.summary

    if len(summary) <= max_length:
        return summary

    truncated = summary[:max_length]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated.rstrip() + "..."


def _build_no_relevant_news_warning(days: int) -> str:
    """Construye la advertencia usada cuando no hay ninguna noticia relevante.

    Se construye dinámicamente (en vez de ser una constante fija de
    módulo) porque debe identificar el tamaño de la ventana (`days`)
    efectivamente usada en la llamada, que es un parámetro variable de
    `assemble_news_relevance_analysis` (mismo criterio ya usado por las
    advertencias por punto degenerado en
    `investmentops.analysis_engines.trends`, construidas inline con los
    valores concretos del caso).
    """
    return (
        "No se encontraron noticias recientes relevantes en los últimos "
        f"{days} día(s)."
    )


def _describe_relevant_news_count(days: int, count: int) -> str:
    """Genera el hallazgo en lenguaje natural a partir de la cantidad de
    noticias relevantes encontradas.

    Plantilla determinista, no generada por un modelo de lenguaje (ver
    "Ensamblado del resultado estructurado del motor" en el docstring
    del módulo).
    """
    if count == 0:
        return _build_no_relevant_news_warning(days)

    noun = "noticia reciente relevante" if count == 1 else "noticias recientes relevantes"
    return f"Se encontraron {count} {noun} en los últimos {days} día(s)."


def assemble_news_relevance_analysis(
    news_items: Sequence[News],
    *,
    days: int = DEFAULT_RELEVANCE_WINDOW_DAYS,
    now: datetime | None = None,
    summary_max_length: int = DEFAULT_SUMMARY_MAX_LENGTH,
) -> NewsRelevanceResult:
    """Ensambla el resultado estructurado del motor de noticias relevantes
    para una empresa.

    Encadena `filter_relevant_news` y `select_news_summary` (ambas ya
    implementadas en este módulo) y empaqueta sus resultados en un
    `NewsRelevanceResult` (ver "Ensamblado del resultado estructurado del
    motor" en el docstring del módulo).

    Parameters
    ----------
    news_items:
        La lista de `News` ya normalizadas de la empresa a analizar (ver
        `investmentops.data_layer.normalization.news_from_raw`), en
        cualquier orden. Una lista vacía es una entrada válida: produce
        el mismo resultado que "ninguna noticia dentro de la ventana"
        (ver NEWS_RELEVANCE.md, "Manejo de casos degenerados").
    days:
        Tamaño de la ventana de relevancia, en días, propagado tal cual
        a `filter_relevant_news`. Por defecto,
        `DEFAULT_RELEVANCE_WINDOW_DAYS` (7).
    now:
        Momento de referencia contra el que se calcula la ventana,
        propagado tal cual a `filter_relevant_news`. Si no se indica, se
        usa `datetime.now()`. Pensado sobre todo para pruebas.
    summary_max_length:
        Longitud máxima del resumen breve de cada noticia relevante,
        propagada tal cual a `select_news_summary`. Por defecto,
        `DEFAULT_SUMMARY_MAX_LENGTH` (280).

    Returns
    -------
    NewsRelevanceResult
        - `analysis_id`: siempre `AGENT_ID` (``"news_relevance"``).
        - `findings`: un único hallazgo, indicando cuántas noticias
          relevantes se encontraron (o su ausencia).
        - `supporting_metrics`: `{"relevant_news": [...]}`, donde cada
          elemento es un `dict` con `title`, `summary` (ya recortado),
          `source`, `published_at` (ISO 8601) y `url`. Lista vacía si no
          hay ninguna noticia relevante.
        - `limitations`: vacío si se encontró al menos una noticia
          relevante; contiene una única advertencia explícita en caso
          contrario.
    """
    relevant_news = filter_relevant_news(list(news_items), days=days, now=now)

    findings = [_describe_relevant_news_count(days, len(relevant_news))]

    supporting_metrics: dict[str, Any] = {
        "relevant_news": [
            {
                "title": item.title,
                "summary": select_news_summary(item, max_length=summary_max_length),
                "source": item.source,
                "published_at": item.published_at.isoformat(),
                "url": item.url,
            }
            for item in relevant_news
        ]
    }

    limitations: list[str] = (
        [] if relevant_news else [_build_no_relevant_news_warning(days)]
    )

    return NewsRelevanceResult(
        analysis_id=AGENT_ID,
        findings=findings,
        supporting_metrics=supporting_metrics,
        limitations=limitations,
    )