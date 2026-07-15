# Valoración básica — múltiplos (Fase 1)

Cubre la tarea "Definir qué múltiplos concretos componen 'valoración
básica' (ej. P/E, P/B)" (TASKS.md, Fase 1, "Agente de análisis:
valoración").

Esta tarea es de **diseño/documentación**, no de código: decide qué
múltiplos de valoración calculará de forma determinística el agente de
valoración (implementación en la tarea siguiente, "Implementar el
cálculo determinístico de esos múltiplos"), a partir de los campos que
**hoy** exponen los modelos de dominio normalizados `MarketData`
(`investmentops/data_layer/market_data.py`: `price`, `market_cap`,
`multiples` —vacío por diseño—, `source`, `as_of`) y
`FinancialStatement` (`investmentops/data_layer/financial_statements.py`:
`revenue`, `net_income`, `debt`, `source`, `period_end`).

## Restricción de partida: no hay `shares_outstanding`

Los múltiplos de valoración "por acción" clásicos (P/E, P/S expresados
como precio por acción sobre beneficio/ingreso por acción) normalmente
requieren el número de acciones en circulación (`shares_outstanding`),
que **ningún** modelo de dominio actual expone. Sin embargo, esto no
impide calcular P/E y P/S: pueden expresarse de forma equivalente usando
cifras **agregadas** (capitalización de mercado y beneficio/ingreso
total de la empresa), sin necesidad de shares_outstanding:

- `P/E = precio / beneficio_por_acción = (precio × acciones) / beneficio_neto = market_cap / net_income`
- `P/S = precio / ingreso_por_acción = (precio × acciones) / ingresos = market_cap / revenue`

Ambas fórmulas son algebraicamente equivalentes a sus versiones "por
acción" tradicionales, sin depender de un dato que hoy no existe en el
modelo de dominio.

## Múltiplos elegidos para el MVP

### Price/Earnings (P/E)

- **Fórmula:** `price_to_earnings = market_cap / net_income`.
- Mide cuántas veces se está pagando el beneficio neto anual de la
  empresa. Calculable directamente con los campos existentes de
  `MarketData` y `FinancialStatement`.
- **Caso `net_income <= 0`:** un P/E con beneficio neto nulo o negativo
  no es un múltiplo interpretable de la forma habitual (la empresa no
  tiene ganancias que "pagar múltiples veces", o el resultado sería
  negativo y engañoso si se calcula sin más). Este caso se trata como
  "no calculable" con una advertencia explícita, igual criterio que
  `revenue == 0` en `FINANCIAL_HEALTH_METRICS.md`, en vez de devolver un
  número negativo o cero sin contexto.

### Price/Sales (P/S)

- **Fórmula:** `price_to_sales = market_cap / revenue`.
- Mide cuántas veces se está pagando el volumen de ingresos anuales de
  la empresa. Útil en particular cuando `net_income` no permite calcular
  P/E (empresas con pérdidas), ya que `revenue` rara vez es cero para una
  empresa en operación. Calculable directamente con los campos
  existentes.
- **Caso `revenue == 0`:** igual que en `FINANCIAL_HEALTH_METRICS.md`,
  se trata como "no calculable" con advertencia explícita (división por
  cero), no como una excepción no controlada.

## Múltiplo descartado: Price/Book (P/B)

- **Limitación conocida: no calculable con el modelo actual.** P/B
  requiere el valor en libros/patrimonio (`equity`/`book_value`) de la
  empresa. `FinancialStatement` solo expone `debt` (deuda), no
  patrimonio. Usar `debt` como sustituto de `equity` (por ejemplo,
  invirtiendo su signo o combinándolo de alguna forma) sería una
  aproximación inventada e incorrecta desde el punto de vista contable:
  deuda y patrimonio son conceptos distintos y no intercambiables. Esto
  violaría el mismo principio ya aplicado en `FINANCIAL_HEALTH_METRICS.md`
  para la liquidez: declarar honestamente lo que no se puede calcular,
  en vez de forzar una fórmula con datos que no le corresponden.

## Múltiplo descartado: EV/EBITDA

- **Limitación conocida: no calculable con el modelo actual.** Requiere
  EBITDA (beneficio antes de intereses, impuestos, depreciación y
  amortización), dato que `FinancialStatement` no expone (solo tiene
  `net_income`, la utilidad neta ya después de esos conceptos). Tampoco
  se dispone de efectivo/equivalentes para calcular el "Enterprise Value"
  completo (`EV = market_cap + debt - cash`); aunque `debt` sí está
  disponible, la ausencia de `cash` y de `EBITDA` hace que este múltiplo
  no pueda calcularse sin inventar datos. Queda como limitación
  explícita, no como una aproximación con datos parciales.

## Decisión

Para el MVP de Fase 1, el agente de valoración calculará
determinísticamente **dos** múltiplos: `price_to_earnings` (P/E) y
`price_to_sales` (P/S), ambos derivables de `MarketData.market_cap`
combinado con `FinancialStatement.net_income`/`FinancialStatement.revenue`
respectivamente, sin necesidad de `shares_outstanding`. P/B y EV/EBITDA
quedan como **limitaciones explícitas**: el resultado del agente
(`AnalysisResult.limitations`, ver
`investmentops/analysis_engines/contracts.py`) debe declarar
explícitamente que no se dispone de datos de patrimonio (para P/B) ni de
EBITDA/efectivo (para EV/EBITDA), en vez de omitir el tema en silencio o
forzar un múltiplo con datos que no le corresponden.

Extender `FinancialStatement`/`MarketData` para incluir `equity`,
`ebitda` o `cash` (y así poder calcular P/B o EV/EBITDA en una fase
posterior) es una decisión que queda fuera de esta tarea — ver "Fuera de
alcance" abajo.

## Múltiplos resultantes (resumen)

| Múltiplo | Fórmula                        | Estado                          |
|----------|----------------------------------|----------------------------------|
| P/E      | `market_cap / net_income`        | Calculable (con advertencia si `net_income <= 0`) |
| P/S      | `market_cap / revenue`           | Calculable (con advertencia si `revenue == 0`)    |
| P/B      | —                                 | No calculable (limitación: falta `equity`)        |
| EV/EBITDA| —                                 | No calculable (limitación: falta `ebitda`/`cash`) |

## Fuera de alcance de esta tarea

- El cálculo determinístico de `price_to_earnings` y `price_to_sales` a
  partir de un `MarketData`/`FinancialStatement` reales, incluyendo el
  manejo de `net_income <= 0` y `revenue == 0` (próxima tarea,
  "Implementar el cálculo determinístico de esos múltiplos a partir del
  modelo normalizado").
- Extender los modelos de dominio `FinancialStatement`/`MarketData` para
  incluir `equity`, `ebitda` o `cash` (y así resolver el gap de P/B o
  EV/EBITDA): sería una tarea separada y explícita, no anticipada aquí
  para no sobre-diseñar antes de que exista una fuente de datos real que
  la respalde.
- El prompt del agente de valoración y la invocación al proveedor de IA:
  tareas separadas y posteriores en la misma sección de `TASKS.md`.
- La comparación de estos múltiplos con el histórico de la propia
  empresa o con comparables del sector: fuera de alcance del MVP de esta
  fase (ver ROADMAP.md, Fase 5, "Comparar con empresas similares").
