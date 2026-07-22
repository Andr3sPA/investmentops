# Sintaxis del comando de comparación (Fase 5)

Cubre la tarea "Diseñar la sintaxis del nuevo comando CLI para comparar
dos o más empresas directamente" (TASKS.md, Fase 5, "Orquestador y
CLI").

Esta tarea es de **diseño/documentación**, no de código: decide la
sintaxis del nuevo subcomando antes de implementar su parseo real
(próxima tarea, "Implementar el parseo de argumentos del comando de
comparación (lista de tickers)"). No se toca `investmentops/cli/__init__.py`
ni `investmentops/__main__.py` en esta tarea.

## Punto de entrada

Mismo punto de entrada ya fijado en `investmentops/cli/CLI.md` para el
subcomando `investigate`:

```bash
python -m investmentops <subcomando> [argumentos]
```

## Decisión: subcomando `compare`, coherente con la estructura de subcomandos ya fijada

`investmentops/cli/CLI.md` (Fase 1) ya decidió una estructura de
**subcomandos** (`argparse` con `add_subparsers`), anticipando
explícitamente este momento:

> "`ROADMAP.md` confirma que se sumarán comandos nuevos y explícitamente
> distintos en fases posteriores: comparar empresas (Fase 5, 'Nuevo
> comando de CLI para comparar dos o más empresas directamente')..."

Esta tarea simplemente cumple esa anticipación: se agrega un **segundo**
subparser, `compare`, junto al ya existente `investigate`, sin modificar
este último ni su sintaxis (`investigate TICKER [--format ...]` sigue
intacta).

- **Nombre del subcomando:** `compare` (en inglés, mismo criterio ya
  aplicado a `investigate`: los identificadores de código están en
  inglés, los mensajes al usuario y los prompts en español).
- Reutiliza el mismo `ArgumentParser` raíz (`build_parser`,
  `investmentops/cli/__init__.py`) y el mismo mecanismo de
  `add_subparsers(dest="command", required=True)` ya usado por
  `investigate`, sin introducir un segundo parser raíz ni un punto de
  entrada distinto.

## Sintaxis del subcomando `compare`

```bash
python -m investmentops compare TICKER1 TICKER2 [TICKER3 ...]
```

- **Argumento posicional variádico y obligatorio:** una lista de
  tickers, **mínimo dos** (`ROADMAP.md`, Fase 5: "comparar dos o más
  empresas"; `GOALS.md`, pregunta 7: "¿Cómo se compara con empresas
  similares?"). Un único ticker no constituye una comparación: para
  investigar una sola empresa ya existe `investigate TICKER` (Fase 1),
  sin que este comando deba duplicar esa capacidad.
- **Sin límite máximo de tickers** fijado en esta tarea: no hay hoy un
  caso de uso concreto que justifique un tope arbitrario (mismo
  criterio de "no inventar un umbral sin caso de uso que lo justifique"
  ya aplicado repetidamente en el proyecto, ver
  `TREND_METRICS.md`/`NEWS_RELEVANCE.md`). Si en el futuro se determina
  que un límite es necesario (ej. por costo de invocaciones a IA o
  tiempo de respuesta), sería una extensión explícita y posterior, no
  algo que deba anticiparse aquí.
- **Sin normalización ni deduplicación de tickers en esta capa:** mismo
  criterio ya fijado en `CLI.md` para `investigate` — la CLI no
  normaliza a mayúsculas ni valida el formato del ticker más allá de "no
  vacío" (esa normalización ya ocurre más abajo en el pipeline, ver
  `FMPFundamentalsProvider.fetch`/`assemble_research_result`). Un mismo
  ticker repetido dos veces en la lista (ej. `compare AAPL AAPL`) no se
  detecta ni se rechaza en esta tarea de diseño: es un caso degenerado
  sin impacto funcional grave (el orquestador simplemente investigaría
  la misma empresa dos veces), y añadir esa validación sin necesidad
  concreta sería sobre-diseñar antes de tener el caso de uso real.

### Ejemplos de invocación

```bash
python -m investmentops compare AAPL MSFT
python -m investmentops compare AAPL MSFT GOOGL
python -m investmentops compare ECOPETROL.CL PFBCOLOM.CL
```

## Validación del mínimo de tickers (alcance de la próxima tarea)

Esta tarea solo fija la sintaxis (`compare TICKER1 TICKER2 [...]`,
mínimo dos); la validación concreta de "al menos dos tickers" —y de que
cada ticker individual no esté vacío o sea solo espacios, reutilizando
el mismo criterio ya usado por `_validate_ticker` en `investigate`— es
la tarea siguiente en `TASKS.md` ("Implementar el parseo de argumentos
del comando de comparación (lista de tickers)"). Queda anotado aquí
únicamente que el argumento es **posicional, variádico (`nargs`) y con
un mínimo de dos elementos**, sin fijar todavía el mecanismo exacto de
`argparse` que impondrá ese mínimo (`nargs="+"` con una validación
posterior, o un tipo de validación combinado): esa decisión de
implementación corresponde a la tarea siguiente, no a esta.

## Sin flags adicionales en esta tarea

Mismo criterio ya aplicado en `CLI.md` para la sintaxis inicial de
`investigate` (Fase 1: "sin flag de formato de salida... capacidad de
la Fase 2"): esta tarea de diseño no introduce ningún flag adicional
para `compare` (ej. `--format`, límites de comparables, orden de
presentación). La presentación del resultado comparativo en reportes
(Markdown/HTML) es alcance de la sección "Reportes" de esta misma fase,
todavía pendiente; si esa sección determina que `compare` necesita su
propio `--format` (reutilizando el ya existente en `investigate`, o uno
propio), esa sería una decisión explícita de una tarea posterior, no
algo que deba anticiparse aquí.

## Fuera de alcance de esta tarea

- Implementar el parseo real de la lista de tickers con `argparse`
  (tarea siguiente, "Implementar el parseo de argumentos del comando de
  comparación (lista de tickers)").
- La validación de cada ticker individual y del mínimo de dos (tarea
  separada, ver arriba).
- La función del orquestador que ejecuta la investigación de cada
  empresa involucrada y ensambla el resultado comparativo (tarea
  separada y posterior de esta misma sección: "Implementar en el
  orquestador la función que ejecuta la investigación de cada empresa
  involucrada en una comparación...").
- Conectar el comando `compare` con esa función del orquestador (tarea
  separada y posterior, "Conectar el comando CLI de comparación con esa
  función del orquestador").
- La impresión en consola del resultado comparativo y el manejo de
  errores específicos de este comando: no desglosadas todavía como
  tareas explícitas en `TASKS.md` para esta sección; se definirán, si
  aplica, siguiendo el mismo patrón ya usado por `format_research_result`
  para `investigate` (Fase 1).
- Cualquier sección de reporte de comparación (Markdown/HTML): tareas
  separadas y posteriores en la sección "Reportes" de esta misma fase.