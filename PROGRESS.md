# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Motor de análisis: noticias relevantes" → "Implementar un
resumen breve por noticia relevante (o selección del resumen ya
provisto por la fuente)" (TASKS.md).

### Qué se implementó

`select_news_summary` en `investmentops/analysis_engines/news_relevance.py`
(mismo módulo que `filter_relevant_news`, ya implementado en la tarea
anterior). Selecciona el resumen ya provisto por la fuente
(`News.summary`), sin generar uno nuevo vía IA:

- **Sin truncar si ya cabe:** si `News.summary` ya tiene una longitud
  menor o igual a `max_length` (por defecto
  `DEFAULT_SUMMARY_MAX_LENGTH = 280`, parámetro explícito, no una clave
  nueva de `config.local.toml`, mismo criterio ya aplicado a
  `DEFAULT_MAX_AGE`/`DEFAULT_RELEVANCE_WINDOW_DAYS`), se devuelve tal
  cual.
- **Truncado en límite de palabra:** si excede `max_length`, se recorta
  en el último espacio antes del límite y se agrega `"..."`, para no
  cortar una palabra a la mitad.
- **Truncado duro como respaldo:** si no hay ningún espacio antes del
  límite (una sola palabra muy larga), se recorta exactamente en
  `max_length` y se agrega `"..."`.
- **Resumen vacío:** se devuelve `""` sin modificar ni lanzar excepción.

### Decisión de implementación

El paréntesis de la propia tarea en `TASKS.md` ("o selección del resumen
ya provisto por la fuente") ya fija el criterio: no se invoca ningún
proveedor de IA para generar un resumen nuevo. Esto es consistente con
el motor de tendencias de la Fase 3
(`investmentops.analysis_engines.trends`), que tampoco usa IA porque
`TASKS.md` no define para estos motores ninguna tarea explícita de
"escribir prompt"/"invocar proveedor de IA", a diferencia de salud
financiera y valoración (Fase 1).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_news_summary.py`

Modificados:
- `investmentops/analysis_engines/news_relevance.py` (se agregó
  `select_news_summary`/`DEFAULT_SUMMARY_MAX_LENGTH`, sin modificar
  `filter_relevant_news`/`DEFAULT_RELEVANCE_WINDOW_DAYS`, ya
  implementadas)
- `TASKS.md` (una línea: tarea de resumen breve marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Motor de análisis: noticias relevantes" → "Ensamblar el
resultado estructurado del motor (hallazgos, lista de noticias
relevantes, advertencias si no hay noticias)".