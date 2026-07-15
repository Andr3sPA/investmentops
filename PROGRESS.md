# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: valoración → *"Definir qué múltiplos
concretos componen 'valoración básica' (ej. P/E, P/B)."*

Antes de implementarla, se verificó que no estuviera ya satisfecha: nada
en el proyecto decide todavía qué múltiplos calcula el agente de
valoración (`MarketData.multiples` sigue vacío por diseño, ver
`market_data.py` y `normalization.py`). Se confirmó que la tarea
requería trabajo nuevo, y que —al ser una tarea de diseño/documentación,
igual que `FINANCIAL_HEALTH_METRICS.md` lo fue para salud financiera—
no correspondía escribir código todavía.

## Qué se implementó

**`investmentops/analysis_engines/VALUATION_METRICS.md`** (nuevo) —
documento de decisión que analiza qué múltiplos de valoración son
calculables con los campos que **hoy** exponen `MarketData` (`price`,
`market_cap`, `multiples` vacío, `source`, `as_of`) y
`FinancialStatement` (`revenue`, `net_income`, `debt`, `source`,
`period_end`), sin inventar ni aproximar campos ausentes:

- **Hallazgo clave:** aunque ningún modelo expone `shares_outstanding`,
  P/E y P/S sí son calculables usando cifras **agregadas** en vez de "por
  acción", ya que `market_cap = price × shares`:
  - `price_to_earnings = market_cap / net_income`
  - `price_to_sales = market_cap / revenue`
  Ambas fórmulas son algebraicamente equivalentes a sus versiones
  clásicas por acción, sin depender de un dato que no existe hoy en el
  modelo de dominio.
- **P/B descartado (limitación explícita):** requiere patrimonio/valor
  en libros (`equity`), que `FinancialStatement` no expone (solo tiene
  `debt`, un concepto distinto y no intercambiable con patrimonio).
- **EV/EBITDA descartado (limitación explícita):** requiere EBITDA
  (ausente; solo hay `net_income`) y efectivo/equivalentes (ausente,
  para calcular el Enterprise Value completo).
- **Casos degenerados ya anticipados** (para la tarea de implementación
  siguiente): `net_income <= 0` hace que P/E no sea interpretable de
  forma estándar (se tratará como "no calculable" + advertencia, mismo
  criterio que `revenue == 0` en `FINANCIAL_HEALTH_METRICS.md`);
  `revenue == 0` hace lo mismo con P/S.

**Decisión final:** el agente de valoración calculará, en esta fase,
`price_to_earnings` y `price_to_sales`. P/B y EV/EBITDA quedan como
limitaciones explícitas que el futuro `AnalysisResult.limitations` del
agente de valoración deberá declarar, siguiendo el mismo patrón ya
usado para la liquidez en el agente de salud financiera.

No se modificó ningún archivo de código Python en esta tarea (es una
tarea de diseño/documentación pura, igual que
`FINANCIAL_HEALTH_METRICS.md` y `CACHE.md` lo fueron en su momento).

## Decisiones tomadas

- **P/E y P/S se expresan como `market_cap / net_income` y
  `market_cap / revenue`** (cifras agregadas), no como fórmulas "por
  acción" que requerirían `shares_outstanding`. Esto evita tener que
  extender el modelo de dominio (`MarketData`/`FinancialStatement`) antes
  de necesitarlo realmente, siguiendo el mismo criterio de no
  sobre-diseñar ya aplicado en el resto del proyecto (ver
  `market_data.py`, "no soporta series históricas").
- **P/B y EV/EBITDA no se aproximan con los campos disponibles** (por
  ejemplo, usando `debt` como sustituto de `equity`, o `net_income` como
  sustituto de `EBITDA`). Se documentan como limitaciones explícitas,
  igual principio que la liquidez en `FINANCIAL_HEALTH_METRICS.md`:
  declarar honestamente lo que no se puede calcular en vez de forzar una
  fórmula con datos que no le corresponden conceptualmente.
- **Los casos `net_income <= 0` y `revenue == 0` se anticipan aquí como
  decisión de diseño** (tratarlos como "no calculable" + advertencia),
  para que la tarea de implementación siguiente los resuelva de forma
  consistente con el precedente ya sentado por
  `calculate_financial_health_metrics` (revenue == 0 → None + warning),
  sin tener que re-decidir el criterio en esa tarea.

## Validación realizada

Tarea de diseño/documentación, sin código nuevo que ejecutar. Se revisó
manualmente la equivalencia algebraica de `market_cap / net_income` y
`market_cap / revenue` con sus versiones "por acción" tradicionales, y se
confirmó contra los campos reales de `MarketData`
(`investmentops/data_layer/market_data.py`) y `FinancialStatement`
(`investmentops/data_layer/financial_statements.py`) que ningún campo
adicional (`equity`, `ebitda`, `cash`, `shares_outstanding`) existe hoy
en el modelo de dominio.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/VALUATION_METRICS.md`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`prompts/financial_health.md`, ningún módulo de código Python existente
(`investmentops/analysis_engines/financial_health.py`,
`investmentops/data_layer/*`, `investmentops/ai_providers/*`, etc.).

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Agente de análisis: valoración" es:

1. *"Implementar el cálculo determinístico de esos múltiplos a partir
   del modelo normalizado."*

Nota para la próxima conversación:
- Implementar una función análoga a
  `calculate_financial_health_metrics`/`FinancialHealthMetrics` (ver
  `investmentops/analysis_engines/financial_health.py`), pero para
  valoración: recibirá un `MarketData` y un `FinancialStatement`, y
  devolverá un dataclass inmutable (ej. `ValuationMetrics`) con
  `price_to_earnings`, `price_to_sales` y `warnings`.
- Seguir el mismo criterio ya sentado en `VALUATION_METRICS.md` y en
  `calculate_financial_health_metrics` para los casos degenerados:
  `net_income <= 0` → `price_to_earnings = None` + advertencia explícita
  (sin lanzar excepción ni inventar un valor); `revenue == 0` →
  `price_to_sales = None` + advertencia explícita.
  Decidir si ambos casos degenerados pueden coexistir en la misma
  llamada (ej. `net_income <= 0` y `revenue == 0` a la vez) y si
  `warnings` debe listar ambas advertencias en ese caso.
- No calcular P/B ni EV/EBITDA (limitaciones ya documentadas en
  `VALUATION_METRICS.md`); esas limitaciones se declararán más adelante
  en `AnalysisResult.limitations`, en la tarea de parseo de la respuesta
  del agente (no en esta tarea de cálculo determinístico).
