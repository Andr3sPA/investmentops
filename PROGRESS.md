# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Motor de análisis: noticias relevantes" → "Definir el criterio
básico de relevancia/filtrado de noticias para el MVP (ej. ventana de
tiempo reciente)" (TASKS.md).

### Nota previa: tarea de caché ya satisfecha, sin código nuevo

Antes de esta tarea, se verificó "Implementar la lectura de noticias
normalizadas desde caché..." (Fase 4, "Normalización"): ya estaba
satisfecha por `load_news` (`investmentops/data_layer/cache.py`),
implementada en la tarea anterior junto con `save_news`, mismo criterio
ya aplicado en Fase 3 a la serie histórica (`save_financial_statement_series`/
`load_financial_statement_series`, también implementadas en conjunto).
Se marcó como completada en `TASKS.md` sin duplicar código.

### Qué se implementó (esta tarea)

`investmentops/analysis_engines/NEWS_RELEVANCE.md` (nuevo). Tarea de
diseño/documentación, sin código: decide qué hace que una noticia se
considere "relevante" para el MVP, a partir de los campos disponibles en
`News` (`investmentops/data_layer/news.py`): `title`, `summary`,
`source`, `published_at`, `url`.

Decisión: **ventana de tiempo reciente**, sin filtrado temático,
de sentimiento ni deduplicación:

- Una noticia es relevante si `published_at` cae dentro de los últimos
  **N días** (por defecto 7) respecto al momento del filtrado (no
  respecto a `queried_at`, para que una noticia cacheada y reutilizada
  días después se evalúe contra el momento real del análisis).
- `N` es un parámetro configurable de la función que implemente el
  filtrado (tarea siguiente), no un valor fijo en `config.local.toml`,
  mismo criterio de no sobre-diseñar ya aplicado a `DEFAULT_MAX_AGE` en
  `investmentops/data_layer/cache.py`.
- Se descarta explícitamente cualquier filtrado por contenido,
  sentimiento o fuente: el modelo de dominio `News` no expone ninguna
  señal de ese tipo, y `NEWS_PROVIDER.md` ya decidió no depender de
  interpretación de terceros (ver "Sin análisis de sentimiento de
  terceros"). Aproximar esa señal con heurísticas no validadas violaría
  el principio ya aplicado en el resto del proyecto (`FINANCIAL_HEALTH_METRICS.md`,
  `VALUATION_METRICS.md`: no inventar datos que no existen).
- Documenta el manejo de casos degenerados: ninguna noticia dentro de la
  ventana (limitación explícita, no error) y lista de entrada vacía
  (mismo resultado, ya no es un error desde `investmentops/data_providers/news.py`).

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/NEWS_RELEVANCE.md`

Modificados:
- `TASKS.md` (dos líneas: la tarea de lectura desde caché marcada como
  ya satisfecha, y esta tarea de criterio de relevancia marcada como
  completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Motor de análisis: noticias relevantes" → "Implementar el
filtrado de noticias según ese criterio" (aplicar la ventana de N días ya
decidida en `NEWS_RELEVANCE.md` sobre una lista de `News`, devolviendo
las que caen dentro de la ventana).