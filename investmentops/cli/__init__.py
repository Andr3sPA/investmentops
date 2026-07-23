"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida, comparar dos o más empresas).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Cubre siete tareas:

Fase 1, "CLI" (TASKS.md):
- "Implementar el parseo del argumento ticker." (`build_parser`,
  `parse_args`), siguiendo la sintaxis ya decidida y documentada en
  `investmentops/cli/CLI.md`: un único subcomando, `investigate`, con un
  argumento posicional obligatorio `TICKER`.
- "Implementar la validación básica del ticker (no vacío, formato
  esperado)." (`_validate_ticker`).
- "Conectar el comando con el orquestador." (`dispatch`).
- "Implementar la impresión en consola del resultado (texto simple, sin
  formato de reporte todavía)." (`format_research_result`).

Fase 2, "Orquestador y CLI" (TASKS.md):
- "Añadir al comando CLI la opción de formato de salida (markdown, html,
  o ambos)." — flag `--format` sobre el subcomando `investigate`
  (`build_parser`), consumido por `dispatch` para generar los reportes
  solicitados vía `investmentops.core.orchestrator.investigate_and_generate_reports`.

Fase 5, "Orquestador y CLI" (TASKS.md):
- "Implementar el parseo de argumentos del comando de comparación (lista
  de tickers)." — nuevo subcomando `compare`, sobre la sintaxis ya fijada
  en `investmentops/cli/COMPARE_CLI.md`.
- "Conectar el comando CLI de comparación con esa función del
  orquestador." (esta tarea) — `dispatch` ahora reconoce
  `args.command == "compare"`, invocando
  `investmentops.core.orchestrator.compare(args.tickers, config=config,
  provider=provider)` y devolviendo el `ComparisonResult` obtenido, sin
  modificar el comportamiento ya existente para `"investigate"`.

```
python -m investmentops investigate TICKER
python -m investmentops investigate TICKER --format markdown
python -m investmentops investigate TICKER --format html
python -m investmentops investigate TICKER --format both
python -m investmentops compare TICKER1 TICKER2 [TICKER3 ...]

```
## Parseo (`build_parser`/`parse_args`)

Construye el `ArgumentParser` (con `add_subparsers`, tal como fija
`CLI.md`) y expone una función que, dada una lista de argumentos,
devuelve el resultado ya parseado.

- **No normaliza** el ticker (ej. a mayúsculas): esa normalización ya
  ocurre más abajo en el pipeline (ver
  `investmentops.data_providers.fundamentals.FMPFundamentalsProvider.fetch`
  y `investmentops.core.orchestrator.assemble_research_result`), conforme
  a `CLI.md`: "no es responsabilidad de la capa CLI". Mismo criterio
  aplicado a los tickers de `compare` (ver `COMPARE_CLI.md`, "Sin
  normalización ni deduplicación de tickers en esta capa").
- **`--format`** es un flag opcional del subcomando `investigate`, con
  `choices` restringidos a `"markdown"`, `"html"` y `"both"` (validados
  nativamente por `argparse`: un valor fuera de esa lista termina el
  proceso con `SystemExit`, mismo mecanismo ya usado para el resto de
  errores de parseo de esta CLI). Su valor por defecto es `None`
  (ausente): si el usuario no pide un formato, `args.format` es `None`
  y `dispatch` se comporta exactamente igual que en la Fase 1 (sin
  generar ningún archivo de reporte).
- **`compare`** es un segundo subcomando, agregado junto a
  `investigate` sin modificar su sintaxis ni su comportamiento (ver
  `COMPARE_CLI.md`, "Decisión: subcomando `compare`..."). Su único
  argumento posicional, `tickers`, es **variádico** (`nargs="+"`, cada
  elemento validado individualmente con `_validate_ticker`, mismo
  criterio ya usado por `investigate`) y exige un **mínimo de dos**
  tickers mediante `_MinimumTwoTickersAction` (ver más abajo). Sin flags
  adicionales todavía (ej. `--format`): su necesidad se decidirá, si
  aplica, en la sección "Reportes" de esta misma fase (ver
  `COMPARE_CLI.md`, "Sin flags adicionales en esta tarea").

## Validación básica (`_validate_ticker`)

Se implementa como una función `type=` de `argparse`, el mismo mecanismo
nativo que ya usa `argparse` para exigir que un argumento posicional esté
*presente*: si `_validate_ticker` levanta `argparse.ArgumentTypeError`,
`argparse` lo traduce automáticamente a un mensaje de error en `stderr` y
un `SystemExit`, igual comportamiento que ya tienen los demás errores de
parseo de esta CLI (ticker ausente, subcomando ausente/desconocido,
formato desconocido). Se reutiliza sin cambios como `type=` de cada
elemento de `tickers` en `compare` (`nargs="+"` aplica `type=` a cada
valor individual antes de agruparlos en la lista).

"Formato esperado", en el alcance de esta tarea, es deliberadamente
mínimo: no vacío y no compuesto solo de espacios en blanco. No se aplica
ninguna expresión regular ni se restringe la forma del ticker (longitud,
mayúsculas, símbolos permitidos): el modelo de dominio `Company` (ver
`investmentops/data_layer/domain.py`) ya documenta que no impone un
formato fijo de ticker (soporta, por ejemplo, tickers con puntos del
mercado colombiano como `"ECOPETROL.CL"`).

## Mínimo de dos tickers en `compare` (`_MinimumTwoTickersAction`)

`argparse` no ofrece nativamente un mecanismo para exigir un mínimo de
elementos en un argumento `nargs="+"` (que ya garantiza "uno o más", no
"dos o más"). Se implementa como una `argparse.Action` propia:
`_MinimumTwoTickersAction.__call__` recibe la lista ya parseada y
validada individualmente (`_validate_ticker` ya corrió sobre cada
elemento antes de llegar aquí), y si tiene menos de dos elementos, llama
a `parser.error(...)` — el mismo método interno que usa `argparse` para
señalar cualquier otro error de parseo (imprime el mensaje de uso +
error en `stderr` y termina el proceso con `SystemExit`, código 2). Si
el mínimo se cumple, simplemente asigna la lista al namespace
(`setattr(namespace, self.dest, values)`), comportamiento equivalente al
de `argparse._StoreAction` por defecto.

## Conexión de `compare` con el orquestador (`dispatch`, esta tarea)

`dispatch` ahora reconoce `args.command == "compare"`: invoca
`investmentops.core.orchestrator.compare(args.tickers, config=config,
provider=provider)` (ya implementada en la tarea anterior de esta misma
sección) y devuelve el `ComparisonResult` obtenido tal cual, sin
transformarlo. Sigue exactamente el mismo criterio ya usado para
`"investigate"`: `provider`/`config` son los mismos parámetros ya
aceptados por `dispatch`, propagados sin cambios; no se agrega un
parámetro `news_provider` a `dispatch` en esta tarea, porque la rama de
`"investigate"` tampoco lo propaga hoy — mantener ambas ramas
consistentes entre sí es preferible a introducir una asimetría nueva sin
necesidad concreta. `compare` internamente ya usa `news_provider=None`
por defecto para cada `investigate(...)` que ejecuta (ver
`investmentops/core/orchestrator.py`), igual que la propia rama de
`"investigate"` de `dispatch`.

Esta tarea no toca `format_research_result`: formatear un
`ComparisonResult` para consola (en vez de un `ResearchResult` a secas)
es explícitamente parte de "Reportes" en esta misma fase, no de esta
tarea de conexión.

## Fuera de alcance de esta tarea (aún, ver TASKS.md, "Orquestador y CLI")

- La impresión en consola del resultado comparativo y el manejo de
  errores específicos de `compare`: no desglosadas todavía como tareas
  explícitas en `TASKS.md` para esta sección.
- Cualquier sección de reporte de comparación (Markdown/HTML): tareas
  separadas y posteriores en la sección "Reportes" de esta misma fase.
- Los subcomandos de fases posteriores (listar investigaciones,
  watchlist, ver `ROADMAP.md`, Fases 7 y 8): no se anticipan aquí.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from investmentops.core.orchestrator import (
    ComparisonResult,
    compare,
    investigate,
    investigate_and_generate_reports,
)
from investmentops.core.research_result import ResearchResult
from investmentops.data_providers.contracts import DataProvider

#: Nombre del programa mostrado en la ayuda de la CLI (`--help`), consistente
#: con la forma de invocación ya fijada en `investmentops/cli/CLI.md`:
#: `python -m investmentops <subcomando> [argumentos]`.
PROG_NAME = "investmentops"

#: Mapeo del valor recibido en `--format` (tal como lo restringe
#: `choices` en `build_parser`) a los formatos concretos que debe generar
#: `investmentops.core.orchestrator.generate_reports`/
#: `investigate_and_generate_reports` (parámetro `formats`, ver ese
#: módulo). `"both"` no es un formato de reporte en sí mismo — es un
#: alias de conveniencia de la CLI para "ambos formatos existentes" — por
#: lo que este mapeo, y no `ALL_REPORT_FORMATS` directamente, es lo que
#: traduce el vocabulario de la CLI al vocabulario del orquestador.
_FORMAT_TO_REPORT_FORMATS: dict[str, tuple[str, ...]] = {
    "markdown": ("markdown",),
    "html": ("html",),
    "both": ("markdown", "html"),
}

#: Número mínimo de tickers exigido por el subcomando `compare` (ver
#: `investmentops/cli/COMPARE_CLI.md`: "una comparación requiere al
#: menos dos empresas").
_MIN_COMPARE_TICKERS = 2


def _validate_ticker(value: str) -> str:
    """Valida que el ticker recibido no esté vacío ni sea solo espacios.

    Usada como `type=` del argumento posicional `ticker` en
    `build_parser` (subcomando `investigate`) y de cada elemento de
    `tickers` en el subcomando `compare`. `argparse` invoca esta función
    con el valor crudo recibido en la línea de comandos; si levanta
    `argparse.ArgumentTypeError`, `argparse` lo traduce automáticamente a
    un mensaje de error en `stderr` y termina el proceso con
    `SystemExit`, el mismo mecanismo ya usado para el resto de errores de
    parseo de esta CLI (ver docstring del módulo).

    Parameters
    ----------
    value:
        El valor crudo del argumento tal como lo recibió `argparse`, sin
        procesar.

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


class _MinimumTwoTickersAction(argparse.Action):
    """Exige un mínimo de dos tickers para el argumento `tickers` de `compare`.

    `nargs="+"` ya garantiza "uno o más" elementos, pero
    `investmentops/cli/COMPARE_CLI.md` exige explícitamente un mínimo de
    **dos** (una comparación requiere al menos dos empresas; un único
    ticker ya está cubierto por `investigate`). `argparse` no ofrece un
    mecanismo nativo para ese mínimo, por lo que se implementa como una
    `Action` propia: si `values` (ya validados individualmente por
    `_validate_ticker`, que corre antes vía `type=`) tiene menos de
    `_MIN_COMPARE_TICKERS` elementos, se levanta el mismo error que
    `argparse` usaría para cualquier otro problema de parseo
    (`parser.error(...)`: mensaje de uso + error en `stderr`, y
    `SystemExit` con código 2), sin introducir un mecanismo de error
    distinto al ya usado por el resto de esta CLI.
    """

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: Any,
        option_string: str | None = None,
    ) -> None:
        if len(values) < _MIN_COMPARE_TICKERS:
            parser.error(
                "compare requiere al menos "
                f"{_MIN_COMPARE_TICKERS} tickers (se recibió "
                f"{len(values)})."
            )
        setattr(namespace, self.dest, values)


def build_parser() -> argparse.ArgumentParser:
    """Construye el `ArgumentParser` de la CLI, con sus subcomandos.

    Implementa la estructura de subcomandos (`argparse` con
    `add_subparsers`) ya decidida en `investmentops/cli/CLI.md`. Expone
    dos subcomandos:

    - `investigate`: un argumento posicional obligatorio `ticker`
      (validado mediante `_validate_ticker`: no vacío, no solo espacios)
      y un flag opcional `--format` (valores admitidos: `markdown`,
      `html`, `both`; por defecto ausente, sin generar ningún reporte).
    - `compare` (ver `investmentops/cli/COMPARE_CLI.md`): un
      argumento posicional variádico `tickers` (`nargs="+"`, cada
      elemento validado con `_validate_ticker`), con un mínimo de dos
      elementos exigido por `_MinimumTwoTickersAction`. Sin flags
      adicionales todavía.

    Subcomandos futuros (listar investigaciones, watchlist) se añadirán
    aquí como subparsers adicionales, sin modificar los existentes,
    cuando les corresponda su propia tarea (ver `CLI.md`, "Decisión:
    subcomandos").

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
    investigate_parser.add_argument(
        "--format",
        choices=sorted(_FORMAT_TO_REPORT_FORMATS),
        default=None,
        help=(
            "Genera y guarda en disco el reporte de la investigación en "
            "el formato indicado ('markdown', 'html', o 'both' para "
            "ambos), además de la salida en consola. Si se omite, no se "
            "genera ningún archivo de reporte."
        ),
    )

    compare_parser = subparsers.add_parser(
        "compare",
        help="Compara dos o más empresas a partir de sus tickers.",
    )
    compare_parser.add_argument(
        "tickers",
        nargs="+",
        type=_validate_ticker,
        action=_MinimumTwoTickersAction,
        help=(
            "Tickers de las empresas a comparar, mínimo dos (ej. AAPL "
            "MSFT GOOGL)."
        ),
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
        `command == "investigate"`, `ticker` (el valor tal cual se
        recibió, ya validado como no vacío/no solo espacios por
        `_validate_ticker`, pero sin normalizar, ver docstring del
        módulo) y `format` (`"markdown"`, `"html"`, `"both"`, o `None`
        si no se indicó `--format`). Para el subcomando `compare`, expone
        `command == "compare"` y `tickers` (la lista de valores tal cual
        se recibieron, cada uno ya validado individualmente, sin
        normalizar; ya garantizada con al menos dos elementos).

    Raises
    ------
    SystemExit
        Comportamiento estándar de `argparse` si falta el subcomando, si
        falta el argumento posicional `ticker` (`investigate`) o
        `tickers` (`compare`), si algún ticker está vacío o es solo
        espacios (ver `_validate_ticker`), si `compare` recibe menos de
        dos tickers (ver `_MinimumTwoTickersAction`), si `--format`
        recibe un valor fuera de `{"markdown", "html", "both"}`, o si se
        pasa `--help`/`-h` (imprime ayuda/error y termina el proceso).
        Este módulo no atrapa ni traduce esa excepción: es el mecanismo
        de error nativo de `argparse`, consistente con una CLI estándar.
    """
    parser = build_parser()
    return parser.parse_args(argv)


def dispatch(
    args: argparse.Namespace,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
    output_dir: str | Path | None = None,
) -> ResearchResult | tuple[ResearchResult, list[Path]] | ComparisonResult:
    """Conecta el comando ya parseado con el orquestador.

    Traduce el `argparse.Namespace` producido por `parse_args` en una
    llamada real al orquestador (`investmentops.core.orchestrator`).

    - **`"investigate"`**: sin `--format`, invoca
      `investigate(args.ticker, config=config, provider=provider)` y
      devuelve el `ResearchResult` obtenido. Con `--format`, invoca en
      su lugar `investigate_and_generate_reports(...)`, devolviendo
      `tuple[ResearchResult, list[Path]]`.
    - **`"compare"`** (esta tarea): invoca
      `investmentops.core.orchestrator.compare(args.tickers,
      config=config, provider=provider)` y devuelve el `ComparisonResult`
      obtenido tal cual, sin transformarlo. Mismo criterio ya usado por
      `"investigate"`: no se propaga ningún `news_provider` desde
      `dispatch` (la rama de `"investigate"` tampoco lo hace hoy);
      `compare` ya usa `news_provider=None` por defecto internamente
      para cada `investigate(...)` que ejecuta.

    Parameters
    ----------
    args:
        El `argparse.Namespace` ya parseado y validado (ver
        `parse_args`).
    config:
        Configuración ya cargada, propagada tal cual a
        `investigate(...)`/`investigate_and_generate_reports(...)`/
        `compare(...)`.
    provider:
        Proveedor de datos ya construido, propagado tal cual al
        orquestador.
    output_dir:
        Ruta al directorio donde guardar los reportes generados, si
        `args.format` no es `None` (solo aplica a `"investigate"`).

    Returns
    -------
    ResearchResult | tuple[ResearchResult, list[Path]] | ComparisonResult
        Ver el detalle por comando arriba.

    Raises
    ------
    ValueError
        Si `args.command` no es `"investigate"` ni `"compare"`.
    ReportError, ConfigError
        Ver `investmentops.core.orchestrator.generate_reports`.
    """
    if args.command == "investigate":
        requested_format = getattr(args, "format", None)

        if requested_format is None:
            return investigate(args.ticker, config=config, provider=provider)

        return investigate_and_generate_reports(
            args.ticker,
            config=config,
            provider=provider,
            output_dir=output_dir,
            formats=_FORMAT_TO_REPORT_FORMATS[requested_format],
        )

    if args.command == "compare":
        return compare(args.tickers, config=config, provider=provider)

    raise ValueError(f"Comando desconocido: {args.command!r}")


def format_research_result(result: ResearchResult) -> str:
    """Formatea un `ResearchResult` como texto simple para consola.

    Cubre la tarea "Implementar la impresión en consola del resultado
    (texto simple, sin formato de reporte todavía)" (TASKS.md, Fase 1,
    "CLI"). Espera un `ResearchResult`, no la tupla que `dispatch` puede
    devolver cuando `args.format` no es `None`, ni el `ComparisonResult`
    que `dispatch` devuelve para `"compare"` (ver docstring de
    `dispatch`; la impresión en consola de un resultado comparativo es
    alcance de una tarea separada, todavía pendiente en TASKS.md,
    "Reportes").

    Esta función solo produce el texto: no imprime nada por sí misma
    (`print(format_research_result(result))` es responsabilidad de quien
    la invoque, ver `investmentops/__main__.py`).

    Parameters
    ----------
    result:
        El `ResearchResult` a formatear.

    Returns
    -------
    str
        Texto plano, multilínea, listo para imprimirse en consola. Nunca
        está vacío: si no hay `analysis_results`, lo indica
        explícitamente; si no hay `failures`, simplemente omite esa
        sección (no imprime un encabezado vacío).
    """
    lines: list[str] = []

    lines.append(f"Investigación: {result.company.ticker}")
    lines.append(f"Generado: {result.generated_at.isoformat()}")
    lines.append("")

    if not result.analysis_results:
        lines.append("No se completó ningún análisis.")
    else:
        for analysis in result.analysis_results:
            lines.append(f"=== {analysis.analysis_id} ===")
            for finding in analysis.findings:
                lines.append(finding)
            lines.append("")

            lines.append("Métricas de soporte:")
            if analysis.supporting_metrics:
                for key, value in analysis.supporting_metrics.items():
                    lines.append(f"  - {key}: {value}")
            else:
                lines.append("  (ninguna)")

            if analysis.limitations:
                lines.append("Limitaciones:")
                for limitation in analysis.limitations:
                    lines.append(f"  - {limitation}")

            lines.append(
                f"(Proveedor de IA: {analysis.provenance.ai_provider}, "
                f"modelo: {analysis.provenance.ai_model})"
            )
            lines.append("")

    if result.failures:
        lines.append("=== Fallos parciales ===")
        for failure in result.failures:
            lines.append(
                f"  - [{failure.stage}] {failure.identifier}: {failure.reason}"
            )
        lines.append("")

    return "\n".join(lines).rstrip("\n")