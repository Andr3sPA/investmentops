"""Pruebas para el parseo de argumentos de la CLI (investmentops.cli).

Cubre la tarea "Implementar el parseo del argumento ticker" (TASKS.md,
Fase 1, "CLI"), siguiendo la sintaxis ya fijada en
`investmentops/cli/CLI.md`: `investigate TICKER`. No prueba la
validación de contenido del ticker, la conexión con el orquestador, ni
la impresión de resultados/errores en consola: esas son tareas
separadas y posteriores de la misma sección.
"""

import argparse

import pytest

from investmentops.cli import build_parser, parse_args


def test_build_parser_returns_argument_parser() -> None:
    parser = build_parser()

    assert isinstance(parser, argparse.ArgumentParser)


def test_parse_args_investigate_returns_command_and_ticker() -> None:
    args = parse_args(["investigate", "AAPL"])

    assert args.command == "investigate"
    assert args.ticker == "AAPL"


def test_parse_args_does_not_normalize_ticker() -> None:
    """La normalización (ej. a mayúsculas) no es responsabilidad de la CLI
    (ver CLI.md); el valor debe pasar tal cual se recibió."""
    args = parse_args(["investigate", "ecopetrol.cl"])

    assert args.ticker == "ecopetrol.cl"


def test_parse_args_supports_tickers_with_dots() -> None:
    args = parse_args(["investigate", "ECOPETROL.CL"])

    assert args.ticker == "ECOPETROL.CL"


def test_parse_args_raises_system_exit_when_ticker_missing() -> None:
    with pytest.raises(SystemExit):
        parse_args(["investigate"])


def test_parse_args_raises_system_exit_when_command_missing() -> None:
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_raises_system_exit_for_unknown_command() -> None:
    with pytest.raises(SystemExit):
        parse_args(["unknown_command", "AAPL"])


def test_investigate_subparser_prog_name_is_investmentops() -> None:
    parser = build_parser()

    assert parser.prog == "investmentops"
