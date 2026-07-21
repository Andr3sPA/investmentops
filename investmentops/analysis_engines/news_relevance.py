"""Motor de análisis: noticias relevantes — filtrado por ventana de tiempo
y selección de un resumen breve por noticia relevante.

Cubre dos tareas de TASKS.md, Fase 4, "Motor de análisis: noticias
relevantes":

- "Implementar el filtrado de noticias según ese criterio."
  (`filter_relevant_news`, ya completada, ver PROGRESS.md), sobre el
  criterio de relevancia ya fijado en
  `investmentops/analysis_engines/NEWS_RELEVANCE.md`: una noticia es
  relevante si su `published_at` cae dentro de una ventana de los
  últimos `N` días (por defecto 7) respecto al momento del filtrado.
- "Implementar un resumen breve por noticia relevante (o selección del
  resumen ya provisto por la fuente)." (`select_news_summary`, esta
  tarea).

Ninguna de las dos funciones consulta ningún proveedor de datos ni
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
  la tarea de ensamblado del motor, todavía pendiente en esta misma
  sección de `TASKS.md`.

## Resumen breve por noticia (`select_news_summary`, esta tarea)

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

Fuera de alcance de este módulo:
- El ensamblado del resultado estructurado del motor (hallazgos, lista
  de noticias relevantes con su resumen ya seleccionado, advertencias si
  no hay noticias): tarea separada y posterior en la misma sección de
  `TASKS.md`.
- Cualquier resumen generado por un modelo de lenguaje: descartado
  explícitamente (ver "Decisión de implementación" en PROGRESS.md); este
  motor no invoca ningún proveedor de IA.
- Cualquier filtrado temático, de sentimiento, por fuente, o
  deduplicación: descartados explícitamente en `NEWS_RELEVANCE.md`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from investmentops.data_layer.news import News

#: Ventana de relevancia por defecto, en días, conforme a la decisión
#: tomada en `NEWS_RELEVANCE.md` ("N por defecto: 7 días").
DEFAULT_RELEVANCE_WINDOW_DAYS = 7

#: Longitud máxima por defecto (en caracteres) del resumen breve
#: devuelto por `select_news_summary`, si `News.summary` la excede. Ver
#: "Resumen breve por noticia" en el docstring del módulo.
DEFAULT_SUMMARY_MAX_LENGTH = 280


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