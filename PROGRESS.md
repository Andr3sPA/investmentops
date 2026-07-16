# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Generador Markdown → *"Implementar la plantilla base de reporte
en Markdown (encabezados, secciones vacías)."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: `investmentops/reports/__init__.py`
solo tenía el docstring de la capa (sin implementación, tal como lo dejó
la Fase 1), y no existía ningún módulo de generación de reportes
concreto. Las dos tareas anteriores de esta misma sección
("Definir la estructura común...", "Definir qué secciones tendrá el
reporte...") ya estaban marcadas como completadas y correspondían a
documentos de diseño (`REPORT_MODEL.md`, `REPORT_SECTIONS.md`), no a
código; la tercera tarea de esa lista está marcada explícitamente como
opcional en `TASKS.md` y no bloquea el avance a "Generador Markdown".
Por eso sí se requería un artefacto de código nuevo para esta tarea.

## Qué se implementó

**`investmentops/reports/markdown.py`** (nuevo) — `render_markdown(result:
ResearchResult) -> str`, la plantilla base del reporte Markdown:

- Encabezado `# Investigación: <ticker>`.
- Línea de identidad de la empresa (`name · sector · market`), solo si
  alguno de esos campos no está vacío — en la Fase 1,
  `assemble_research_result` siempre construye una `Company` mínima con
  esos tres campos vacíos, por lo que en la práctica esta línea no
  aparece todavía; queda lista para cuando una fuente de datos futura
  los complete.
- Línea `Generado: <fecha ISO 8601>` (`ResearchResult.generated_at`).
- Encabezados vacíos `## Salud financiera` y `## Valoración`, en el
  orden ya fijado en `REPORT_SECTIONS.md`.

Deliberadamente **no** incluye todavía: los hallazgos/métricas/limitaciones
de cada análisis, la procedencia de IA, ni la sección condicional de
"Fallos parciales" — esas son las cuatro tareas siguientes, ya
desglosadas por separado en `TASKS.md` bajo la misma sección
("Generador Markdown").

**`investmentops/reports/__init__.py`** (modificado) — re-exporta
`render_markdown`, siguiendo el mismo patrón de re-exportación ya usado
por el resto de los `__init__.py` del proyecto (`investmentops.core`,
`investmentops.data_layer`, `investmentops.ai_providers`, etc.).

**`investmentops/tests/test_reports_markdown.py`** (nuevo) — cubre: el
título con el ticker, la fecha de ensamblado, la presencia y el orden de
los encabezados de "Salud financiera"/"Valoración", la omisión de la
línea de identidad cuando `name`/`sector`/`market` están vacíos (caso
actual de Fase 1) y su inclusión cuando sí hay datos, la ausencia
todavía de la sección de fallos parciales, y que el texto termina en un
único salto de línea final (sin líneas en blanco sobrantes al final).

## Decisiones tomadas

- **Andamiaje completo desde ya, contenido vacío.** En vez de esperar a
  la primera tarea de volcado de contenido para introducir los
  encabezados de "Salud financiera"/"Valoración", esta plantilla base ya
  los construye ambos (vacíos). Esto sigue literalmente el enunciado de
  la tarea ("encabezados, secciones vacías") y deja que las tareas
  siguientes solo tengan que *rellenar*, sin rediseñar la estructura del
  documento.
- **La sección "Fallos parciales" queda fuera de la plantilla base.** A
  diferencia de "Salud financiera"/"Valoración" (secciones fijas que
  siempre aparecen, aunque vacías por ahora), "Fallos parciales" es
  condicional (solo se muestra si `ResearchResult.failures` no está
  vacío, ver `REPORT_SECTIONS.md`). Incluir ya su encabezado sin lógica
  condicional sería inconsistente con esa regla; se deja para cuando se
  implemente el volcado de contenido real, mismo criterio que ya aplica
  `investmentops.cli.format_research_result` en la Fase 1.
- **Reutilizar `ResearchResult` directamente, sin nueva estructura
  intermedia.** Consistente con la decisión ya tomada en
  `REPORT_MODEL.md`: `render_markdown` recibe un `ResearchResult` tal
  cual, sin ningún tipo de entrada nuevo.

## Archivos creados o modificados

Creados:
- `investmentops/reports/markdown.py` (nuevo)
- `investmentops/tests/test_reports_markdown.py` (nuevo)

Modificados:
- `investmentops/reports/__init__.py` (re-exporta `render_markdown`)
- `TASKS.md` (tarea "Implementar la plantilla base de reporte en
  Markdown (encabezados, secciones vacías)" marcada como completada,
  Fase 2, "Generador Markdown")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/REPORT_MODEL.md`,
`investmentops/reports/REPORT_SECTIONS.md`, ningún otro módulo de código
Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`); esta tarea agregó su prueba nueva bajo
`investmentops/tests/`, siguiendo la ubicación ya usada por el resto de
pruebas de módulos de `investmentops/` (`data_layer`, `analysis_engines`,
`ai_providers`, `cli`, `core`), a diferencia de las pruebas de
`core.orchestrator` que están duplicadas en ambas carpetas.

## Próxima tarea recomendada

Fase 2 → Generador Markdown → *"Implementar el volcado de los hallazgos
de salud financiera en la sección correspondiente."*

Esta tarea rellenará la sección `## Salud financiera` ya creada por
`render_markdown` con el contenido del `AnalysisResult` correspondiente
(`analysis_id == "financial_health"`): hallazgos, métricas de soporte y
limitaciones, siguiendo el orden ya fijado en `REPORT_SECTIONS.md` (la
procedencia de IA se deja para la tarea de "fuentes/procedencia" que le
sigue en la misma sección de `TASKS.md`, salvo que se decida incluirla
ya en esta misma tarea por cohesión — a evaluar al implementarla).
