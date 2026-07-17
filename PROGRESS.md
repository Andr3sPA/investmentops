# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 2 → Generador Markdown → *"Implementar el guardado del archivo
Markdown generado en una ruta local configurable."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: `render_markdown`
solo devolvía un `str`, no existía ninguna función que escribiera ese
texto a disco, y `[output].output_dir` (ya documentado en
`CONFIGURATION.md` y presente en `config.example.toml` desde la Fase 1)
todavía no tenía ningún consumidor real. Por eso sí se requería código
nuevo.

## Qué se implementó

**`investmentops/reports/markdown.py`** (modificado):

- `ReportError` (nueva excepción): cubre ticker vacío y fallos de E/S al
  crear el directorio de salida o escribir el archivo del reporte, mismo
  criterio ya aplicado por `investmentops.data_layer.cache.CacheError`.
- `DEFAULT_OUTPUT_DIR = "reports/"` (nueva constante): mismo valor de
  ejemplo ya presente en `config.example.toml`, sección `[output]`.
- `_resolve_output_dir(output_dir, config)` (nueva función privada):
  resuelve la ruta de salida en este orden de prioridad: parámetro
  explícito → `[output].output_dir` en la configuración ya cargada (o en
  `load_config()` si no se indica) → `DEFAULT_OUTPUT_DIR`. Mismo patrón
  ya usado por `investmentops.data_layer.cache._resolve_cache_dir`.
- `save_markdown_report(ticker, content, *, output_dir=None, config=None) -> Path`
  (nueva función pública): valida que el ticker no esté vacío, resuelve
  el directorio de salida, lo crea si no existe (`mkdir(parents=True,
  exist_ok=True)`), y escribe `content` tal cual en
  `<output_dir>/<TICKER>.md` (ticker normalizado a mayúsculas, misma
  convención que la caché de datos normalizados,
  `investmentops/data_layer/CACHE.md`). Sobrescribe por completo
  cualquier reporte previo del mismo ticker. No modifica `render_markdown`
  ni ninguna otra función ya existente del módulo.

**`investmentops/reports/__init__.py`** (modificado):

- Re-exporta `save_markdown_report` y `ReportError`, junto con
  `render_markdown` ya existente.

**`investmentops/tests/test_reports_markdown_save.py`** (nuevo):

- Pruebas para `save_markdown_report`: escritura del contenido exacto,
  normalización del ticker a mayúsculas en el nombre del archivo,
  creación del directorio de salida si falta (incluyendo rutas anidadas),
  sobrescritura de un reporte previo del mismo ticker, rechazo de ticker
  vacío/solo espacios (`ReportError`), lectura de `output_dir` desde
  `config` cuando no se indica explícitamente, uso de `DEFAULT_OUTPUT_DIR`
  cuando la configuración no define `[output].output_dir`, y que
  `ReportError` es una `RuntimeError`.

**Decisión de diseño — nombre de archivo:** se usa `<TICKER>.md` (ticker
normalizado a mayúsculas), no un nombre con marca de tiempo. Es la misma
convención "un archivo por ticker" ya usada por la caché de datos
normalizados (`investmentops/data_layer/CACHE.md`), y significa que una
investigación nueva del mismo ticker sobrescribe el reporte anterior en
vez de acumular versiones. No hay hoy un caso de uso que exija conservar
un historial de reportes por fecha (eso es, en todo caso, competencia de
la Fase 7, "Registro personal de investigaciones", no de esta tarea); de
necesitarse en el futuro, sería una extensión explícita y separada,
mismo criterio de "no sobre-diseñar antes de tener el caso de uso real"
ya aplicado en otros módulos del proyecto.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_reports_markdown_save.py`

Modificados:
- `investmentops/reports/markdown.py`
- `investmentops/reports/__init__.py`
- `TASKS.md` (tarea "Implementar el guardado del archivo Markdown
  generado en una ruta local configurable" marcada como completada,
  Fase 2, "Generador Markdown")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/REPORT_MODEL.md`,
`investmentops/reports/REPORT_SECTIONS.md`,
`investmentops/tests/test_reports_markdown.py`, ningún otro módulo de
código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Generador HTML → *"Definir la plantilla base HTML (estructura
mínima, sin diseño elaborado)."*

Con "Generador Markdown" completo (plantilla base, salud financiera,
valoración, procedencia y guardado en disco), la siguiente sección
natural de `TASKS.md` es el generador HTML, empezando por su tarea de
diseño (estructura mínima), antes de implementar el volcado de contenido
y el guardado, siguiendo el mismo patrón ya usado para Markdown.
