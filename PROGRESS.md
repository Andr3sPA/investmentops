# PROGRESS.md

**Última actualización:** 2026-07-23

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar la
invocación al proveedor de IA configurado para el agente 'growth',
enviando los datos normalizados ya existentes junto con el prompt."
(TASKS.md).

### Qué se implementó

`invoke_growth_agent`/`AGENT_ID` en
`investmentops/analysis_engines/growth.py` (nuevo). Mismo patrón ya
usado por `invoke_value_agent` (Fase 6, estrategia "value"):

1. Carga el prompt del agente desde `prompts/growth.md` (ya escrito en
   la tarea anterior de esta misma sección).
2. Resuelve el proveedor/modelo configurado para el agente ``"growth"``
   vía `resolve_agent_provider`.
3. Construye la instancia concreta de `AIProvider` vía
   `build_ai_provider`.
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   el resultado ya calculado de forma determinística por
   `assemble_trend_analysis` (Fase 3): `revenue_trend`,
   `net_income_trend`, `revenue_growth_by_period`,
   `net_income_growth_by_period` (de `TrendAnalysisResult.supporting_metrics`)
   y las advertencias ya producidas (`TrendAnalysisResult.limitations`),
   sin recalcular nada — sobre el mapeo de datos ya fijado en
   `STRATEGY_DATA_MAPPING.md` ("Growth").

Devuelve el `AIProviderResponse` crudo, sin parsear: el parseo a
`AnalysisResult` es la tarea siguiente de esta misma sección.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/growth.py`
- `investmentops/tests/test_analysis_engines_growth_invoke.py`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'growth' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no un
  veredicto)."