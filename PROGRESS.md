# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Modelo de reporte → *"Definir qué secciones tendrá el reporte
(identidad de la empresa, salud financiera, valoración, fuentes y fecha
de cada dato, incluyendo qué proveedor de IA generó cada
interpretación)."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba ya satisfecha:
`investmentops/reports/REPORT_MODEL.md` (tarea anterior) solo mapea
secciones a campos de `ResearchResult`, pero no fija el **orden de
presentación** ni el **nivel de detalle** de cada sección — el propio
`PROGRESS.md` (versión anterior) dejaba esto explícitamente como la
siguiente tarea recomendada. Por eso sí requería un artefacto nuevo.

## Qué se implementó

**`investmentops/reports/REPORT_SECTIONS.md`** (nuevo) — documento de
decisión que:

- Fija el orden de cuatro secciones que compartirán todos los formatos
  de reporte (Markdown, HTML, y JSON si aplica a futuro):
  1. Encabezado (identidad de la empresa + fecha de ensamblado).
  2. Salud financiera (hallazgos → métricas de soporte → limitaciones →
     procedencia de IA).
  3. Valoración (misma estructura que la sección anterior).
  4. Fallos parciales (solo si `ResearchResult.failures` no está vacío).
- Reutiliza el mismo orden ya usado por
  `investmentops.cli.format_research_result` (Fase 1, texto plano de
  consola), en vez de inventar un orden distinto para los generadores de
  reporte de la Fase 2.
- Documenta explícitamente una limitación real encontrada al diseñar
  esta tarea: `ResearchResult` expone la procedencia de la
  **interpretación de IA** (`AnalysisProvenance`: proveedor, modelo,
  fecha) pero no la fuente/fecha del **dato normalizado subyacente**
  (`FinancialStatement.source`/`period_end`, `MarketData.source`/`as_of`),
  ya que esos modelos no se propagan hacia `ResearchResult` (solo se
  usan internamente para calcular métricas). Se documenta como
  limitación aceptable para el MVP de esta fase (en Fase 1 solo existe un
  proveedor de datos fijo, FMP, por lo que la fuente es implícitamente
  uniforme), en vez de rediseñar `ResearchResult` sin un caso de uso
  concreto que lo justifique todavía.
- Deja explícitamente fuera de alcance: la implementación de cualquier
  plantilla concreta (tarea siguiente, "Generador Markdown"), resolver la
  limitación de fuente/fecha del dato subyacente, y el agente de reporte
  opcional.

## Decisiones tomadas

- **Reutilizar el orden ya usado por `format_research_result` (Fase 1).**
  En vez de diseñar un orden nuevo para los generadores de reporte, se
  fija el mismo orden que ya demostró ser legible en la salida de
  consola: encabezado → salud financiera → valoración → fallos
  parciales. Esto evita inconsistencias entre la salida de consola (Fase
  1) y los reportes formales (Fase 2).
- **Documentar la ausencia de fuente/fecha del dato normalizado como
  limitación explícita, no como un problema a resolver ahora.** Se
  consideró extender `ResearchResult`/`AnalysisResult` para propagar
  `FinancialStatement`/`MarketData` completos, pero se descartó por ir
  contra el criterio de "no sobre-diseñar antes de tener el caso de uso
  real" ya aplicado en el proyecto: en Fase 1 solo hay un proveedor de
  datos (FMP), por lo que la fuente es uniforme e implícita para todo el
  reporte. Si en el futuro se agregan múltiples proveedores de datos
  fundamentales, esta limitación se resolvería como una tarea explícita
  y separada.

## Archivos creados o modificados

Creados:
- `investmentops/reports/REPORT_SECTIONS.md` (nuevo)

Modificados:
- `TASKS.md` (tarea "Definir qué secciones tendrá el reporte..." marcada
  como completada, Fase 2, "Modelo de reporte")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/REPORT_MODEL.md`, ningún módulo de código Python
existente (esta tarea es puramente de diseño/documentación, sin cambios
de código).

## Problemas encontrados

Ninguno nuevo, más allá de la limitación ya documentada arriba (ausencia
de fuente/fecha del dato normalizado subyacente en `ResearchResult`),
que se deja registrada como decisión consciente, no como un defecto sin
resolver. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`); no aplica a esta tarea, que no agrega pruebas.

## Próxima tarea recomendada

Fase 2 → Generador Markdown → *"Implementar la plantilla base de reporte
en Markdown (encabezados, secciones vacías)."*

Esta es la primera tarea de código de la Fase 2: construir el andamiaje
Markdown (encabezados para las cuatro secciones ya fijadas en
`REPORT_SECTIONS.md`, con las secciones "salud financiera" y "valoración"
inicialmente vacías) antes de volcar el contenido real de cada sección
(tareas siguientes en la misma parte de `TASKS.md`).
