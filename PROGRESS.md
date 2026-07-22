# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Diseñar la sintaxis del nuevo comando
CLI para comparar dos o más empresas directamente." (TASKS.md).

### Qué se implementó

`investmentops/cli/COMPARE_CLI.md` (nuevo): documento de
diseño/documentación (sin código) que fija la sintaxis del nuevo
subcomando `compare`, siguiendo el mismo patrón ya usado en
`investmentops/cli/CLI.md` para `investigate` (Fase 1):

- Sintaxis: `python -m investmentops compare TICKER1 TICKER2 [TICKER3 ...]`.
- Segundo subparser, agregado junto al ya existente `investigate`, sin
  modificar la sintaxis ni el comportamiento de este último.
- Argumento posicional variádico con un **mínimo de dos** tickers (una
  comparación requiere al menos dos empresas; un único ticker ya está
  cubierto por `investigate`).
- Sin límite máximo de tickers, sin normalización ni deduplicación en
  esta capa (mismo criterio ya aplicado a `investigate` en `CLI.md`).
- Sin flags adicionales (`--format` u otros) en esta tarea: se decidirá,
  si aplica, en la sección "Reportes" de esta misma fase.
- Deja explícitamente fuera de alcance: el parseo real con `argparse`
  (tarea siguiente), la función del orquestador que ejecuta la
  investigación comparativa, y la conexión CLI-orquestador (ambas
  tareas separadas y posteriores de esta misma sección).

## Archivos creados o modificados

Creados:
- `investmentops/cli/COMPARE_CLI.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Implementar el parseo de argumentos del comando de comparación
  (lista de tickers)." Sobre la sintaxis ya fijada en
  `investmentops/cli/COMPARE_CLI.md`: agregar el subparser `compare` en
  `build_parser` (`investmentops/cli/__init__.py`), con un argumento
  posicional variádico (`nargs`) validado para exigir un mínimo de dos
  tickers, reutilizando `_validate_ticker` para cada elemento
  individual.