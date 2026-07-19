# InvestmentOps — Progreso

**Última actualización:** 2026-07-19

## Última tarea completada

Fase 3, "Orquestador" → "Decidir cómo se integra `TrendAnalysisResult`
(sin `AnalysisProvenance`) en `ResearchResult.analysis_results`... y
documentar la decisión, sin modificar código todavía" (TASKS.md).

Es una tarea de **diseño/documentación**, no de código: no se tocó
ningún archivo `.py`.

### Decisión tomada

`investmentops/core/TREND_INTEGRATION.md` (nuevo). Resumen:

- **No se modifica ningún contrato ya estable** (`AnalysisResult`,
  `AnalysisProvenance` en `investmentops/analysis_engines/contracts.py`,
  ni `ResearchResult` en `investmentops/core/research_result.py`).
  `ResearchResult.analysis_results` sigue siendo `Sequence[AnalysisResult]`.
- `TrendAnalysisResult` (`investmentops/analysis_engines/trends.py`,
  ya implementado en una tarea previa) se incorporará convirtiéndolo a
  un `AnalysisResult` normal mediante una función adaptadora, todavía
  sin implementar (eso es la tarea siguiente de esta misma sección).
- Esa conversión usará una `AnalysisProvenance` **centinela** explícita:
  `ai_provider="none"`, `ai_model="deterministic"`, `generated_at` =
  momento del ensamblado. No es un dato inventado: es una etiqueta
  honesta de que esa interpretación concreta no vino de un modelo de
  lenguaje (a diferencia de salud financiera/valoración), consistente
  con el principio de trazabilidad de `ARCHITECTURE.md`.
- Se descartó extender el contrato (`AnalysisResult.provenance`
  opcional, o tipar `analysis_results` como una unión de tipos) porque
  obligaría a modificar los tres consumidores ya estables
  (`render_markdown`, `render_html`, `format_research_result`) sin
  necesidad real, violando "Extensibilidad sin reescritura"
  (`ARCHITECTURE.md`).

Con esta decisión documentada, las tres subtareas de implementación que
le siguen en la misma sección de `TASKS.md` (obtener/normalizar la
serie histórica en el orquestador, registrar la invocación del motor,
incluir el resultado en `ResearchResult` con manejo de fallos
parciales) quedan desbloqueadas.

## Archivos creados o modificados

Creados:
- `investmentops/core/TREND_INTEGRATION.md`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia al nuevo
  documento de decisión)
- `PROGRESS.md` (este archivo)

No modificados: ningún archivo `.py` del proyecto, ni `ROADMAP.md`,
`GOALS.md`, `ARCHITECTURE.md`, `CONFIGURATION.md`,
`config.example.toml`, ni ningún archivo de prompt.

## Próxima tarea recomendada

Fase 3, "Orquestador" → "Implementar en el orquestador la función que
obtiene y normaliza la serie histórica de una empresa para un ticker
(encadenando `FMPFundamentalsProvider.fetch_historical` con
`financial_statement_series_from_raw`), como pieza reutilizable análoga
a `fetch_and_normalize`."

Es la primera tarea de implementación que depende de la decisión de
diseño recién documentada en `investmentops/core/TREND_INTEGRATION.md`.
