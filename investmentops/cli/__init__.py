"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Cubre dos tareas de TASKS.md, Fase 1, "CLI":

- "Implementar el parseo del argumento ticker." (`build_parser`,
  `parse_args`), siguiendo la sintaxis ya decidida y documentada en
  `investmentops/cli/CLI.md`: un único subcomando, `investigate`, con un
  argumento posicional obligatorio `TICKER`.
- "Implementar la validación básica del ticker (no vacío, formato
  esperado)." (`_validate_ticker`).

```
python -m investmentops investigate TICKER
```

## Parseo (`build_parser`/`parse_args`)

Construye el `ArgumentParser` (con `add_subparsers`, tal como fija
`CLI.md`) y expone una función que, dada una lista de argumentos,
devuelve el resultado ya parseado.

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

## Validación básica (`_validate_ticker`)

Se implementa como una función `type=` de `argparse`, el mismo mecanismo
nativo que ya usa `argparse` para exigir que el argumento posicional
`ticker` esté *presente*: si `_validate_ticker` levanta
`argparse.ArgumentTypeError`, `argparse` lo traduce automáticamente a un
mensaje de error en `stderr` y un `SystemExit`, igual comportamiento que
ya tienen los demás errores de parseo de esta CLI (ticker ausente,
subcomando ausente/desconocido, ver `investmentops/tests/test_cli.py`).
Esto evita introducir un mecanismo de validación distinto al ya usado
por el resto del parser.

"Formato esperado", en el alcance de esta tarea, es deliberadamente
mínimo: no vacío y no compuesto solo de espacios en blanco. No se aplica
ninguna expresión regular ni se restringe la forma del ticker (longitud,
mayúsculas, símbolos permitidos): el modelo de dominio `Company` (ver
`investmentops/data_layer/domain.py`) ya documenta que no impone un
formato fijo de ticker (soporta, por ejemplo, tickers con puntos del
mercado colombiano como `"ECOPETROL.CL"`), y agregar una restricción de
formato más estricta aquí iría contra ese mismo criterio sin que exista
hoy un caso de uso real que lo justifique.

Esta validación es independiente de la normalización a mayúsculas (que
sigue sin ocurrir en esta capa, ver más arriba): no se duplica aquí.

Fuera de alcance de este módulo (aún, ver TASKS.md, sección "CLI"):
- La conexión del comando con el orquestador.
- La impresión en consola del resultado.
- Los mensajes de error legibles ante fallos del flujo (más allá del
  mensaje estándar que ya produce `argparse` ante un ticker inválido).
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


def _validate_ticker(value: str) -> str:
    """Valida que el ticker recibido no esté vacío ni sea solo espacios.

    Usada como `type=` del argumento posicional `ticker` en
    `build_parser`. `argparse` invoca esta función con el valor crudo
    recibido en la línea de comandos; si levanta
    `argparse.ArgumentTypeError`, `argparse` lo traduce automáticamente a
    un mensaje de error en `stderr` y termina el proceso con
    `SystemExit`, el mismo mecanismo ya usado para el resto de errores de
    parseo de esta CLI (ver docstring del módulo).

    Parameters
    ----------
    value:
        El valor crudo del argumento `ticker` tal como lo recibió
        `argparse`, sin procesar.

    Returns
    -------
    str
        El mismo `value` recibido, sin modificar (ni recortar espacios
        externos ni normalizar a mayúsculas: ver "Validación básica" en
        el docstring del módulo).

    Raises
    ------
    argparse.ArgumentTypeError
        Si `value` está vacío o contiene solo espacios en blanco.
    """
    if not value or not value.strip():
        raise argparse.ArgumentTypeError(
            "el ticker no puede estar vacío ni contener solo espacios."
        )
    return value


def build_parser() -> argparse.ArgumentParser:
    """Construye el `ArgumentParser` de la CLI, con sus subcomandos.

    Implementa la estructura de subcomandos (`argparse` con
    `add_subparsers`) ya decidida en `investmentops/cli/CLI.md`. En esta
    fase existe un único subcomando, `investigate`, con un argumento
    posicional obligatorio `ticker`, validado mediante `_validate_ticker`
    (no vacío, no solo espacios). Subcomandos futuros (comparar, listar
    investigaciones, watchlist) se añadirán aquí como subparsers
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
        type=_validate_ticker,
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
        recibió, ya validado como no vacío/no solo espacios por
        `_validate_ticker`, pero sin normalizar, ver docstring del
        módulo).

    Raises
    ------
    SystemExit
        Comportamiento estándar de `argparse` si falta el subcomando, si
        falta el argumento posicional `ticker`, si el ticker está vacío o
        es solo espacios (ver `_validate_ticker`), o si se pasa
        `--help`/`-h` (imprime ayuda/error y termina el proceso). Este
        módulo no atrapa ni traduce esa excepción: es el mecanismo de
        error nativo de `argparse`, consistente con una CLI estándar.
    """
    parser = build_parser()
    return parser.parse_args(argv)
