# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Motor de análisis: noticias relevantes" → "Ensamblar el
resultado estructurado del motor (hallazgos, lista de noticias
relevantes, advertencias si no hay noticias)" (TASKS.md).

### Qué se implementó

`assemble_news_relevance_analysis`/`NewsRelevanceResult` en
`investmentops/analysis_engines/news_relevance.py`, encadenando las dos
piezas ya implementadas en este módulo (`filter_relevant_news`,
`select_news_summary`):

- **`findings`**: un único hallazgo en lenguaje natural, generado por
  plantilla determinista (no por un modelo de lenguaje), indicando
  cuántas noticias relevantes se encontraron dentro de la ventana
  configurada (con singular/plural correcto), o su ausencia explícita
  si no se encontró ninguna.
- **`supporting_metrics`**: `{"relevant_news": [...]}`, donde cada
  elemento es un `dict` serializable con `title`, `summary` (ya
  recortado vía `select_news_summary`), `source`, `published_at` (ISO
  8601) y `url`, en el mismo orden relativo en que llegaron las
  noticias filtradas. Lista vacía si no hay ninguna noticia relevante.
- **`limitations`**: vacío si se encontró al menos una noticia
  relevante; una única advertencia explícita (identificando el tamaño
  de la ventana usada) en caso contrario — mismo tratamiento tanto para
  una lista de entrada vacía como para "ninguna noticia dentro de la
  ventana" (dos casos que `NEWS_RELEVANCE.md` ya identificaba como
  equivalentes desde la perspectiva de este ensamblado).

Mismo criterio de diseño ya aplicado por `TrendAnalysisResult`
(`investmentops.analysis_engines.trends`, Fase 3): este motor tampoco
invoca ningún proveedor de IA en las tareas ya definidas para él en
`TASKS.md` (el "resumen breve" es un recorte determinístico, no una
interpretación generada por IA), por lo que `NewsRelevanceResult` no
lleva `AnalysisProvenance` — se define como un tipo de resultado propio
(`analysis_id`, `findings`, `supporting_metrics`, `limitations`), sin
forzar el contrato `AnalysisResult`. Su incorporación al `ResearchResult`
común queda como tarea separada y posterior ("Orquestador", Fase 4).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_analysis_engines_news_assembly.py`

Modificados:
- `investmentops/analysis_engines/news_relevance.py` (agregado
  `AGENT_ID`, `NewsRelevanceResult`, `assemble_news_relevance_analysis`
  y sus helpers internos `_build_no_relevant_news_warning`/
  `_describe_relevant_news_count`; `filter_relevant_news` y
  `select_news_summary` no cambiaron)
- `TASKS.md` (una línea: tarea de ensamblado del motor de noticias
  relevantes marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Orquestador" → "Registrar el nuevo proveedor de noticias sin
modificar los proveedores existentes."