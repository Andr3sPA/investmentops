# Salud financiera básica — métricas (Fase 1)

Cubre la tarea "Definir qué métricas concretas componen 'salud financiera
básica' (liquidez, endeudamiento, rentabilidad)" (TASKS.md, Fase 1,
"Agente de análisis: salud financiera").

Esta tarea es de **diseño/documentación**, no de código: decide qué
ratios concretos calculará de forma determinística el agente de salud
financiera (implementación en la tarea siguiente, "Implementar el
cálculo determinístico..."), a partir de los campos que **hoy** expone el
modelo de dominio normalizado `FinancialStatement`
(`investmentops/data_layer/financial_statements.py`): `revenue`,
`net_income`, `debt`, `source`, `period_end`.

## Métricas elegidas para el MVP

### Rentabilidad

- **Margen neto** (`net_margin`) = `net_income / revenue`.
  Mide qué proporción de los ingresos se convierte en beneficio neto.
  Calculable directamente con los campos existentes.

### Endeudamiento

- **Deuda sobre ingresos** (`debt_to_revenue`) = `debt / revenue`.
  Mide el tamaño de la deuda total en relación con el volumen de
  ingresos de la empresa. Se elige esta razón (y no deuda/patrimonio,
  "debt-to-equity", el ratio de endeudamiento más común) porque
  `FinancialStatement` no tiene un campo de patrimonio ("equity"); ver
  "Limitación conocida" más abajo.

### Liquidez

- **Limitación conocida: no calculable con el modelo actual.**
  Un ratio de liquidez estándar (ej. liquidez corriente = activos
  corrientes / pasivos corrientes) requiere campos que
  `FinancialStatement` no tiene hoy (`current_assets`,
  `current_liabilities`). Este módulo **no** inventa una aproximación
  con los campos disponibles (ej. usar `debt` como proxy de pasivos
  corrientes sería impreciso y engañoso): eso violaría el principio de
  `ARCHITECTURE.md`, "Manejo de errores y limitaciones" — declarar
  honestamente lo que no se puede calcular, en vez de inventar un dato.

## Decisión

Para el MVP de Fase 1, el agente de salud financiera calculará
determinísticamente **dos** de las tres categorías previstas en
`GOALS.md`/`ROADMAP.md` (rentabilidad y endeudamiento). La liquidez
queda como una **limitación explícita**: el resultado del agente
(`AnalysisResult.limitations`, ver
`investmentops/analysis_engines/contracts.py`) debe declarar
explícitamente que no se dispone de datos de liquidez, en vez de omitir
el tema en silencio o forzar un ratio con datos que no le corresponden.

Extender `FinancialStatement` para incluir `current_assets` y
`current_liabilities` (y así poder calcular liquidez en una fase
posterior) es una decisión que queda fuera de esta tarea — ver "Fuera de
alcance" abajo.

## Métricas resultantes (resumen)

| Categoría     | Métrica            | Fórmula                | Estado                        |
|---------------|---------------------|-------------------------|--------------------------------|
| Rentabilidad  | `net_margin`        | `net_income / revenue`  | Calculable                     |
| Endeudamiento | `debt_to_revenue`   | `debt / revenue`        | Calculable                     |
| Liquidez      | —                    | —                        | No calculable (limitación)     |

## Fuera de alcance de esta tarea

- El cálculo determinístico de `net_margin` y `debt_to_revenue` a partir
  de un `FinancialStatement` real (próxima tarea, "Implementar el
  cálculo determinístico de ratios de liquidez, endeudamiento y
  rentabilidad a partir del modelo normalizado").
- Extender el modelo de dominio `FinancialStatement` para incluir
  `current_assets`/`current_liabilities` (y así resolver el gap de
  liquidez): sería una tarea separada y explícita, no anticipada aquí
  para no sobre-diseñar antes de que exista una fuente de datos real que
  la respalde.
- El manejo del caso `revenue == 0` (división por cero) en el cálculo:
  corresponde a la implementación del cálculo determinístico, no a esta
  tarea de diseño.
- El prompt del agente de salud financiera y la invocación al proveedor
  de IA: tareas separadas y posteriores en la misma sección de
  `TASKS.md`.
