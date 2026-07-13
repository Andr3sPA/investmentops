"""Pruebas para el modelo de dominio "Datos de mercado"
(investmentops.data_layer.MarketData).

Cubre la tarea "Definir la estructura del modelo de dominio 'Datos de
mercado' (precio, capitalización, múltiplos, fecha de corte)" (TASKS.md,
Fase 1, "Contratos e interfaces"). No prueba ninguna transformación desde
datos crudos de un proveedor, ni el cálculo de múltiplos, ni series
históricas (varios cortes): eso corresponde a tareas posteriores (ver
TASKS.md, "Normalización y almacenamiento" y "Agente de análisis:
valoración").
"""

from datetime import date

import pytest

from investmentops.data_layer import MarketData


def test_market_data_holds_basic_figures_with_source_and_date() -> None:
    market_data = MarketData(
        price=185.5,
        market_cap=2_900_000_000_000.0,
        multiples={"pe": 18.4, "pb": 3.1},
        source="example_provider",
        as_of=date(2025, 12, 31),
    )

    assert market_data.price == 185.5
    assert market_data.market_cap == 2_900_000_000_000.0
    assert market_data.multiples == {"pe": 18.4, "pb": 3.1}
    assert market_data.source == "example_provider"
    assert market_data.as_of == date(2025, 12, 31)


def test_market_data_is_immutable() -> None:
    market_data = MarketData(
        price=185.5,
        market_cap=2_900_000_000_000.0,
        multiples={"pe": 18.4, "pb": 3.1},
        source="example_provider",
        as_of=date(2025, 12, 31),
    )

    with pytest.raises(AttributeError):
        market_data.price = 200.0  # type: ignore[misc]


def test_market_data_supports_empty_multiples() -> None:
    """Si la fuente no entrega múltiplos, el modelo no debe exigir ninguno."""
    market_data = MarketData(
        price=42.0,
        market_cap=1_000_000.0,
        multiples={},
        source="example_provider",
        as_of=date(2025, 6, 30),
    )

    assert market_data.multiples == {}


def test_market_data_does_not_restrict_multiple_names() -> None:
    """El modelo no impone una lista fija de múltiplos soportados."""
    market_data = MarketData(
        price=10.0,
        market_cap=500_000.0,
        multiples={"ev_ebitda": 7.2, "ps": 1.9},
        source="example_provider",
        as_of=date(2025, 9, 30),
    )

    assert market_data.multiples["ev_ebitda"] == 7.2
    assert market_data.multiples["ps"] == 1.9
