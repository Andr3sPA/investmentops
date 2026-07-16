"""Punto de entrada de la CLI: `python -m investmentops`.

Conecta las tres piezas ya implementadas en `investmentops.cli`:
`parse_args` (parseo y validación del ticker), `dispatch` (invocación al
orquestador, `investmentops.core.orchestrator.investigate`) y
`format_research_result` (traducción del `ResearchResult` obtenido a
texto simple para consola, ver TASKS.md, Fase 1, "CLI" > "Implementar la
impresión en consola del resultado").

El único manejo de error implementado aquí es `ConfigError` (si falta
`config.local.toml`), heredado sin cambios de la versión anterior de
este módulo: `dispatch`/`investigate` ya traducen internamente
`DataProviderError`, `NormalizationError`, `PromptError`,
`AgentProviderSelectionError` y `AIProviderError` a `ResearchFailure`
dentro del propio `ResearchResult` (ver
`investmentops/core/orchestrator.py`), por lo que esos fallos ya
aparecen reflejados en la salida de `format_research_result`, no como
una excepción. Mensajes de error más elaborados (ej. para `ConfigError`)
son la tarea siguiente en TASKS.md ("Implementar mensajes de error
legibles en consola ante fallos del flujo"), intencionalmente separada.
"""

from investmentops.cli import dispatch, format_research_result, parse_args
from investmentops.config import ConfigError

if __name__ == "__main__":
    args = parse_args()

    try:
        result = dispatch(args)
    except ConfigError as exc:
        print(f"[config] {exc}")
    else:
        print(format_research_result(result))
