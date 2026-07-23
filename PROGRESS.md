# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Implementar el parseo de argumentos del
comando de comparación (lista de tickers)." (TASKS.md).

### Qué se implementó

`investmentops/cli/__init__.py` (modificado): sobre la sintaxis ya
fijada en `investmentops/cli/COMPARE_CLI.md`, se agrega un segundo
subparser, `compare`, junto al ya existente `investigate` (sin modificar
la sintaxis ni el comportamiento de este último):

- `compare TICKER1 TICKER2 [TICKER3 ...]`: argumento posicional
  variádico (`nargs="+"`), cada elemento validado individualmente con
  `_validate_ticker` (reutilizada sin cambios de `investigate`).
- Mínimo de dos tickers exigido por una `argparse.Action` propia,
  `_MinimumTwoTickersAction`: como `argparse` no ofrece un mecanismo
  nativo para un mínimo en `nargs="+"`, esta acción llama a
  `parser.error(...)` si `len(values) < 2`, terminando el proceso con el
  mismo mecanismo estándar (mensaje en `stderr` + `SystemExit`) ya usado
  por el resto de errores de parseo de esta CLI.
- Sin normalización ni deduplicación de tickers en esta capa (mismo
  criterio ya aplicado a `investigate`, ver `CLI.md`).
- Sin flags adicionales para `compare` en esta tarea (`--format` u
  otros): fuera de alcance, ver `COMPARE_CLI.md`.
- `dispatch` no se modificó: `args.command == "compare"` sigue
  levantando `ValueError("Comando desconocido: ...")`, ya que conectar
  `compare` con el orquestador es la tarea siguiente y separada de esta
  misma sección de `TASKS.md`.

`investmentops/tests/test_cli_compare.py` (nuevo): cubre el parseo de
`compare` (tickers válidos, mínimo de dos, ticker vacío/solo espacios,
preservación de orden, tickers con puntos, no normalización), confirma
que `investigate` sigue funcionando sin cambios tras agregar el nuevo
subparser, y confirma que `dispatch` todavía no reconoce `compare`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_cli_compare.py`

Modificados:
- `investmentops/cli/__init__.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Implementar en el orquestador la función que ejecuta la investigación
  de cada empresa involucrada en una comparación y ensambla sus
  resultados individuales en un resultado comparativo, reutilizando el
  flujo de investigación ya existente." Reutilizaría `investigate(...)`
  (`investmentops/core/orchestrator.py`) para cada ticker de la lista
  recibida, ensamblando sus `ResearchResult` individuales en una
  estructura comparativa nueva (a definir: lista de `ResearchResult`, o
  un tipo contenedor simple), sin modificar `investigate` ni
  `assemble_research_result`.