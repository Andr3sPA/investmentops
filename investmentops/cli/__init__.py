"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Cubre tres tareas de TASKS.md, Fase 1, "CLI":

- "Implementar el parseo del argumento ticker." (`build_parser`,
  `parse_args`), siguiendo la sintaxis ya decidida y documentada en
  `investmentops/cli/CLI.md`: un único subcomando, `investigate`, con un
  argumento posicional obligatorio `TICKER`.
- "Implementar la validación básica del ticker (no vacío, formato
  esperado)." (`_validate_ticker`).
- "Conectar el comando con el orquestador." (`dispatch`).

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

## Validación básica (`_validate_ticker`)

Se implementa como una función `type=` de `argparse`, el mismo mecanismo
nativo que ya usa `argparse` para exigir que el argumento posicional
`ticker` esté *presente*: si `_validate_ticker` levanta
`argparse.ArgumentTypeError`, `argparse` lo traduce automáticamente a un
mensaje de error en `stderr` y un `SystemExit`, igual comportamiento que
ya tienen los demás errores de parseo de esta CLI (ticker ausente,
subcomando ausente/desconocido, ver `investmentops/tests/test_cli.py`).

"Formato esperado", en el alcance de esta tarea, es deliberadamente
mínimo: no vacío y no compuesto solo de espacios en blanco. No se aplica
ninguna expresión regular ni se restringe la forma del ticker (longitud,
mayúsculas, símbolos permitidos): el modelo de dominio `Company` (ver
`investmentops/data_layer/domain.py`) ya documenta que no impone un
formato fijo de ticker (soporta, por ejemplo, tickers con puntos del
mercado colombiano como `"ECOPETROL.CL"`).

## Conexión con el orquestador (`dispatch`)

`dispatch(args, ...)` recibe el `argparse.Namespace` ya producido por
`parse_args` y lo traduce a una llamada real al orquestador
(`investmentops.core.orchestrator.investigate`). Es, deliberadamente,
**solo la conexión**:

- Para el subcomando `investigate`, invoca
  `investigate(args.ticker, config=config, provider=provider)` y
  devuelve el `ResearchResult` obtenido tal cual, sin transformarlo.
- **No imprime nada en consola.** Cómo y qué se imprime del
  `ResearchResult` devuelto es la tarea siguiente en `TASKS.md`
  ("Implementar la impresión en consola del resultado").
- **No traduce ni maneja ningún error.** `investigate(...)` ya no deja
  escapar `DataProviderError`, `NormalizationError`, `PromptError`,
  `AgentProviderSelectionError` ni `AIProviderError` (los captura
  internamente como `ResearchFailure` dentro del propio
  `ResearchResult`, ver `investmentops/core/orchestrator.py`); lo que
  puede seguir escapando (ej. `ConfigError` si falta
  `config.local.toml`) se propaga tal cual desde `dispatch`. Decidir
  qué mensaje legible mostrar ante ese tipo de fallo es la tarea
  siguiente ("Implementar mensajes de error legibles en consola ante
  fallos del flujo").
- `config` y `provider` son parámetros opcionales que se propagan
  directamente a `investigate(...)`, pensados sobre todo para pruebas
  (para no depender de un `config.local.toml` real en disco ni de un
  proveedor de datos real). En uso normal (`python -m investmentops
  investigate TICKER`), ambos se dejan en `None` y `investigate` resuelve
  la configuración real y el proveedor por defecto (FMP) por sí mismo.
- Si `args.command` no es un comando reconocido, levanta `ValueError`:
  esto no debería ocurrir en la práctica, ya que `parse_args` ya exige
  (vía `argparse`, `required=True` en los subparsers) que `command` sea
  uno de los subcomandos definidos; es una salvaguarda defensiva, no un
  camino esperado del flujo normal.

Fuera de alcance de este módulo (aún, ver TASKS.md, sección "CLI"):
- La impresión en consola del resultado.
- Los mensajes de error legibles ante fallos del flujo (más allá del
  mensaje estándar que ya produce `argparse` ante un ticker inválido, o
  de que una excepción como `ConfigError` se propague sin traducir).
- Los subcomandos de fases posteriores (comparar, listar investigaciones,
  watchlist, ver `ROADMAP.md`, Fases 5, 7 y 8): no se anticipan aquí,
  siguiendo el mismo criterio de no sobre-diseñar ya aplicado en el resto
  del proyecto.
"""

from __future__ import annotations

import argparse
from typing import Any, Sequence

from investmentops.core.orchestrator import investigate
from investmentops.core.research_result import ResearchResult
from investmentops.data_providers.contracts import DataProvider

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


def dispatch(
    args: argparse.Namespace,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> ResearchResult:
    """Conecta el comando ya parseado con el orquestador (`investigate`).

    Traduce el `argparse.Namespace` producido por `parse_args` en una
    llamada real a `investmentops.core.orchestrator.investigate`. Ver
    "Conexión con el orquestador (`dispatch`)" en el docstring del
    módulo para el alcance exacto de esta tarea (solo la conexión: sin
    impresión en consola ni manejo/traducción de errores adicional).

    Parameters
    ----------
    args:
        El `argparse.Namespace` ya parseado y validado (ver
        `parse_args`). Para el único subcomando existente
        (`"investigate"`), se espera que exponga `args.ticker`.
    config:
        Configuración ya cargada, propagada tal cual a `investigate(...)`.
        Pensado sobre todo para pruebas, para no depender de un
        `config.local.toml` real en disco. Si no se indica,
        `investigate` resuelve la configuración real por sí mismo.
    provider:
        Proveedor de datos ya construido, propagado tal cual a
        `investigate(...)`. Pensado sobre todo para pruebas. Si no se
        indica, `investigate` usa el proveedor por defecto (FMP).

    Returns
    -------
    ResearchResult
        El resultado de investigación devuelto por `investigate(...)`,
        sin transformar (puede incluir `failures` si algo falló
        parcialmente; ver `investmentops.core.research_result`).

    Raises
    ------
    ValueError
        Si `args.command` no es un comando reconocido (salvaguarda
        defensiva; no debería ocurrir en la práctica, ya que
        `build_parser` exige un subcomando válido mediante `argparse`).
    """
    if args.command == "investigate":
        return investigate(args.ticker, config=config, provider=provider)

    raise ValueError(f"Comando desconocido: {args.command!r}")
