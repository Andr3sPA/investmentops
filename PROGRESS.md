# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 6, "Motores de análisis por estrategia" → "Implementar la
invocación al proveedor de IA configurado para el agente 'value',
enviando los datos normalizados ya existentes (sin nuevas fuentes ni
cálculos adicionales) junto con el prompt." (TASKS.md).

### Qué se implementó

`investmentops/analysis_engines/value.py` (nuevo): `AGENT_ID = "value"`
e `invoke_value_agent(market_data, statement, valuation_metrics,
health_metrics, *, config=None) -> AIProviderResponse`, siguiendo
exactamente el mismo patrón ya usado por
`invoke_financial_health_agent`/`invoke_valuation_agent` (Fase 1):

1. Carga el prompt desde `prompts/value.md` (`load_prompt("value")`).
2. Resuelve el proveedor/modelo configurado para el agente `"value"`
   (`resolve_agent_provider`).
3. Construye la instancia concreta de `AIProvider`
   (`build_ai_provider`).
4. Invoca `complete(prompt, data=...)`, enviando como `data`:
   `market_data` y `financial_statement` normalizados, más las
   `valuation_metrics` (`price_to_earnings`, `price_to_sales`) y
   `financial_health_metrics` (`net_margin`, `debt_to_revenue`) ya
   calculadas de forma determinística en Fase 1 — reutilizadas tal
   cual, sin recalcularlas, conforme a `STRATEGY_DATA_MAPPING.md`
   ("ningún cálculo nuevo, solo reinterpretación").

Devuelve el `AIProviderResponse` crudo, sin parsear: el parseo a un
resultado estructurado del agente es la tarea siguiente y separada de
la misma sección.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/value.py`
- `investmentops/tests/test_analysis_engines_value_invoke.py`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 6, "Motores de análisis por estrategia":
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'value' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no
  un veredicto)."