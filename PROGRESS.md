# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: valoración → *"Implementar el cálculo
determinístico de esos múltiplos a partir del modelo normalizado."*

Antes de implementarla, se verificó que no estuviera ya satisfecha:
no existía ningún módulo `investmentops/analysis_engines/valuation.py`
ni una estructura equivalente a `ValuationMetrics`/
`calculate_valuation_metrics`. La tarea anterior ("Definir qué
múltiplos concretos componen 'valoración básica'") fue puramente de
diseño/documentación (`VALUATION_METRICS.md`), sin código; esta tarea sí
requería trabajo nuevo.

## Qué se implementó

**`investmentops/analysis_engines/valuation.py`** (nuevo) — cálculo
determinístico de los dos múltiplos ya decididos en
`VALUATION_METRICS.md`, siguiendo el mismo patrón ya usado por
`calculate_financial_health_metrics`/`FinancialHealthMetrics` en
`investmentops/analysis_engines/financial_health.py`:

- **`ValuationMetrics`** (`dataclass(frozen=True)`): `price_to_earnings`,
  `price_to_sales`, `warnings`.
- **`calculate_valuation_metrics(market_data, statement)`**:
  - `price_to_earnings = market_data.market_cap / statement.net_income`.
  - `price_to_sales = market_data.market_cap / statement.revenue`.
  - Si `statement.net_income <= 0`, `price_to_earnings` se devuelve como
    `None` con una advertencia explícita en `warnings` (un P/E con
    beneficio nulo o negativo no es interpretable de la forma habitual,
    conforme a lo ya anticipado en `VALUATION_METRICS.md`).
  - Si `statement.revenue == 0`, `price_to_sales` se devuelve como
    `None` con su propia advertencia explícita (división por cero).
  - Ambos casos degenerados pueden coexistir en la misma llamada: en ese
    caso `warnings` contiene ambas advertencias, una por cada métrica no
    calculable.
  - Nunca lanza `ZeroDivisionError` ni inventa un valor sustituto,
    mismo criterio ya sentado por `calculate_financial_health_metrics`
    para `revenue == 0`.

**`investmentops/tests/test_analysis_engines_valuation.py`** (nuevo) —
pruebas para: cálculo normal de ambos múltiplos; `net_income == 0`;
`net_income` negativo; `revenue == 0`; coexistencia de ambos casos
degenerados con dos advertencias; ausencia de `ZeroDivisionError`;
inmutabilidad de `ValuationMetrics`; `warnings` vacío en el caso feliz.

No se calculó P/B ni EV/EBITDA (limitaciones ya documentadas en
`VALUATION_METRICS.md`); esas limitaciones se declararán más adelante en
`AnalysisResult.limitations`, en la tarea de parseo de la respuesta del
agente (fuera de alcance de esta tarea).

## Decisiones tomadas

- **Mismo patrón que `financial_health.py`**: dataclass inmutable +
  función pura de cálculo, sin invocar ningún proveedor de IA, conforme
  a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un accesorio").
- **`net_income <= 0` (no solo `== 0`) invalida P/E**: decisión ya
  anticipada en `VALUATION_METRICS.md` ("un P/E con beneficio neto nulo
  o negativo no es un múltiplo interpretable de la forma habitual"), a
  diferencia de `debt_to_revenue` en salud financiera, que sí acepta
  `debt == 0` como un ratio válido de `0.0`. Aquí la condición es
  distinta porque un P/E negativo (empresa con pérdidas) sería engañoso
  sin contexto adicional, no simplemente "cero".
- **No se implementó todavía el resto del agente de valoración**
  (prompt, invocación al proveedor de IA, parseo de la respuesta):
  siguiendo la instrucción de implementar solo una tarea por conversación,
  y dado que cada una de esas piezas es una tarea separada y explícita
  en `TASKS.md`.

## Validación realizada

Pruebas unitarias nuevas en
`investmentops/tests/test_analysis_engines_valuation.py` cubriendo el
caso feliz, ambos casos degenerados por separado, su coexistencia,
ausencia de excepciones no controladas e inmutabilidad del dataclass.
No se ejecutó la suite completa en este entorno (Claude Web, sin acceso
al repositorio real); el código sigue el mismo patrón ya probado y
funcionando en `financial_health.py`.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/valuation.py`
- `investmentops/tests/test_analysis_engines_valuation.py`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`VALUATION_METRICS.md`, ningún módulo de código Python existente
(`investmentops/analysis_engines/financial_health.py`,
`investmentops/data_layer/*`, `investmentops/ai_providers/*`, etc.).

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Agente de análisis: valoración" es:

1. *"Escribir el archivo de prompt del agente de valoración (fuera del
   código Python)."*

Nota para la próxima conversación:
- Seguir el mismo patrón de `prompts/financial_health.md`: instruir al
  modelo a interpretar `price_to_earnings` y `price_to_sales` ya
  calculados (nunca recalcularlos), declarar explícitamente cuando
  vengan como `null`/ausentes (usando la advertencia entregada junto con
  los datos), y declarar la ausencia de datos para P/B y EV/EBITDA sin
  aproximarlos.
- Prohibir explícitamente cualquier recomendación de compra/venta o
  veredicto de inversión, igual que en `prompts/financial_health.md`.
- El archivo debe llamarse `prompts/valuation.md`, ya que
  `AGENT_ID = "valuation"` es el identificador natural para este agente
  (consistente con `[agents]` en `config.example.toml`, que ya trae
  `# valuation = "default"` como ejemplo comentado).
