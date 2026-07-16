"""Punto de entrada de la CLI: `python -m investmentops`.

Conecta las tres piezas ya implementadas en `investmentops.cli`:
`parse_args` (parseo y validación del ticker), `dispatch` (invocación al
orquestador, `investmentops.core.orchestrator.investigate`) y
`format_research_result` (traducción del `ResearchResult` obtenido a
texto simple para consola, ver TASKS.md, Fase 1, "CLI").

Cubre la tarea "Implementar mensajes de error legibles en consola ante
fallos del flujo" (TASKS.md, Fase 1, "CLI"), la última de esa sección.

## Qué fallos puede dejar escapar `dispatch`

`dispatch` (`investmentops.cli.dispatch`) delega en
`investmentops.core.orchestrator.investigate`, que ya captura
internamente `DataProviderError`, `NormalizationError`, `PromptError`,
`AgentProviderSelectionError` y `AIProviderError`, traduciéndolos a
`ResearchFailure` dentro del propio `ResearchResult` (ver
`investmentops/core/orchestrator.py`). Esos fallos ya se ven reflejados
en la salida de `format_research_result`, no como una excepción: no
requieren manejo adicional aquí.

El único fallo de flujo que sí puede escapar hasta este punto es
`ConfigError` (`investmentops.config.ConfigError`): ocurre si
`config.local.toml` no existe o no es TOML válido, y `dispatch` no lo
recibe pre-cargado (uso normal de `python -m investmentops`, donde
`config=None` y cada pieza del pipeline resuelve la configuración real
por sí misma). `ConfigError` ya trae, en su propio mensaje, la
instrucción concreta para resolverlo (ver
`investmentops/config/__init__.py`: sugiere
`cp config.example.toml config.local.toml`), por lo que este módulo no
necesita reconstruir esa guía: solo debe presentarla de forma clara.

## Argumentos inválidos (`argparse`)

Un ticker vacío, un subcomando ausente o desconocido, o `--help`, ya
terminan el proceso mediante el mecanismo estándar de `argparse`
(mensaje en `stderr` + `SystemExit`, ver `investmentops/cli/__init__.py`
y `investmentops/cli/CLI.md`). Ese mecanismo ya es legible por sí mismo
y es el comportamiento esperado de cualquier CLI basada en `argparse`;
este módulo no lo intercepta ni lo envuelve.

## `main(argv=None) -> int`

Se extrae el flujo completo a una función `main()` (en vez de dejarlo
solo en el bloque `if __name__ == "__main__":`) para que sea invocable
y probable directamente desde pruebas, sin depender de `sys.argv` real
ni de capturar un proceso completo:

1. `parse_args(argv)`: si los argumentos son inválidos, `argparse`
   termina el proceso por su cuenta (`SystemExit`), sin pasar por el
   `try/except` de esta función.
2. `dispatch(args)`: si tiene éxito, se imprime
   `format_research_result(result)` en `stdout` y se devuelve `0`.
3. Si `dispatch` levanta `ConfigError`, se imprime un mensaje legible
   con el prefijo `"Error de configuración: "` en `stderr` (no en
   `stdout`, para no mezclarlo con la salida normal del programa ni con
   scripts que redirijan `stdout`), y se devuelve `1`.

El bloque `if __name__ == "__main__":` solo llama a `main()` y propaga
su código de salida a través de `sys.exit(...)`, el mecanismo estándar
para que el proceso termine con el código correcto (`0` en éxito, `1`
ante un fallo de configuración).
"""

from __future__ import annotations

import sys
from typing import Sequence

from investmentops.cli import dispatch, format_research_result, parse_args
from investmentops.config import ConfigError


def main(argv: Sequence[str] | None = None) -> int:
    """Ejecuta el flujo completo de la CLI y devuelve el código de salida.

    Parameters
    ----------
    argv:
        Lista de argumentos de la CLI (sin el nombre del programa), tal
        como los recibiría `sys.argv[1:]`. Se propaga directamente a
        `parse_args`. Si no se indica, `argparse` toma `sys.argv[1:]`
        por defecto (comportamiento estándar); pensado sobre todo para
        pruebas, que pueden invocar `main(["investigate", "AAPL"])` sin
        depender del proceso real.

    Returns
    -------
    int
        `0` si el flujo se completó (con o sin `failures` parciales
        dentro del `ResearchResult`, ver
        `investmentops.core.orchestrator.investigate`), `1` si
        `config.local.toml` no se pudo cargar (`ConfigError`).

    Raises
    ------
    SystemExit
        Si `argv` contiene argumentos inválidos (ticker vacío,
        subcomando ausente/desconocido, `--help`): comportamiento
        estándar de `argparse` (ver `investmentops.cli.parse_args`), no
        capturado por esta función.
    """
    args = parse_args(argv)

    try:
        result = dispatch(args)
    except ConfigError as exc:
        print(f"Error de configuración: {exc}", file=sys.stderr)
        return 1

    print(format_research_result(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
