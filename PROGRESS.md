# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Motor de análisis: noticias relevantes" → "Implementar el
filtrado de noticias según ese criterio" (TASKS.md).

### Qué se implementó

`filter_relevant_news` en `investmentops/analysis_engines/news_relevance.py`
(nuevo). Implementa el criterio ya fijado en
`investmentops/analysis_engines/NEWS_RELEVANCE.md`: filtra una lista de
`News` (`investmentops.data_layer.News`) a las que caen dentro de una
ventana de tiempo reciente.

- **Ventana:** `days` días, parámetro explícito con valor por defecto
  `DEFAULT_RELEVANCE_WINDOW_DAYS = 7` (no una clave nueva de
  `config.local.toml`, mismo criterio ya aplicado a `DEFAULT_MAX_AGE` en
  `investmentops.data_layer.cache`).
- **Referencia temporal:** el momento del filtrado (`now`, parámetro
  opcional para pruebas; por defecto `datetime.now()`), no `queried_at`.
  Se usa un `datetime` *naive* por defecto porque `News.published_at` ya
  es naive (viene de `datetime.fromisoformat` sobre el formato de FMP
  `"YYYY-MM-DD HH:MM:SS"`, sin zona horaria).
- **Límite inclusivo:** una noticia publicada exactamente en el borde de
  la ventana (`now - timedelta(days=days)`) se considera relevante.
- **Sin reordenar ni deduplicar:** el resultado conserva el orden
  relativo de la entrada.
- **Casos degenerados:** lista de entrada vacía o ninguna noticia dentro
  de la ventana producen ambos una lista vacía, sin lanzar excepción —
  declarar esa ausencia como limitación explícita queda para la tarea de
  ensamblado del motor (todavía pendiente en la misma sección).

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/news_relevance.py`
- `investmentops/tests/test_analysis_engines_news_relevance.py`

Modificados:
- `TASKS.md` (una línea: tarea de filtrado marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Motor de análisis: noticias relevantes" → "Implementar un
resumen breve por noticia relevante (o selección del resumen ya provisto
por la fuente)".