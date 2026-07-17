# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Generador Markdown → *"Implementar la sección de
fuentes/procedencia (qué proveedor, qué fecha) al final del reporte."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: las pruebas ya
existentes (`test_render_does_not_include_financial_health_provenance_yet`,
`test_render_does_not_include_valuation_provenance_yet`) afirmaban
explícitamente que `anthropic`/`claude-sonnet-5` **no** aparecían todavía
en el Markdown generado por `render_markdown`. Por eso sí se requería
código nuevo.

## Qué se implementó

**`investmentops/reports/markdown.py`** (modificado):

- `_render_analysis_body` ahora agrega, como última parte del cuerpo de
  cada análisis (después de limitaciones), una línea con la procedencia
  de la interpretación de IA: `**Generado por:** <ai_provider>
  (<ai_model>) el <generated_at en ISO 8601>`, leída directamente de
  `AnalysisResult.provenance` (`AnalysisProvenance`).
- No se modificó la firma de `_render_analysis_body` ni de
  `_find_analysis`: ambas ya estaban generalizadas (no acopladas a un
  `analysis_id` concreto), por lo que la nueva línea de procedencia
  queda disponible automáticamente tanto para "Salud financiera" como
  para "Valoración" sin duplicar lógica.
- `render_markdown` no cambió su propia lógica (sigue llamando a
  `_find_analysis`/`_render_analysis_body` igual que antes); el cambio
  está contenido enteramente dentro de `_render_analysis_body`.

**Decisión de diseño — dónde vive la procedencia:** `TASKS.md` describe
la tarea como una sección "al final del reporte", pero
`investmentops/reports/REPORT_SECTIONS.md` (ya escrito en una tarea
anterior de esta misma fase) fija de forma más específica que la
procedencia de IA es la **cuarta parte de cada sección de análisis**
(hallazgos → métricas → limitaciones → procedencia), no una sección
nueva y separada al final del documento completo. Se siguió esa decisión
ya documentada, en vez de introducir una sección adicional que la
contradijera. Además del proveedor y el modelo (que sí menciona
`REPORT_SECTIONS.md`), se incluyó también la fecha de generación
(`generated_at`), conforme a lo que pide literalmente el texto de la
tarea en `TASKS.md` ("qué proveedor, qué fecha").

**`investmentops/tests/test_reports_markdown.py`** (modificado):

- Se eliminaron las dos pruebas que afirmaban la ausencia de procedencia
  (`test_render_does_not_include_financial_health_provenance_yet`,
  `test_render_does_not_include_valuation_provenance_yet`), ya que su
  aserción quedó obsoleta por diseño (la tarea que hacían explícitamente
  "todavía no cubierta" es la que se acaba de implementar).
- Se agregó soporte para pasar una `AnalysisProvenance` explícita a los
  helpers `_financial_health_result`/`_valuation_result` (parámetro
  `provenance`, opcional, con el mismo valor por defecto que antes si no
  se indica).
- Pruebas nuevas: procedencia de salud financiera presente
  (`anthropic`, `claude-sonnet-5`, fecha ISO 8601 exacta), procedencia de
  valoración presente, procedencia de cada agente contenida dentro de su
  propia sección (no se mezcla `claude-sonnet-5` de un agente con
  `claude-haiku-4-5` del otro), presencia del rótulo `**Generado por:**`,
  y ausencia total de esa línea cuando el agente correspondiente no
  completó su análisis (sección vacía, igual criterio que hallazgos/
  métricas/limitaciones).

## Archivos creados o modificados

Modificados:
- `investmentops/reports/markdown.py`
- `investmentops/tests/test_reports_markdown.py`
- `TASKS.md` (tarea "Implementar la sección de fuentes/procedencia (qué
  proveedor, qué fecha) al final del reporte" marcada como completada,
  Fase 2, "Generador Markdown")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/REPORT_MODEL.md`,
`investmentops/reports/REPORT_SECTIONS.md`,
`investmentops/reports/__init__.py`, ningún otro módulo de código
Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Generador Markdown → *"Implementar el guardado del archivo
Markdown generado en una ruta local configurable."*

Con las cuatro sub-tareas de contenido de "Generador Markdown" ya
completas (plantilla base, salud financiera, valoración, procedencia),
esta tarea añadiría la escritura del Markdown ya renderizado a disco,
probablemente reutilizando `[output]` de `config.local.toml`
(`output_dir`, ya documentado en `CONFIGURATION.md` y
`config.example.toml` desde la Fase 1, aunque todavía sin consumidor
real) para resolver la ruta de destino, sin introducir una nueva clave
de configuración si `output_dir` ya cubre esa necesidad.
