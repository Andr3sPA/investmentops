# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: salud financiera → *"Implementar el cálculo
determinístico de ratios de liquidez, endeudamiento y rentabilidad a
partir del modelo normalizado (entrada del agente, no su resultado
final)."*

Antes de implementarla, se revisó si ya existía algún cálculo de este
tipo en el proyecto (`investmentops/analysis_engines/`,
`investmentops/data_layer/financial_statements.py`) y se confirmó que
solo existía el contrato (`contracts.py`) y el documento de diseño
(`FINANCIAL_HEALTH_METRICS.md`) de la tarea anterior: ningún módulo
calculaba todavía `net_margin` ni `debt_to_revenue`. La tarea requería
trabajo nuevo.

## Qué se implementó

**`investmentops/analysis_engines/financial_health.py`** (nuevo) —
implementa exactamente las métricas ya decididas en
`FINANCIAL_HEALTH_METRICS.md`:

- `FinancialHealthMetrics`: dataclass inmutable con `net_margin`,
  `debt_to_revenue` y `warnings` (advertencias explícitas sobre métricas
  no calculables).
- `calculate_financial_health_metrics(statement)`: calcula
  `net_margin = net_income / revenue` y
  `debt_to_revenue = debt / revenue` en Python puro (sin invocar ningún
  proveedor de IA), a partir de un `FinancialStatement` ya normalizado.

**Manejo de `revenue == 0`:** en vez de dejar escapar un
`ZeroDivisionError` o inventar un valor (ej. `float("inf")`), la función
devuelve ambos ratios como `None` y agrega una advertencia explícita en
`FinancialHealthMetrics.warnings`, describiendo por qué no se pudieron
calcular. Esto sigue el mismo criterio de honestidad ante datos
degenerados/faltantes ya aplicado en el resto del proyecto (ver
`investmentops/data_layer/cache.py`, distinción entre "no cacheado" y
"cacheado pero corrupto").

**`investmentops/tests/test_analysis_engines_financial_health.py`**
(nuevo) — cubre: cálculo correcto de ambos ratios, soporte de
`net_income` negativo (empresa con pérdidas), manejo de `revenue == 0`
(ratios `None` + advertencia, sin `ZeroDivisionError`), inmutabilidad del
dataclass, y el caso de deuda cero (`debt_to_revenue == 0.0`, no `None`).

## Decisiones tomadas

- **Solo `net_margin` y `debt_to_revenue`, sin liquidez**, conforme a lo
  ya decidido en `FINANCIAL_HEALTH_METRICS.md`: no se agrega ninguna
  aproximación de liquidez en esta tarea. Esa limitación sigue viviendo
  únicamente en el documento de diseño; será el resultado del agente
  (`AnalysisResult.limitations`, tarea futura) quien la declare de cara
  al usuario.
- **`revenue == 0` se trata como caso degenerado explícito, no como error
  fatal ni como aproximación silenciosa.** Se devuelve `None` en ambos
  ratios más una advertencia legible en `warnings`, en vez de lanzar una
  excepción no controlada (que detendría el cálculo del agente sin
  necesidad) o de devolver un valor inventado que podría leerse como un
  dato real.
- **`warnings` es parte del resultado de esta función, no una excepción
  levantada.** A diferencia de `CacheError`/`NormalizationError` (que
  señalan datos corruptos o ausentes de forma imprevista), `revenue == 0`
  es un valor válido y posible en el modelo de dominio (una empresa sin
  ingresos reportados en el periodo); tratarlo como una excepción
  bloquearía innecesariamente el flujo del futuro agente.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/financial_health.py`
- `investmentops/tests/test_analysis_engines_financial_health.py`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`,
`investmentops/analysis_engines/__init__.py` (no se re-exporta esta
función a nivel de paquete, siguiendo el mismo criterio ya usado con
`investmentops.data_layer.cache`/`normalization`, que tampoco se
re-exportan desde `investmentops.data_layer`), y el resto del código
existente.

## Problemas encontrados

Ninguno. El único punto que requería una decisión explícita (`revenue ==
0`) ya estaba anticipado por la tarea anterior (ver nota de PROGRESS.md
previa) y se resolvió como advertencia explícita, no como bloqueo.

## Próxima tarea recomendada

La siguiente tarea sin empezar en la misma sección de `TASKS.md`
("Agente de análisis: salud financiera") es:

1. *"Escribir el archivo de prompt del agente de salud financiera (fuera
   del código Python), indicando cómo debe interpretar esas métricas."*

Nota para la próxima conversación:
- El prompt debe vivir en `prompts/financial_health.md` (ver
  `prompts/README.md`), en Markdown, y limitarse a instrucciones para el
  modelo de lenguaje sobre cómo interpretar `net_margin` y
  `debt_to_revenue` (y cómo manejar el caso en que alguno venga como
  `None`, con su advertencia asociada) — nunca debe pedir un veredicto de
  compra/venta, conforme a `GOALS.md` y `ARCHITECTURE.md`.
- El prompt debe mencionar explícitamente que no hay datos de liquidez
  disponibles para este análisis, para que el modelo no asuma que puede
  opinar sobre liquidez a partir de las métricas que sí recibe.
- No confundir esta tarea con la invocación al proveedor de IA (tarea
  siguiente en la misma sección): aquí solo se escribe el texto del
  prompt como archivo independiente, sin tocar
  `investmentops.ai_providers` ni construir ninguna llamada todavía.
