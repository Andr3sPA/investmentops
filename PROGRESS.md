# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar la
invocación al proveedor de IA configurado para el agente 'calidad',
enviando los datos normalizados ya existentes junto con el prompt."
(TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/quality.py` (nuevo): `AGENT_ID = "quality"`
y `invoke_quality_agent(statement, health_metrics, *, config=None)`.
Sigue exactamente el mismo patrón ya usado por `invoke_value_agent`
(`investmentops.analysis_engines.value`) e `invoke_growth_agent`
(`investmentops.analysis_engines.growth`): carga el prompt desde
`prompts/quality.md`, resuelve el proveedor/modelo configurado para el
agente `"quality"`, construye la instancia concreta de `AIProvider`, e
invoca `complete(prompt, data=...)`.

Sobre el mapeo de datos ya fijado en `STRATEGY_DATA_MAPPING.md`, este
agente envía como `data` únicamente el `FinancialStatement` normalizado
y las `FinancialHealthMetrics` ya calculadas por
`calculate_financial_health_metrics` (Fase 1) — `net_margin`,
`debt_to_revenue`, más sus `warnings` — sin recalcular nada. A
diferencia del agente "value", no utiliza `MarketData` ni
`ValuationMetrics`: la lectura de calidad se limita a la solidez
financiera subyacente, no a la valoración de mercado.

Devuelve el `AIProviderResponse` crudo; no parsea la respuesta a
`AnalysisResult` (esa es la tarea siguiente y separada de esta misma
sección).

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/quality.py`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'calidad' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no un
  veredicto)."