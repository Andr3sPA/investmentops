"""Pruebas para la validación básica del ticker en la CLI
(investmentops.cli._validate_ticker, integrada en build_parser/parse_args).

Cubre la tarea "Implementar la validación básica del ticker (no vacío,
formato esperado)" (TASKS.md, Fase 1, "CLI"). No prueba de nuevo el
parseo básico ya cubierto en `test_cli.py` (comando/ticker válidos,
ticker con puntos, subcomando ausente/desconocido); solo agrega los
casos nuevos de esta tarea: ticker vacío y ticker compuesto solo de
espacios.
"""

import argparse

import pytest

from investmentops.cli import build_parser, parse_args


def test_parse_args_raises_system_exit_when_ticker_is_empty_string() -> None:
    with pytest.raises(SystemExit):
        parse_args(["investigate", ""])


def test_parse_args_raises_system_exit_when_ticker_is_only_whitespace() -> None:
    with pytest.raises(SystemExit):
        parse_args(["investigate", "   "])


def test_parse_args_accepts_valid_ticker_after_validation_added() -> None:
    """Confirma que la validación no rompe el caso válido ya cubierto en
    test_cli.py (regresión mínima tras agregar `type=_validate_ticker`)."""
    args = parse_args(["investigate", "AAPL"])

    assert args.command == "investigate"
    assert args.ticker == "AAPL"


def test_parse_args_does_not_strip_or_normalize_valid_ticker() -> None:
    """La validación solo rechaza vacío/solo-espacios; no recorta ni
    normaliza un ticker válido (esa no es responsabilidad de la CLI, ver
    CLI.md)."""
    args = parse_args(["investigate", "ecopetrol.cl"])

    assert args.ticker == "ecopetrol.cl"


def test_investigate_ticker_argument_declares_a_type_validator() -> None:
    """Confirma que el argumento `ticker` del subparser `investigate` usa
    un validador (`type=`), en vez de depender solo de la presencia del
    argumento."""
    parser = build_parser()
    investigate_parser = parser._subparsers._group_actions[0].choices["investigate"]
    ticker_action = next(
        action for action in investigate_parser._actions if action.dest == "ticker"
    )

    assert ticker_action.type is not None
