# Integración del motor de evolución de ingresos y beneficios en el
# "Resultado de investigación" (Fase 3)

Cubre la tarea "Decidir cómo se integra `TrendAnalysisResult` (sin
`AnalysisProvenance`) en `ResearchResult.analysis_results`... y
documentar la decisión, sin modificar código todavía" (TASKS.md, Fase 3,
"Orquestador").

Esta tarea es de **diseño/documentación**, no de código: decide cómo el
`TrendAnalysisResult` ya producido por
`investmentops.analysis_engines.trends.assemble_trend_analysis` se
incorporará a `ResearchResult.analysis_results`
(`investmentops/core/research_result.py`), antes de tocar el
orquestador (`investmentops/core/orchestrator.py`) en las tareas
siguientes de esta misma sección ("obtener y normalizar la serie
histórica", "registrar la invocación del motor", "incluir el resultado
en el `ResearchResult` con manejo de fallos parciales").

## El problema

`ResearchResult.analysis_results` está tipado como
`Sequence[AnalysisResult]` (ver
`investmentops/core/research_result.py`), y todo el sistema que ya
consume esa secuencia asume que cada elemento es un `AnalysisResult`
completo, incluyendo un campo `provenance: AnalysisProvenance`
obligatorio (`ai_provider`, `ai_model`, `generated_at`):

- `investmentops.reports.markdown.render_markdown` /
  `investmentops.reports.html.render_html`: ambos generadores buscan un
  análisis por `analysis_id` (`_find_analysis`) y, si lo encuentran,
  vuelcan incondicionalmente `analysis.provenance.ai_provider` /
  `.ai_model` / `.generated_at` como parte fija del cuerpo de la
  sección (ver `_render_analysis_body` / `_render_analysis_body_html`).
- `investmentops.cli.format_research_result`: imprime
  `analysis.provenance.ai_provider` / `.ai_model` para cada análisis,
  sin comprobar su presencia.

`TrendAnalysisResult` (`investmentops/analysis_engines/trends.py`), en
cambio, **no tiene** `provenance`: el motor de evolución de ingresos y
beneficios, tal como quedó implementado, no invoca ningún proveedor de
IA (sus hallazgos se generan por plantilla determinista a partir de la
tendencia agregada, ver "Por qué no se usa `AnalysisResult`/
`AnalysisProvenance`" en el docstring de `trends.py`). Forzar el
contrato `AnalysisResult` tal cual, sin resolver este desajuste,
significaría o (a) dejar `provenance` en un valor inventado sin
documentar qué significa, o (b) que el orquestador ni siquiera pueda
construir el objeto.

## Opciones evaluadas

**Opción A — Extender el contrato de `ResearchResult`/`AnalysisResult`**
para aceptar explícitamente resultados sin procedencia de IA (ej.
tipar `analysis_results` como `Sequence[AnalysisResult |
TrendAnalysisResult]`, o hacer `AnalysisResult.provenance` opcional).

- Descartada. Requeriría modificar `investmentops/analysis_engines/
  contracts.py` (contrato ya estable desde la Fase 1, con pruebas que
  exigen `provenance` como no-opcional, ver
  `test_analysis_engines_contracts.py`) y, en cascada, los tres
  consumidores ya listados (`render_markdown`, `render_html`,
  `format_research_result`), que tendrían que aprender a manejar la
  ausencia de `provenance` en cada punto donde hoy la dan por sentada.
  Es el tipo de cambio que `ARCHITECTURE.md` busca evitar
  ("Extensibilidad sin reescritura": añadir una capacidad no debería
  requerir modificar los consumidores ya existentes de un contrato
  estable).

**Opción B — Construir una `AnalysisProvenance` "centinela"** que
identifique honestamente el análisis como no generado por un modelo de
lenguaje, y envolver el contenido de `TrendAnalysisResult` en un
`AnalysisResult` normal antes de agregarlo a `analysis_results`.

- **Elegida.** Ver justificación abajo.

## Decisión: opción B — `AnalysisProvenance` centinela + conversión a `AnalysisResult`

`ResearchResult.analysis_results` **no cambia de tipo**: sigue siendo
`Sequence[AnalysisResult]`. El resultado del motor de tendencias se
incorpora convirtiéndolo a un `AnalysisResult` normal, con:

- `analysis_id`: `trends.AGENT_ID` (`"trend_analysis"`), tal cual ya lo
  expone `TrendAnalysisResult.analysis_id`.
- `findings`, `supporting_metrics`, `limitations`: tomados
  directamente de `TrendAnalysisResult`, sin transformarlos.
- `provenance`: una `AnalysisProvenance` centinela, con valores fijos y
  explícitos:
  - `ai_provider = "none"`
  - `ai_model = "deterministic"`
  - `generated_at`: el momento en que se ensambló el análisis (mismo
    criterio que ya usa `AnalysisProvenance.generated_at` para los
    demás agentes: cuándo se generó *esta* interpretación concreta, no
    cuándo se consultó el dato subyacente).

Esta construcción vivirá como una función de conversión explícita (ej.
`trend_analysis_to_analysis_result` o similar; el nombre y ubicación
exactos —`investmentops.analysis_engines.trends` vs.
`investmentops.core.orchestrator`— se deciden en la tarea de
implementación siguiente, no aquí) que **no modifica** ni
`TrendAnalysisResult` ni `AnalysisResult`/`AnalysisProvenance`: es
puramente un adaptador entre ambos tipos ya existentes.

### Por qué "centinela" y no "inventar procedencia de IA"

Este proyecto evita explícitamente inventar datos que no existen (ver
`FINANCIAL_HEALTH_METRICS.md`, `VALUATION_METRICS.md`: "no se inventa
una aproximación... eso sería impreciso y engañoso"). Ese principio
aplica a **cifras financieras** (un ratio de liquidez que no se puede
calcular, un múltiplo que no se puede derivar): rellenarlas con un
valor plausible sería engañoso porque el lector no podría distinguir un
dato real de uno inventado.

`ai_provider`/`ai_model` no son cifras financieras: son metadatos de
procedencia cuyo propósito, según `ARCHITECTURE.md`
("Reproducibilidad y trazabilidad"), es que el reporte pueda explicar
**de dónde salió** cada interpretación. Los valores `"none"` /
`"deterministic"` no fingen que un modelo de lenguaje generó esta
interpretación: la etiquetan honestamente como lo que es (cálculo
determinístico en código, sin IA), de la misma forma en que
`ProviderMetadata.reliability` ya usa texto libre (`"alta"`,
`"media"`, `"estimado"`) para describir la confiabilidad de un dato sin
inventar una cifra numérica de confianza que no existe. Esto es
consistente con el principio de `ARCHITECTURE.md`, "El sistema informa,
no decide": informar correctamente que *no* hubo IA involucrada es
parte de la trazabilidad exigida, no una violación de ella.

### Qué gana el sistema con esta decisión

- **Cero cambios en contratos ya estables** (`AnalysisResult`,
  `AnalysisProvenance`, `ResearchResult`): las pruebas de Fase 1 que
  los cubren (`test_analysis_engines_contracts.py`,
  `test_core_research_result.py`) siguen pasando sin modificación.
- **Cero cambios en los generadores de reporte ni en la CLI**
  (`render_markdown`, `render_html`, `format_research_result`): al
  recibir un `AnalysisResult` con `provenance` real (aunque centinela),
  la sección "Generado por: none (deterministic) el ..." se imprime
  con el mismo código ya existente, sin ramas condicionales nuevas.
- El texto `"none (deterministic)"` en el reporte es, en sí mismo,
  información útil para el usuario: le indica que esta sección en
  particular no fue interpretada por un modelo de lenguaje, a
  diferencia de "Salud financiera" y "Valoración".

## Alcance de la tarea de implementación siguiente

Esta decisión **no implementa** todavía la función de conversión ni
registra el motor en el orquestador. Las tareas siguientes de esta
misma sección de `TASKS.md` (ya desglosadas) se encargan de:

1. Implementar en el orquestador la obtención/normalización de la
   serie histórica de una empresa (análoga a `fetch_and_normalize`).
2. Registrar la invocación de `assemble_trend_analysis` en el flujo de
   análisis del orquestador.
3. Incluir el resultado (ya convertido a `AnalysisResult` según esta
   decisión) en el `ResearchResult` ensamblado, con manejo de fallos
   parciales (serie histórica no disponible, error de normalización)
   sin detener el resto del flujo — mismo criterio ya usado por
   `investigate` para salud financiera y valoración.

## Fuera de alcance de esta tarea

- La función de conversión concreta (`TrendAnalysisResult ->
  AnalysisResult`): implementación de la tarea siguiente.
- Cualquier cambio a `investmentops/analysis_engines/trends.py`,
  `investmentops/analysis_engines/contracts.py` o
  `investmentops/core/research_result.py`: ninguno de los tres se
  modifica como parte de esta decisión.
- La presentación de esta sección en los reportes Markdown/HTML: ya
  fijada como tarea separada y posterior en `TASKS.md`, Fase 3,
  "Reportes" (decidir formato de presentación de la serie, luego
  añadir la sección a cada plantilla).
