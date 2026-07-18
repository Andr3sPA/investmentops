# Evolución de ingresos y beneficios — qué se considera "tendencia" (Fase 3)

Cubre la tarea "Definir qué se considera 'tendencia' (ej. crecimiento
interanual, aceleración/desaceleración) a nivel básico" (TASKS.md, Fase
3, "Motor de análisis: evolución de ingresos y beneficios").

Esta tarea es de **diseño/documentación**, no de código: decide qué
constituye "tendencia" para el MVP, a partir de los campos que **hoy**
expone el modelo de dominio `FinancialStatementSeries`
(`investmentops/data_layer/financial_statement_series.py`): una
secuencia ordenada de `FinancialStatement` (cada uno con `revenue`,
`net_income`, `debt`, `source`, `period_end`), del periodo más reciente
al más antiguo. El cálculo determinístico de estas métricas
(implementación) es la tarea siguiente de esta misma sección
("Implementar el cálculo de variación periodo a periodo de ingresos" /
"...de beneficios"); esta tarea solo fija la definición.

## Métrica base elegida: variación periodo a periodo (crecimiento interanual/intertrimestral)

Para cada par de periodos **consecutivos** de la serie (el periodo `t` y
el inmediatamente anterior `t-1`, en el mismo orden ya usado por
`FinancialStatementSeries.statements` — más reciente primero), se define
una única métrica de variación relativa, aplicada por separado a
ingresos y a beneficios:

- **Variación de ingresos:** `revenue_growth = (revenue_t - revenue_{t-1}) / abs(revenue_{t-1})`
- **Variación de beneficios:** `net_income_growth = (net_income_t - net_income_{t-1}) / abs(net_income_{t-1})`

Se usa `abs(...)` en el denominador (no `revenue_{t-1}`/`net_income_{t-1}`
directamente) para que el signo del resultado siempre refleje si la
cifra creció o decreció en términos absolutos, incluso cuando el periodo
base es negativo (ej. una empresa que pasa de una pérdida de -100 a una
pérdida de -50 tuvo una **mejora** de beneficios, y el resultado debe
ser positivo, no negativo por dividir entre un número negativo).

Se elige esta variación relativa —y no una diferencia absoluta
(`revenue_t - revenue_{t-1}`) sin normalizar— porque `GOALS.md` pide
identificar tendencias ("¿cómo han evolucionado sus ingresos/
beneficios?"), y una diferencia absoluta no es comparable entre empresas
de distinto tamaño ni entre ingresos y beneficios de la misma empresa
(magnitudes muy distintas). Es la misma lógica de "ratio, no cifra
cruda" ya aplicada en `FINANCIAL_HEALTH_METRICS.md` (`net_margin`,
`debt_to_revenue`) y `VALUATION_METRICS.md` (P/E, P/S).

Esta métrica se calcula para **cada par consecutivo** de la serie, no
solo entre el periodo más reciente y el anterior: una serie de 5 periodos
produce 4 variaciones (una por cada "salto" entre periodos consecutivos),
lo que es lo que permitirá, en la tarea siguiente de esta misma sección,
detectar si la tendencia es consistente a lo largo del tiempo o solo
puntual.

## Clasificación de tendencia: creciente / decreciente / estable

Para cada variación calculada (`revenue_growth` o `net_income_growth`
entre un par de periodos), se define una clasificación de tres valores,
basada únicamente en el **signo** del resultado:

- **Creciente:** `growth > 0`
- **Decreciente:** `growth < 0`
- **Estable:** `growth == 0` (caso exacto, no una banda de tolerancia)

Se elige el signo puro, sin una banda de tolerancia arbitraria (ej. "±2%
se considera estable"), porque no hay hoy ningún caso de uso ni
retroalimentación del usuario que justifique un umbral concreto — definir
una banda arbitraria sería inventar un criterio sin base, mismo tipo de
decisión que el proyecto ya evita en otros lugares (ver
`FINANCIAL_HEALTH_METRICS.md`, "no se inventa una aproximación"). Si en
el futuro se determina que un umbral es necesario (ej. variaciones
menores al 1% se perciben como ruido, no como tendencia real), esa sería
una extensión explícita y posterior de esta definición, no algo que deba
anticiparse aquí.

Esta clasificación es **por salto entre periodos consecutivos**, no un
resumen único de toda la serie: una serie con crecimiento en 3 de 4
saltos y una caída en el cuarto no se colapsa aquí en una única etiqueta
"creciente" — esa síntesis (si la tendencia general de la serie es
consistente o mixta) es explícitamente el alcance de la tarea siguiente
("Implementar la detección simple de tendencia... para cada serie"), no
de esta.

## "Aceleración/desaceleración": mencionado en `ROADMAP.md`/`TASKS.md`, descartado para el MVP

El título de la tarea en `TASKS.md` menciona
"aceleración/desaceleración" como ejemplo posible de qué podría
entenderse por tendencia. Se **descarta explícitamente** para el MVP de
esta fase:

- Detectar aceleración/desaceleración requeriría comparar la variación
  de un salto contra la variación del salto anterior (la "derivada" de la
  tasa de crecimiento), lo que exige al menos 3 periodos consecutivos
  completos y una definición adicional de qué diferencia se considera
  significativa — la misma clase de umbral arbitrario ya descartado
  arriba para "estable".
- `ROADMAP.md`, Fase 3, solo promete responder las preguntas 3 y 4 de
  `GOALS.md` ("¿Cómo han evolucionado sus ingresos/beneficios?"), que ya
  quedan cubiertas con la variación periodo a periodo y la clasificación
  de tres valores definidas arriba. Aceleración/desaceleración es una
  lectura más sofisticada que no es necesaria para responder esas dos
  preguntas concretas del MVP.

Si en una fase posterior se necesita esta lectura más fina, es una
extensión explícita y separada de esta definición, no parte del MVP de
la Fase 3.

## Manejo de casos degenerados (mismo criterio ya aplicado en Fase 1)

- **Periodo base en cero** (`revenue_{t-1} == 0` o `net_income_{t-1} ==
  0`): produciría una división por cero. Se trata como "no calculable"
  para ese salto concreto, con una advertencia explícita, en vez de
  lanzar una excepción o inventar un valor — mismo criterio ya aplicado
  en `calculate_financial_health_metrics`/`calculate_valuation_metrics`
  para `revenue == 0`/`net_income <= 0`.
- **Serie con un único periodo:** no hay ningún par consecutivo, por lo
  que no se puede calcular ninguna variación ni clasificación para esa
  serie. Este caso no es un error: una serie de un solo punto es válida
  según `FinancialStatementSeries` (ver su propio docstring), pero no
  contiene evolución que analizar. El motor de análisis debe declarar
  esta ausencia explícitamente (ej. como limitación en su
  `AnalysisResult`), no fallar ni omitir el tema en silencio.
- **Huecos en la serie** (periodos no consecutivos, ej. falta un año
  entre dos puntos disponibles): esta definición no distingue huecos de
  periodos verdaderamente consecutivos — trata cualquier par adyacente en
  `FinancialStatementSeries.statements` como "consecutivo" a efectos del
  cálculo, sin validar que sus fechas correspondan a periodos contiguos
  en el calendario (ej. año tras año sin saltos). Detectar y advertir
  sobre huecos reales es responsabilidad de la tarea de ensamblado del
  motor ("advertencias si hay huecos en la serie", ya prevista como tarea
  separada en `TASKS.md`), no de esta definición de métrica.

## Resumen de la definición

| Concepto                | Definición                                                              |
|--------------------------|---------------------------------------------------------------------------|
| Variación de ingresos     | `(revenue_t - revenue_{t-1}) / abs(revenue_{t-1})`, por cada par consecutivo |
| Variación de beneficios   | `(net_income_t - net_income_{t-1}) / abs(net_income_{t-1})`, por cada par consecutivo |
| Clasificación             | Creciente (`> 0`) / Decreciente (`< 0`) / Estable (`== 0`), por salto     |
| Aceleración/desaceleración| Fuera de alcance del MVP (ver sección dedicada arriba)                    |
| Periodo base en cero      | No calculable para ese salto, con advertencia explícita                   |
| Serie de un solo periodo  | Sin variación calculable; se declara como limitación explícita            |

## Fuera de alcance de esta tarea

- El cálculo determinístico real de `revenue_growth`/`net_income_growth`
  a partir de un `FinancialStatementSeries`: tareas siguientes en la
  misma sección de `TASKS.md` ("Implementar el cálculo de variación
  periodo a periodo de ingresos" / "...de beneficios").
- La detección de tendencia agregada para toda la serie (si el conjunto
  de saltos es consistentemente creciente, decreciente, o mixto): tarea
  separada y siguiente ("Implementar la detección simple de tendencia...
  para cada serie").
- El ensamblado del resultado estructurado del motor (hallazgos,
  métricas de soporte, advertencias por huecos): tarea separada y
  posterior en la misma sección.
- El prompt del agente de evolución de ingresos/beneficios (si este motor
  delega interpretación a un modelo de lenguaje, siguiendo el mismo
  patrón de salud financiera/valoración) y su invocación al proveedor de
  IA: no están desglosados todavía como tareas explícitas en `TASKS.md`
  para esta sección; se definirán si el diseño de este motor concreto lo
  requiere, siguiendo el patrón ya establecido en Fase 1.
- Cualquier umbral de tolerancia para "estable", CAGR, proyecciones o
  suavizado estadístico: descartados explícitamente para el MVP (ver
  arriba), no anticipados aquí.
