"""Motor de análisis: noticias relevantes — filtrado por ventana de tiempo.

Cubre la tarea "Implementar el filtrado de noticias según ese criterio"
(TASKS.md, Fase 4, "Motor de análisis: noticias relevantes"), sobre el
criterio de relevancia ya fijado en
`investmentops/analysis_engines/NEWS_RELEVANCE.md`: una noticia es
relevante si su `published_at` cae dentro de una ventana de los últimos
`N` días (por defecto 7) respecto al momento del filtrado.

Este módulo implementa únicamente el filtrado en sí, sobre una lista de
`News` ya normalizadas (ver `investmentops.data_layer.News`). No
consulta ningún proveedor de datos ni invoca ningún proveedor de IA:
es un cálculo puramente determinístico, conforme a `ARCHITECTURE.md`
("La IA es un mecanismo central, no un accesorio... El cálculo
determinístico de métricas... es una entrada para el agente, no un
sustituto de su interpretación").

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

Fuera de alcance de este módulo:
- El resumen breve por noticia relevante (tarea separada y posterior de
  la misma sección, "Implementar un resumen breve por noticia relevante
  (o selección del resumen ya provisto por la fuente)").
- El ensamblado del resultado estructurado del motor (hallazgos, lista
  de noticias relevantes, advertencias si no hay noticias): tarea
  separada y posterior en la misma sección.
- Cualquier filtrado temático, de sentimiento, por fuente, o
  deduplicación: descartados explícitamente en `NEWS_RELEVANCE.md`.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from investmentops.data_layer.news import News

#: Ventana de relevancia por defecto, en días, conforme a la decisión
#: tomada en `NEWS_RELEVANCE.md` ("N por defecto: 7 días").
DEFAULT_RELEVANCE_WINDOW_DAYS = 7


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