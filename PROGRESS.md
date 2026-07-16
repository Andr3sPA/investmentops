# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Modelo de reporte → *"Definir la estructura común que consumirán los generadores (a partir del 'Resultado de investigación')."*

Con esta tarea inicia la Fase 2 en `TASKS.md`.

## Verificación previa (sin duplicar trabajo)

Antes de escribir nada, se confirmó qué tan satisfecha estaba ya esta
tarea. `ARCHITECTURE.md`, sección "Modelo de datos interno (conceptual)",
ya documentaba desde la Fase 1 que "Resultado de investigación... es lo
que finalmente consumen los generadores de reportes". El propio
`ResearchResult`/`ResearchFailure`
(`investmentops/core/research_result.py`) ya existían con todos los
campos que un generador necesitaría: identidad de la empresa
(`Company`), los `AnalysisResult` de cada agente (con `findings`,
`supporting_metrics`, `limitations`, `provenance`), y los fallos
parciales (`ResearchFailure`).

Es decir: la **estructura en sí** ya existía y ya estaba documentada como
destino de los generadores. Pero esta tarea de `TASKS.md` (Fase 2,
"Modelo de reporte") pide explícitamente **definir/decidir** esa
estructura como parte del trabajo de esta fase — mismo patrón usado en
otras tareas de diseño del proyecto (`CACHE.md`, `VALUATION_METRICS.md`,
`FINANCIAL_HEALTH_METRICS.md`, `CONFIGURATION.md`): dejar la decisión
registrada explícitamente, no solo inferible de otro documento, para que
ninguna conversación futura reintroduzca una estructura intermedia
redundante sin saber que ya se evaluó y se descartó.

Por eso esta tarea sí requería un artefacto nuevo (un documento de
decisión), aunque no requiriera ningún código Python nuevo.

## Qué se implementó

**`investmentops/reports/REPORT_MODEL.md`** (nuevo) — documento de
decisión que:

- Decide explícitamente que los generadores de reportes (Markdown, HTML,
  y JSON si aplica en el futuro) consumirán **directamente**
  `ResearchResult`, sin introducir ningún tipo intermedio nuevo
  (`ReportInput`, `ReportData`, etc.).
- Justifica la decisión citando `ARCHITECTURE.md` y el propio docstring
  de `research_result.py`, que ya anticipaban este uso desde la Fase 1.
- Incluye una tabla explícita que mapea cada sección de reporte prevista
  en `TASKS.md`/`ROADMAP.md` (identidad de la empresa, salud financiera,
  valoración, fuentes/procedencia de IA, fallos/limitaciones) al campo
  concreto de `ResearchResult` del que sale, confirmando que no falta
  ningún dato.
- Documenta el criterio de "no sobre-diseñar antes de tener el caso de
  uso real" (ya aplicado en otros módulos del proyecto) como motivo para
  no crear una capa de indirección sin beneficio demostrado todavía.
- Deja explícitamente fuera de alcance: qué secciones concretas tendrá
  el reporte y en qué orden (tarea siguiente en la misma sección de
  `TASKS.md`), la implementación de cualquier plantilla concreta, el
  agente de reporte opcional, y la serialización a JSON.

## Decisiones tomadas

- **Reutilizar `ResearchResult` tal cual, sin tipo intermedio nuevo.**
  Introducir una estructura de "modelo de reporte" separada antes de
  escribir la primera plantilla concreta habría sido anticipar una
  necesidad no demostrada. Si en el futuro un generador necesita un dato
  derivado que `ResearchResult` no expone, esa sería una extensión
  explícita y posterior de esta decisión, documentada cuando surja el
  caso de uso real.
- **Documentar la decisión aunque la estructura ya existiera.** Se
  consideró marcar la tarea como satisfecha sin ningún artefacto nuevo
  (ya que `ARCHITECTURE.md` ya decía que `ResearchResult` es lo que
  consumen los generadores), pero se prefirió dejar un documento
  explícito de esta fase, siguiendo el mismo patrón ya establecido en el
  proyecto para tareas de "definir estructura/mecanismo" (ver `CACHE.md`,
  `VALUATION_METRICS.md`), para que quede trazable como parte del trabajo
  de la Fase 2 y no se pierda en un documento de una fase anterior.

## Archivos creados o modificados

Creados:
- `investmentops/reports/REPORT_MODEL.md` (nuevo)

Modificados:
- `TASKS.md` (tarea "Definir la estructura común que consumirán los
  generadores..." marcada como completada, Fase 2, "Modelo de reporte")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, ningún módulo de código
Python existente (esta tarea es puramente de diseño/documentación, sin
cambios de código).

## Problemas encontrados

Ninguno. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`); no aplica a esta tarea, que no agrega pruebas.

## Próxima tarea recomendada

Fase 2 → Modelo de reporte → *"Definir qué secciones tendrá el reporte
(identidad de la empresa, salud financiera, valoración, fuentes y fecha
de cada dato, incluyendo qué proveedor de IA generó cada
interpretación)."*

Esta tarea sigue siendo de diseño/documentación (no de código): decidir
el orden y contenido exacto de cada sección antes de implementar la
primera plantilla concreta (Generador Markdown, tarea siguiente en esa
misma sección). `REPORT_MODEL.md` (esta tarea) ya deja mapeadas las
secciones a los campos de `ResearchResult`; la tarea siguiente debe fijar
el orden de presentación y el nivel de detalle de cada una.
