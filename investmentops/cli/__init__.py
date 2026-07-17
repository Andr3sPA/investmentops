"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Cubre cinco tareas:

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

```
python -m investmentops investigate TICKER
python -m investmentops investigate TICKER --format markdown
python -m investmentops investigate TICKER --format html
python -m investmentops investigate TICKER --format both
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
- **`--format`** es un flag opcional del subcomando `investigate`, con
  `choices` restringidos a `"markdown"`, `"html"` y `"both"` (validados
  nativamente por `argparse`: un valor fuera de esa lista termina el
  proceso con `SystemExit`, mismo mecanismo ya usado para el resto de
  errores de parseo de esta CLI). Su valor por defecto es `None`
  (ausente): si el usuario no pide un formato, `args.format` es `None`
  y `dispatch` se comporta exactamente igual que en la Fase 1 (sin
  generar ningún archivo de reporte).

## Validación básica (`_validate_ticker`)

Se implementa como una función `type=` de `argparse`, el mismo mecanismo
nativo que ya usa `argparse` para exigir que el argumento posicional
`ticker` esté *presente*: si `_validate_ticker` levanta
`argparse.ArgumentTypeError`, `argparse` lo traduce automáticamente a un
mensaje de error en `stderr` y un `SystemExit`, igual comportamiento que
ya tienen los demás errores de parseo de esta CLI (ticker ausente,
subcomando ausente/desconocido, formato desconocido, ver
`investmentops/tests/test_cli.py`).

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
(`investmentops.core.orchestrator`). Su comportamiento depende de
`args.format`:

- **`args.format is None`** (comportamiento histórico, sin cambios):
  invoca `investigate(args.ticker, config=config, provider=provider)` y
  devuelve el `ResearchResult` obtenido tal cual, sin transformarlo. No
  se genera ningún archivo. Este es el único camino que existía antes de
  esta tarea, y sigue siendo exactamente igual para cualquier llamador
  que no use `--format` (ver `investmentops/tests/test_cli_dispatch.py`,
  todas sus llamadas a `dispatch` siguen devolviendo un `ResearchResult`
  sin modificación alguna).
- **`args.format` es `"markdown"`, `"html"` o `"both"`** (nuevo en esta
  tarea): invoca
  `investigate_and_generate_reports(args.ticker, config=config,
  provider=provider, output_dir=output_dir, formats=<mapeo>)` (ver
  `_FORMAT_TO_REPORT_FORMATS` más abajo), y devuelve la tupla
  `(ResearchResult, list[Path])` que esa función produce. `dispatch`
  amplía así su tipo de retorno a `ResearchResult | tuple[ResearchResult,
  list[Path]]`, condicionado estrictamente a si el usuario pidió un
  formato de salida.

En ambos casos:
- **No imprime nada en consola** (eso sigue siendo responsabilidad de
  `format_research_result`, y de quien invoque `dispatch`, ver
  `investmentops/__main__.py`). Presentar en consola las rutas de los
  reportes generados cuando `dispatch` devuelve la tupla es alcance de
  la tarea siguiente ("Implementar el mensaje final en consola
  indicando dónde quedaron guardados los reportes generados",
  TASKS.md); `investmentops/__main__.py` **no se modificó** en esta
  tarea, por lo que invocar la CLI real con `--format` hoy generará los
  archivos correctamente pero `main()` todavía no sabe presentar la
  tupla resultante (se actualizará en la tarea siguiente).
- **No traduce ni maneja ningún error adicional** más allá de lo que ya
  hacían `investigate`/`investigate_and_generate_reports` (ver sus
  propios docstrings): `DataProviderError`, `NormalizationError`,
  `PromptError`, `AgentProviderSelectionError` y `AIProviderError` ya
  quedan reflejados como `ResearchFailure` dentro del propio
  `ResearchResult`; lo que puede seguir escapando (ej. `ConfigError` si
  falta `config.local.toml`, o `ReportError` si no se puede escribir el
  reporte en disco) se propaga tal cual desde `dispatch`.
- `config`, `provider` y `output_dir` son parámetros opcionales que se
  propagan directamente al orquestador, pensados sobre todo para pruebas.
- Si `args.command` no es un comando reconocido, levanta `ValueError`
  (salvaguarda defensiva, no debería ocurrir en la práctica).

## Impresión en consola (`format_research_result`)

`format_research_result(result)` traduce un `ResearchResult` (no la
tupla que `dispatch` puede devolver cuando se pide `--format`; ver
arriba) a un texto simple y legible, pensado para imprimirse
directamente en consola. Sin cambios en esta tarea; ver la sección
completa en versiones anteriores de este docstring o el código de la
función.

Fuera de alcance de este módulo (aún, ver TASKS.md, sección "CLI" /
"Orquestador y CLI"):
- El mensaje final en consola indicando dónde quedaron guardados los
  reportes generados cuando se usa `--format` (tarea separada y
  siguiente).
- Los subcomandos de fases posteriores (comparar, listar investigaciones,
  watchlist, ver `ROADMAP.md`, Fases 5, 7 y 8): no se anticipan aquí,
  siguiendo el mismo criterio de no sobre-diseñar ya aplicado en el resto
  del proyecto.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Sequence

from investmentops.core.orchestrator import investigate, investigate_and_generate_reports
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
    posicional obligatorio `ticker` (validado mediante `_validate_ticker`:
    no vacío, no solo espacios) y un flag opcional `--format` (valores
    admitidos: `markdown`, `html`, `both`; por defecto ausente, sin
    generar ningún reporte). Subcomandos futuros (comparar, listar
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
        si no se indicó `--format`).

    Raises
    ------
    SystemExit
        Comportamiento estándar de `argparse` si falta el subcomando, si
        falta el argumento posicional `ticker`, si el ticker está vacío o
        es solo espacios (ver `_validate_ticker`), si `--format` recibe
        un valor fuera de `{"markdown", "html", "both"}`, o si se pasa
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
    output_dir: str | Path | None = None,
) -> ResearchResult | tuple[ResearchResult, list[Path]]:
    """Conecta el comando ya parseado con el orquestador.

    Traduce el `argparse.Namespace` producido por `parse_args` en una
    llamada real al orquestador (`investmentops.core.orchestrator`). Ver
    "Conexión con el orquestador (`dispatch`)" en el docstring del
    módulo para el alcance exacto de esta función, incluyendo el nuevo
    comportamiento condicionado a `args.format` (ver esa sección para la
    explicación completa; resumen abajo).

    Parameters
    ----------
    args:
        El `argparse.Namespace` ya parseado y validado (ver
        `parse_args`). Para el único subcomando existente
        (`"investigate"`), se espera que exponga `args.ticker` y
        `args.format` (`None` si no se pidió `--format`).
    config:
        Configuración ya cargada, propagada tal cual a
        `investigate(...)`/`investigate_and_generate_reports(...)`.
        Pensado sobre todo para pruebas, para no depender de un
        `config.local.toml` real en disco. Si no se indica, el
        orquestador resuelve la configuración real por sí mismo.
    provider:
        Proveedor de datos ya construido, propagado tal cual al
        orquestador. Pensado sobre todo para pruebas. Si no se indica, el
        orquestador usa el proveedor por defecto (FMP).
    output_dir:
        Ruta al directorio donde guardar los reportes generados, si
        `args.format` no es `None`. Se ignora por completo si
        `args.format` es `None` (no se genera ningún reporte). Si no se
        indica, `generate_reports` la resuelve desde `config.local.toml`
        (sección `[output].output_dir`, ver CONFIGURATION.md).

    Returns
    -------
    ResearchResult | tuple[ResearchResult, list[Path]]
        - Si `args.format is None`: el `ResearchResult` devuelto por
          `investigate(...)`, sin transformar (comportamiento idéntico al
          de la Fase 1).
        - Si `args.format` es `"markdown"`, `"html"` o `"both"`: la tupla
          `(ResearchResult, list[Path])` devuelta por
          `investigate_and_generate_reports(...)`, con las rutas de los
          reportes ya generados y guardados en disco.

    Raises
    ------
    ValueError
        Si `args.command` no es un comando reconocido (salvaguarda
        defensiva; no debería ocurrir en la práctica, ya que
        `build_parser` exige un subcomando válido mediante `argparse`).
    ReportError, ConfigError
        Si `args.format` no es `None`, ver
        `investmentops.core.orchestrator.generate_reports` para los
        fallos que puede levantar la generación de reportes.
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

    raise ValueError(f"Comando desconocido: {args.command!r}")


def format_research_result(result: ResearchResult) -> str:
    """Formatea un `ResearchResult` como texto simple para consola.

    Cubre la tarea "Implementar la impresión en consola del resultado
    (texto simple, sin formato de reporte todavía)" (TASKS.md, Fase 1,
    "CLI"). Espera un `ResearchResult`, no la tupla que `dispatch` puede
    devolver cuando `args.format` no es `None` (ver docstring de
    `dispatch`); presentar esa tupla, incluyendo las rutas de los
    reportes generados, es alcance de la tarea siguiente ("Implementar
    el mensaje final en consola indicando dónde quedaron guardados los
    reportes generados").

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
