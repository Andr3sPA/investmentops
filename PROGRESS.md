# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Normalización → *"Extender el modelo 'Estados financieros
normalizados' para incluir series temporales (no solo el dato más
reciente)."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo
anterior: `FinancialStatement` (Fase 1, `investmentops/data_layer/financial_statements.py`)
sigue representando deliberadamente un único corte —el más reciente—
por empresa, y su propio docstring ya dejaba anotado que extenderlo a
series temporales era alcance explícito y posterior de la Fase 3 (no
adelantado en Fase 1 para no sobre-diseñar antes de tener la fuente de
datos histórica y el motor de análisis de evolución que la
consumirían). No existía ningún tipo de dominio para series temporales
en el proyecto. Era trabajo nuevo.

## Qué se implementó

**`investmentops/data_layer/financial_statement_series.py`** (nuevo):

- `FinancialStatementSeries`: dataclass inmutable (`frozen=True`) con
  dos campos: `ticker: str` y `statements: Sequence[FinancialStatement]`.
- **Decisión de diseño:** en vez de introducir un tipo nuevo por punto
  de la serie, se reutiliza `FinancialStatement` (ya definido en Fase
  1) tal cual para cada elemento: sus campos (`revenue`, `net_income`,
  `debt`, `source`, `period_end`) ya son exactamente los que necesita
  cada corte histórico, y esto evita duplicar una estructura casi
  idéntica. `statements` se espera ordenada del periodo más reciente al
  más antiguo, mismo orden que ya devuelve FMP y que ya asume
  `financial_statement_from_raw` (Fase 1) para el corte único.
- **Deliberadamente fuera de alcance de esta tarea de estructura:**
  validación de huecos/duplicados/orden en la serie, y conservar
  `queried_at` por punto (es metadato de la *consulta*, no del *dato
  financiero* en sí — mismo criterio que ya aplica `FinancialStatement`
  para el corte único de Fase 1, que tampoco lo conserva). Ambas quedan
  para la tarea siguiente ("Implementar la transformación de la
  respuesta cruda histórica al modelo de series temporales") o para el
  futuro motor de análisis de evolución.

**`investmentops/data_layer/__init__.py`** (modificado): re-exporta
`FinancialStatementSeries`, siguiendo el mismo patrón ya usado para
`Company`, `FinancialStatement` y `MarketData`.

**`investmentops/tests/test_data_layer_financial_statement_series.py`**
(nuevo): confirma que la serie guarda `ticker` y `statements` tal
cual, que preserva el orden entregado (sin reordenar ni validar), que
es inmutable, que soporta un único punto, y que el `source` de cada
punto se conserva vía `FinancialStatement.source` sin necesitar un
campo de procedencia adicional en la serie.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/financial_statement_series.py` (nuevo)
- `investmentops/tests/test_data_layer_financial_statement_series.py` (nuevo)

Modificados:
- `investmentops/data_layer/__init__.py` (re-exporta `FinancialStatementSeries`)
- `TASKS.md` (tarea marcada como completada, Fase 3, "Normalización")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/data_layer/financial_statements.py` (el modelo de Fase 1
no cambió; la serie lo envuelve, no lo reemplaza ni lo modifica),
`investmentops/data_layer/normalization.py`,
`investmentops/data_providers/fundamentals.py`, ningún otro módulo de
código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Con la estructura de `FinancialStatementSeries` ya definida, la
siguiente tarea pendiente de la misma sección ("Normalización", Fase 3)
es:

> "Implementar la transformación de la respuesta cruda histórica al
> modelo de series temporales."

Esta tarea deberá construir una función (siguiendo el mismo patrón ya
usado por `financial_statement_from_raw` en
`investmentops/data_layer/normalization.py`) que traduzca el
`RawProviderData` devuelto por `FMPFundamentalsProvider.fetch_historical`
(cuyos puntos ya llevan procedencia individual — `"source"`,
`"queried_at"` — adjuntada en la tarea anterior) a un
`FinancialStatementSeries`, construyendo un `FinancialStatement` por
cada elemento de `payload["income_statement"]`/`payload["balance_sheet_statement"]`
combinados por fecha, y señalando `NormalizationError` (reutilizada de
`normalization.py`) ante campos imprescindibles ausentes o fechas no
interpretables, mismo criterio ya aplicado para el corte único.
