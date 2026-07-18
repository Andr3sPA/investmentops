# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 3 → Motor de análisis: evolución de ingresos y beneficios →
*"Definir qué se considera 'tendencia' (ej. crecimiento interanual,
aceleración/desaceleración) a nivel básico."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha por trabajo anterior:
no existía ningún documento (`TREND_METRICS.md` u otro) que definiera qué
constituye "tendencia" para el futuro motor de análisis de evolución de
ingresos y beneficios. `FinancialStatementSeries` (Fase 3, "Normalización")
ya existe como modelo de dominio de entrada, pero ningún motor de
análisis lo consume todavía. Era trabajo nuevo, no una tarea ya cubierta.

## Qué se implementó

Esta es una tarea de **diseño/documentación**, no de código, mismo tipo
de tarea que `FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md` en
Fase 1.

**`investmentops/analysis_engines/TREND_METRICS.md`** (nuevo):

- **Métrica base:** variación relativa periodo a periodo, calculada por
  separado para ingresos y beneficios:
  `growth = (valor_t - valor_{t-1}) / abs(valor_{t-1})`, usando `abs(...)`
  en el denominador para que el signo del resultado siempre refleje
  mejora/deterioro real, incluso con periodos base negativos (ej. una
  empresa que reduce sus pérdidas). Se calcula para **cada par
  consecutivo** de `FinancialStatementSeries.statements`, no solo entre
  el periodo más reciente y el anterior.
- **Clasificación de tendencia (por salto):** creciente (`> 0`),
  decreciente (`< 0`), estable (`== 0`), basada en el signo puro, sin
  banda de tolerancia arbitraria (se documenta explícitamente por qué no
  se inventa un umbral sin caso de uso que lo justifique).
- **Aceleración/desaceleración** (mencionado como ejemplo en el título de
  la tarea de `TASKS.md`): se descarta explícitamente para el MVP, con
  justificación (exigiría comparar variación contra variación anterior,
  un umbral adicional arbitrario, y no es necesario para responder las
  preguntas 3/4 de `GOALS.md`).
- **Casos degenerados:** periodo base en cero (no calculable para ese
  salto, con advertencia explícita, mismo criterio ya usado en
  `FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md` para división por
  cero) y serie de un solo periodo (sin variación calculable; debe
  declararse como limitación explícita, no como error). Se aclara también
  que esta definición no distingue huecos reales en el calendario de
  pares simplemente consecutivos en la lista — eso es responsabilidad de
  la tarea de ensamblado del motor, ya prevista por separado en
  `TASKS.md`.
- **Fuera de alcance:** el cálculo determinístico real (próximas dos
  tareas de la misma sección), la detección de tendencia agregada para
  toda la serie (tarea siguiente a esas), el ensamblado del resultado
  estructurado del motor, el prompt/invocación de IA (si aplica), y
  cualquier umbral de tolerancia/CAGR/proyecciones/suavizado estadístico.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/TREND_METRICS.md` (nuevo)

Modificados:
- `TASKS.md` (tarea marcada como completada, Fase 3, "Motor de análisis:
  evolución de ingresos y beneficios")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, ningún módulo de código Python
existente (esta tarea es puramente de diseño/documentación, sin
implementación).

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Con la definición de "tendencia" ya fijada, la siguiente tarea pendiente
en la misma sección de `TASKS.md` ("Motor de análisis: evolución de
ingresos y beneficios") es:

> "Implementar el cálculo de variación periodo a periodo de ingresos."

Esta es la primera tarea de **implementación** de código de esta
sección: deberá calcular `revenue_growth` para cada par consecutivo de
`FinancialStatementSeries.statements`, siguiendo exactamente la fórmula y
el manejo de casos degenerados (periodo base en cero, serie de un solo
punto) ya fijados en `investmentops/analysis_engines/TREND_METRICS.md`,
con el mismo patrón ya usado en `calculate_financial_health_metrics`/
`calculate_valuation_metrics` (dataclass de resultado inmutable +
advertencias explícitas, sin lanzar `ZeroDivisionError` ni inventar
valores).
