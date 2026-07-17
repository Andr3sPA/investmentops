# InvestmentOps — Progreso

**Última actualización:** 2026-07-17

## Última tarea completada

Fase 2 → Orquestador y CLI → *"Añadir al comando CLI la opción de
formato de salida (markdown, html, o ambos)."*

## Verificación previa (sin duplicar trabajo)

Se confirmó que esta tarea **no** estaba satisfecha: `build_parser`
(`investmentops/cli/__init__.py`) solo declaraba el argumento posicional
`ticker` en el subcomando `investigate`, sin ningún flag de formato de
salida; `dispatch` invocaba siempre `investigate(...)` sin conexión
alguna a `generate_reports`/`investigate_and_generate_reports` (ya
implementadas en la tarea anterior).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (modificado): `generate_reports`
e `investigate_and_generate_reports` ganan un parámetro opcional nuevo,
`formats: Sequence[str] | None = None`:

- `formats=None` (por defecto): comportamiento histórico exacto — genera
  **ambos** formatos, en el orden `[markdown_path, html_path]`. Ningún
  llamador existente (incluyendo todas las pruebas de
  `test_core_orchestrator_reports.py`) cambia de comportamiento.
- `formats=("markdown",)` / `("html",)`: genera únicamente ese formato.
- El orden de la lista devuelta es siempre `[markdown_path, html_path]`
  cuando ambos formatos están presentes en `formats`, sin importar el
  orden en que se hayan pedido.
- `formats` vacío o con un valor desconocido (distinto de `"markdown"`/
  `"html"`) levanta `ValueError`.
- Se agregó la constante `ALL_REPORT_FORMATS = ("markdown", "html")`
  como fuente única de verdad de los formatos soportados y su orden.

**`investmentops/cli/__init__.py`** (modificado):

- `build_parser`: se agrega el flag opcional `--format` al subcomando
  `investigate`, con `choices=["both", "html", "markdown"]` (orden
  alfabético de `argparse`, sin relevancia funcional) y `default=None`.
- `dispatch`: su tipo de retorno se amplía a
  `ResearchResult | tuple[ResearchResult, list[Path]]`, condicionado
  estrictamente a `args.format`:
  - `args.format is None` → comportamiento idéntico a antes de esta
    tarea: llama a `investigate(...)` y devuelve el `ResearchResult` sin
    transformar. **Todas** las pruebas ya existentes de
    `test_cli_dispatch.py` y `test_main.py` siguen pasando sin
    modificación, ya que ninguna pasa `--format`.
  - `args.format` es `"markdown"`/`"html"`/`"both"` → llama a
    `investigate_and_generate_reports(...)` (mapeando el valor de
    `--format` a la tupla de formatos concreta vía el diccionario
    `_FORMAT_TO_REPORT_FORMATS`) y devuelve la tupla
    `(ResearchResult, list[Path])` que esa función produce.
  - Se agregó un nuevo parámetro `output_dir` a `dispatch`, propagado
    solo cuando se genera un reporte (se ignora si `args.format is
    None`).

**Decisión de diseño clave (documentada en los docstrings de ambos
módulos):** `investmentops/__main__.py` **no se modificó** en esta
tarea. La presentación en consola de las rutas de los reportes generados
(cuando `dispatch` devuelve la tupla) es, explícitamente, la tarea
siguiente ("Implementar el mensaje final en consola indicando dónde
quedaron guardados los reportes generados"). Invocar hoy la CLI real con
`--format` genera los archivos correctamente en disco, pero `main()`
todavía no sabe manejar el valor tupla que `dispatch` devolvería en ese
caso (se resolverá en la tarea siguiente).

**Archivos de prueba nuevos:**
- `investmentops/tests/test_cli_format.py`: parseo de `--format`
  (valores válidos, valor inválido → `SystemExit`, valor por defecto
  `None`), y `dispatch` con cada valor de `--format` (verifica archivos
  generados en disco, orden de rutas, y que un fallo de la fuente de
  datos igual permite generar los reportes).
- `investmentops/tests/test_core_orchestrator_report_formats.py`:
  parámetro `formats` de `generate_reports` (formato único, orden
  independiente del orden de entrada, errores por `formats` vacío/
  desconocido, y regresión explícita del comportamiento por defecto).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_cli_format.py`
- `investmentops/tests/test_core_orchestrator_report_formats.py`

Modificados:
- `investmentops/core/orchestrator.py` (parámetro `formats` nuevo en
  `generate_reports`/`investigate_and_generate_reports`; constante
  `ALL_REPORT_FORMATS`; docstring del módulo actualizado)
- `investmentops/cli/__init__.py` (flag `--format` en `build_parser`;
  `dispatch` amplía su tipo de retorno condicionado a `args.format`;
  nuevo parámetro `output_dir`; docstring del módulo actualizado)
- `TASKS.md` (tarea marcada como completada, Fase 2, "Orquestador y
  CLI")
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/reports/markdown.py`, `investmentops/reports/html.py`,
`investmentops/reports/__init__.py`, `investmentops/__main__.py`,
ningún otro módulo de código Python existente, ningún otro archivo de
pruebas existente (en particular, `test_cli_dispatch.py` y
`test_main.py` no requirieron ningún cambio).

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`).

## Próxima tarea recomendada

Fase 2 → Orquestador y CLI → *"Implementar el mensaje final en consola
indicando dónde quedaron guardados los reportes generados."*

Esa tarea deberá actualizar `investmentops/__main__.py::main` para
detectar cuándo `dispatch(args, ...)` devuelve la tupla
`(ResearchResult, list[Path])` (es decir, cuando `args.format is not
None`) en vez de un `ResearchResult` a secas, imprimir
`format_research_result(result)` igual que hoy, y agregar a continuación
una línea (o sección) indicando las rutas de los archivos ya escritos
(`paths`, ya devueltas por `dispatch`/`investigate_and_generate_reports`
en esta tarea).
