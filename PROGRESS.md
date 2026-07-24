# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Orquestador" → "Incluir los resultados de cada estrategia en el
'Resultado de investigación' como entradas independientes y
contrastables." (TASKS.md).

### Qué se implementó

`investmentops/core/orchestrator.py` (modificado): `investigate` ahora
invoca también `run_value_engine`, `run_growth_engine` y
`run_quality_engine` (ya implementados en la tarea anterior), cada uno
en su propio `try/except` independiente, siguiendo el mismo espíritu ya
usado para salud financiera/valoración/tendencia/noticias relevantes:
un fallo de una estrategia nunca detiene las demás ni el resto del
flujo.

Diferencia clave respecto a los motores centinela (tendencia, noticias,
comparables): `run_value_engine`/`run_growth_engine`/`run_quality_engine`
ya devuelven un `AnalysisResult` con `AnalysisProvenance` real (proveedor
de IA genuino), por lo que se agregan a `analysis_results` tal cual, sin
ninguna conversión adicional.

Gating de cada estrategia:

- **`value`/`quality`**: solo se intentan si `provider is None` (uso
  real, sin un `DataProvider` de prueba inyectado). Ambas reutilizan
  `fetch_and_normalize`, igual que salud financiera/valoración, sin
  ninguna capacidad especial del proveedor; este gating evita que las
  numerosas pruebas ya existentes que inyectan un `DataProvider` mínimo
  (con `mock_post.side_effect` dimensionado para 2 llamadas) se rompan
  al intentar invocar IA para estrategias no anticipadas.
- **`growth`**: se intenta si `provider is None or
  hasattr(provider, "fetch_historical")`, misma condición ya usada por
  el motor de tendencia (necesita series históricas).

Cada `try/except` captura el conjunto completo de excepciones que puede
levantar la cadena obtención+normalización+IA de cada estrategia
(`DataProviderError`, `NormalizationError`, `PromptError`,
`AgentProviderSelectionError`, `AIProviderError`), clasificando el
`ResearchFailure` resultante como `stage="data_provider"` para los dos
primeros tipos y `stage="analysis_engine"` para el resto, con
`identifier` igual al `AGENT_ID` de la estrategia (`"value"`,
`"growth"`, `"quality"`).

No se modificó `run_value_engine`, `run_growth_engine`,
`run_quality_engine`, `run_analysis_engines`,
`run_trend_analysis_engine`, `run_news_relevance_engine` ni
`run_comparables_engine`.

Se agregó
`investmentops/tests/test_core_orchestrator_strategies_integration.py`.

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

Creados:
- `investmentops/tests/test_core_orchestrator_strategies_integration.py`

## Próxima tarea recomendada

Fase 6, "Reportes":
- "Añadir la sección 'Lecturas por estrategia de inversión' a la
  plantilla Markdown, presentando cada estrategia por separado."