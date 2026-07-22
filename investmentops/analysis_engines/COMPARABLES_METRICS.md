# Posicionamiento relativo — qué métricas se comparan lado a lado (Fase 5)

Cubre la tarea "Definir qué métricas clave se comparan lado a lado (ej.
valoración, márgenes, crecimiento)" (TASKS.md, Fase 5, "Motor de
análisis: posicionamiento relativo").

Esta tarea es de **diseño/documentación**, no de código: decide qué
métricas concretas comparará el futuro motor de posicionamiento relativo
entre la empresa investigada y sus pares, a partir de los campos que
**hoy** expone el modelo de dominio normalizado `Comparables`/
`PeerComparable` (`investmentops/data_layer/comparables.py`): cada par
trae un único corte de `FinancialStatement` (`revenue`, `net_income`,
`debt`, `source`, `period_end`) y `MarketData` (`price`, `market_cap`,
`multiples` —vacío por diseño—, `source`, `as_of`), exactamente los
mismos modelos ya normalizados para la propia empresa investigada desde
la Fase 1.

## Restricción de partida: reutilizar métricas ya definidas, no inventar nuevas

Este proyecto ya definió y calculó, en fases anteriores, exactamente las
métricas de rentabilidad/endeudamiento (`FINANCIAL_HEALTH_METRICS.md`,
Fase 1) y de valoración (`VALUATION_METRICS.md`, Fase 1) que son
calculables con los campos disponibles en `FinancialStatement`/
`MarketData`. El motor de posicionamiento relativo no necesita —ni debe—
definir un conjunto de métricas nuevo y paralelo: los pares
(`PeerComparable`) exponen exactamente los mismos dos modelos de dominio
normalizados que la empresa investigada, por lo que las mismas funciones
de cálculo determinístico ya implementadas (`calculate_financial_health_metrics`
en `investmentops/analysis_engines/financial_health.py`,
`calculate_valuation_metrics` en
`investmentops/analysis_engines/valuation.py`) ya sirven, sin
modificación, para calcular esas métricas también para cada par.

Esto es consistente con el principio de `ARCHITECTURE.md`
("Extensibilidad sin reescritura") y con el criterio ya aplicado en
`COMPARABLES_PROVIDER.md` ("Las métricas de cada par ya son las que el
sistema ya sabe obtener y normalizar"): comparar significa aplicar el
mismo cálculo ya existente a cada empresa (investigada y pares), no
definir una fórmula nueva.

## Métricas elegidas para el MVP

### Rentabilidad

- **Margen neto** (`net_margin`) = `net_income / revenue`.
  Ya definida y calculada en `FINANCIAL_HEALTH_METRICS.md`/
  `calculate_financial_health_metrics`. Se calcula para la empresa
  investigada y para cada par, usando la misma función, sin
  duplicarla.

### Endeudamiento

- **Deuda sobre ingresos** (`debt_to_revenue`) = `debt / revenue`.
  Misma fórmula y función ya usada en Fase 1
  (`calculate_financial_health_metrics`), aplicada también a cada par.

### Valoración

- **Price/Earnings** (`price_to_earnings`) = `market_cap / net_income`.
- **Price/Sales** (`price_to_sales`) = `market_cap / revenue`.
  Ambas ya definidas y calculadas en `VALUATION_METRICS.md`/
  `calculate_valuation_metrics` (Fase 1), aplicadas también a cada par.

Las cuatro métricas comparten el mismo manejo de casos degenerados ya
decidido en sus tareas originales (periodo/beneficio en cero → `None`
con advertencia explícita, nunca `ZeroDivisionError` ni un valor
inventado): el motor de posicionamiento relativo no redefine ese
comportamiento, simplemente lo hereda al reutilizar las mismas
funciones.

## Métrica descartada: crecimiento

`TASKS.md` menciona "crecimiento" como ejemplo posible de qué podría
compararse lado a lado. Se **descarta explícitamente** para el MVP de
esta fase:

- El cálculo de crecimiento (variación periodo a periodo, ver
  `TREND_METRICS.md`, Fase 3) requiere una **serie histórica**
  (`FinancialStatementSeries`, con varios periodos), no un único corte.
- `Comparables`/`PeerComparable` (`investmentops/data_layer/comparables.py`)
  expone, por diseño, un único `FinancialStatement`/`MarketData` por
  par (mismo criterio ya documentado en ese módulo: "reutilizar
  `FinancialStatement`/`MarketData` por par", no una serie). No hay hoy
  ninguna fuente de datos que obtenga series históricas de cada empresa
  **par** (`FMPFundamentalsProvider.fetch_historical` solo se invoca hoy
  para la empresa investigada, ver
  `investmentops.core.orchestrator.run_trend_analysis_engine`).
- Aproximar "crecimiento" con un único corte (ej. comparando el
  `period_end` de un par contra otro sin serie) no sería una variación
  periodo a periodo real, sino una comparación de magnitud entre
  empresas de tamaños distintos — algo que ya cubren `net_margin`/
  `price_to_sales`, no una métrica de evolución en el tiempo. Inventar
  una aproximación aquí violaría el mismo principio ya aplicado en
  `FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md` (declarar
  honestamente lo que no se puede calcular, en vez de forzar un dato
  con información que no le corresponde).

Extender la consulta de comparables para traer series históricas de cada
par (y así poder comparar crecimiento) es una decisión que queda fuera
de esta tarea: no hay hoy un caso de uso ni una fuente de datos que lo
respalde, y anticiparlo sería sobre-diseñar antes de tener esa necesidad
concreta (mismo criterio ya aplicado repetidamente en el proyecto, ver
`investmentops/data_layer/market_data.py`).

## Decisión

Para el MVP de Fase 5, el motor de posicionamiento relativo comparará
**cuatro** métricas ya definidas y ya calculables con las funciones
existentes: `net_margin`, `debt_to_revenue` (rentabilidad/endeudamiento,
reutilizando `calculate_financial_health_metrics`) y
`price_to_earnings`, `price_to_sales` (valoración, reutilizando
`calculate_valuation_metrics`), aplicadas tanto a la empresa investigada
como a cada una de sus empresas pares. "Crecimiento" queda como
**limitación explícita**: el resultado del motor deberá declarar
honestamente que no se compara la evolución en el tiempo, ya que el
modelo de dominio de comparables no expone series históricas por par —
en vez de omitir el tema en silencio o aproximarlo con datos que no le
corresponden.

## Métricas resultantes (resumen)

| Categoría      | Métrica              | Fórmula                     | Función ya existente reutilizada          |
|----------------|------------------------|------------------------------|--------------------------------------------|
| Rentabilidad   | `net_margin`            | `net_income / revenue`       | `calculate_financial_health_metrics`       |
| Endeudamiento  | `debt_to_revenue`       | `debt / revenue`             | `calculate_financial_health_metrics`       |
| Valoración     | `price_to_earnings`    | `market_cap / net_income`    | `calculate_valuation_metrics`              |
| Valoración     | `price_to_sales`       | `market_cap / revenue`       | `calculate_valuation_metrics`              |
| Crecimiento    | —                       | —                             | No calculable (limitación: sin series por par) |

## Fuera de alcance de esta tarea

- El cálculo real de estas cuatro métricas para la empresa investigada y
  cada par, y el cálculo de la posición relativa entre ellas (tarea
  siguiente, "Implementar el cálculo de la posición relativa de la
  empresa frente a sus pares en cada métrica").
- El ensamblado del resultado estructurado del motor (hallazgos, tabla
  comparativa, advertencias si faltan datos de algún par): tarea
  separada y posterior en la misma sección.
- Extender `Comparables`/`FMPComparablesProvider` para traer series
  históricas por par (y así habilitar una futura comparación de
  crecimiento): fuera de alcance, sin caso de uso que lo justifique hoy.
- El prompt de este motor y su invocación al proveedor de IA (si en el
  futuro se decide que este motor también interprete sus métricas vía
  IA, siguiendo el patrón de salud financiera/valoración): no están
  desglosados todavía como tareas explícitas en `TASKS.md` para esta
  sección; se definirán si el diseño concreto lo requiere, mismo
  criterio ya aplicado por los motores de tendencia y noticias
  relevantes (Fases 3 y 4), que no invocan IA.