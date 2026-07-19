# InvestmentOps — Progreso

**Última actualización:** 2026-07-19

## Última tarea completada

Fase 3, "Orquestador" → "Implementar en el orquestador la función que
obtiene y normaliza la serie histórica de una empresa para un ticker
(encadenando `FMPFundamentalsProvider.fetch_historical` con
`financial_statement_series_from_raw`), como pieza reutilizable análoga
a `fetch_and_normalize`" (TASKS.md).

### Qué se implementó

`investmentops/core/orchestrator.py` gana dos funciones nuevas, sobre la
decisión de integración ya documentada en
`investmentops/core/TREND_INTEGRATION.md`:

- **`fetch_raw_historical_data(ticker, *, config=None, provider=None,
  period="annual", limit=5) -> RawProviderData`**: equivalente
  histórico de `fetch_raw_data` (Fase 1). En vez de invocar
  `DataProvider.fetch(ticker)`, invoca
  `FMPFundamentalsProvider.fetch_historical(ticker, period=period,
  limit=limit)`. Por defecto construye un `FMPFundamentalsProvider`
  (mismo proveedor ya elegido para el MVP); acepta un `provider`
  inyectado (pensado para pruebas) siempre que exponga un método
  `fetch_historical` con esa misma firma.
- **`fetch_and_normalize_historical(ticker, *, config=None,
  provider=None, period="annual", limit=5) -> FinancialStatementSeries`**:
  equivalente histórico de `fetch_and_normalize` (Fase 1). Encadena
  `fetch_raw_historical_data(ticker, ...)` con
  `investmentops.data_layer.normalization.financial_statement_series_from_raw`
  (ya implementada en una tarea previa de esta misma sección de la Fase
  3), devolviendo un `FinancialStatementSeries` listo para
  `investmentops.analysis_engines.trends.assemble_trend_analysis`.

Ninguna de las dos funciones captura `DataProviderError` ni
`NormalizationError`: las propagan tal cual, exactamente el mismo
criterio ya documentado para `fetch_raw_data`/`fetch_and_normalize`. El
manejo de fallos parciales sin detener el resto del flujo de
`investigate` queda para la tarea siguiente de esta misma sección
("Incluir el resultado de evolución de ingresos y beneficios en el
`ResearchResult` ensamblado... con manejo de fallos parciales").

`period`/`limit` se exponen con los mismos valores por defecto ya
elegidos en `FMPFundamentalsProvider.fetch_historical`
(`"annual"`/`5`), sin imponer un valor distinto desde el orquestador.

Se actualizó también el docstring del módulo (encabezado y nueva
sección "Obtención y normalización de la serie histórica") para dejar
documentada esta extensión junto a las siete piezas ya existentes del
mismo módulo (mismo criterio ya usado en el resto del archivo).

## Archivos creados o modificados

Modificados:
- `investmentops/core/orchestrator.py` (nuevas funciones
  `fetch_raw_historical_data`/`fetch_and_normalize_historical`, más
  imports de `financial_statement_series_from_raw` y
  `FinancialStatementSeries`; docstring del módulo actualizado)
- `TASKS.md` (tarea marcada como completada, con referencia a las
  funciones nuevas)
- `PROGRESS.md` (este archivo)

No modificados: ningún otro archivo `.py` del proyecto (no se tocó
`investmentops/analysis_engines/trends.py`,
`investmentops/data_layer/normalization.py`,
`investmentops/data_providers/fundamentals.py`, ni ningún contrato de
Fase 1/2), ni `ROADMAP.md`, `GOALS.md`, `ARCHITECTURE.md`,
`CONFIGURATION.md`, `config.example.toml`, ni ningún archivo de prompt.

## Próxima tarea recomendada

Fase 3, "Orquestador" → "Registrar la invocación de
`assemble_trend_analysis` en el flujo de análisis del orquestador,
conforme a la decisión de integración ya tomada, sin modificar los
motores existentes (salud financiera, valoración)."

Esta tarea consumirá `fetch_and_normalize_historical` (recién
implementada) y `assemble_trend_analysis`
(`investmentops.analysis_engines.trends`, ya implementada) para
construir el `AnalysisResult` centinela descrito en
`investmentops/core/TREND_INTEGRATION.md`, dejando la incorporación
final al `ResearchResult` (con manejo de fallos parciales) para la
tarea siguiente y separada de esta misma sección.
