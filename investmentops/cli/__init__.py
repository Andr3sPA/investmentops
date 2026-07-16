"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Cubre la tarea "Implementar el parseo del argumento ticker" (TASKS.md,
Fase 1, "CLI"), siguiendo la sintaxis ya decidida y documentada en
`investmentops/cli/CLI.md`: un único subcomando, `investigate`, con un
argumento posicional obligatorio `TICKER`.

```
python -m investmentops investigate TICKER
```

Esta tarea es puramente de **parseo de argumentos**: construir el
`ArgumentParser` (con `add_subparsers`, tal como fija `CLI.md`) y exponer
una función que, dada una lista de argumentos, devuelve el resultado ya
parseado. No hace nada más:

- **No valida** el contenido de `ticker` (no vacío, formato esperado):
  eso es la tarea siguiente en `TASKS.md` ("Implementar la validación
  básica del ticker"). El parser de `argparse` sí exige que el argumento
  posicional esté presente (comportamiento estándar de `argparse`, no una
  validación de contenido añadida aquí).
- **No normaliza** el ticker (ej. a mayúsculas): esa normalización ya
  ocurre más abajo en el pipeline (ver
  `investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch`
  y `investmentops.core.orchestrator.assemble_research_result`), conforme
  a `CLI.md`: "no es responsabilidad de la capa CLI".
- **No invoca** al orquestador (`investmentops.core.orchestrator.investigate`):
  esa conexión es una tarea separada y posterior ("Conectar el comando
  con el orquestador").
- **No imprime** nada en consola: la impresión del resultado y el manejo
  de mensajes de error también son tareas separadas y posteriores.

Fuera de alcance de este módulo (aún, ver TASKS.md, sección "CLI"):
- La validación básica del ticker.
- La conexión del comando con el orquestador.
- La impresión en consola del resultado.
- Los mensajes de error legibles ante fallos del flujo.
- Los subcomandos de fases posteriores (comparar, listar investigaciones,
  watchlist, ver `ROADMAP.md`, Fases 5, 7 y 8): no se anticipan aquí,
  siguiendo el mismo criterio de no sobre-diseñar ya aplicado en el resto
  del proyecto.
"""

from __future__ import annotations

import argparse
from typing import Sequence

#: Nombre del programa mostrado en la ayuda de la CLI (`--help`), consistente
#: con la forma de invocación ya fijada en `investmentops/cli/CLI.md`:
#: `python -m investmentops <subcomando> [argumentos]`.
PROG_NAME = "investmentops"


def build_parser() -> argparse.ArgumentParser:
    """Construye el `ArgumentParser` de la CLI, con sus subcomandos.

    Implementa la estructura de subcomandos (`argparse` con
    `add_subparsers`) ya decidida en `investmentops/cli/CLI.md`. En esta
    fase existe un único subcomando, `investigate`, con un argumento
    posicional obligatorio `ticker`. Subcomandos futuros (comparar,
    listar investigaciones, watchlist) se añadirán aquí como subparsers
    adicionales, sin modificar este, cuando les corresponda su propia
    tarea (ver `CLI.md`, "Decisión: subcomandos").

    Returns
    -------
    argparse.ArgumentParser
        El parser completo, listo para invocar `.parse_args(...)`.
    """
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description=(
            "InvestmentOps - herramienta CLI local de apoyo a la "
            "investigación previa a una decisión de inversión."
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    investigate_parser = subparsers.add_parser(
        "investigate",
        help="Investiga una empresa a partir de su ticker.",
    )
    investigate_parser.add_argument(
        "ticker",
        help="Ticker de la empresa a investigar (ej. AAPL, ECOPETROL.CL).",
    )

    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parsea los argumentos de la CLI y devuelve el resultado.

    Parameters
    ----------
    argv:
        Lista de argumentos a parsear (sin el nombre del programa), tal
        como los recibiría `sys.argv[1:]`. Si no se indica, `argparse`
        toma `sys.argv[1:]` por defecto (comportamiento estándar).

    Returns
    -------
    argparse.Namespace
        El resultado del parseo. Para el subcomando `investigate`, expone
        `command == "investigate"` y `ticker` (el valor tal cual se
        recibió, sin validar ni normalizar, ver docstring del módulo).

    Raises
    ------
    SystemExit
        Comportamiento estándar de `argparse` si falta el subcomando, si
        falta el argumento posicional `ticker`, o si se pasa `--help`/
        `-h` (imprime ayuda/error y termina el proceso). Este módulo no
        atrapa ni traduce esa excepción: es el mecanismo de error nativo
        de `argparse`, consistente con una CLI estándar.
    """
    parser = build_parser()
    return parser.parse_args(argv)
