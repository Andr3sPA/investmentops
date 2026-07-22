"""Pruebas para el modelo de dominio "Comparables"
(investmentops.data_layer.Comparables / PeerComparable).

Cubre la tarea "Definir el modelo de dominio 'Comparables' (conjunto de
empresas pares y sus métricas equivalentes)" (TASKS.md, Fase 5,
"Normalización"). No prueba ninguna transformación desde datos crudos de
un proveedor: eso corresponde a una tarea posterior (ver TASKS.md,
"Implementar la transformación de los datos crudos de comparables al
modelo normalizado").
"""

from datetime import date

import pytest

from investmentops.data_layer import Comparables, FinancialStatement, MarketData, PeerComparable


def _financial_statement(revenue: float = 1_000_000.0) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _market_data(price: float = 185.5) -> MarketData:
    return MarketData(
        price=price,
        market_cap=2_900_000_000_000.0,
        multiples={},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def _peer(ticker: str = "MSFT") -> PeerComparable:
    return PeerComparable(
        ticker=ticker,
        financial_statement=_financial_statement(),
        market_data=_market_data(),
    )


def test_peer_comparable_holds_ticker_and_normalized_cuts() -> None:
    statement = _financial_statement()
    market_data = _market_data()

    peer = PeerComparable(
        ticker="MSFT", financial_statement=statement, market_data=market_data
    )

    assert peer.ticker == "MSFT"
    assert peer.financial_statement == statement
    assert peer.market_data == market_data


def test_peer_comparable_is_immutable() -> None:
    peer = _peer()

    with pytest.raises(AttributeError):
        peer.ticker = "GOOG"  # type: ignore[misc]


def test_comparables_holds_ticker_and_ordered_peers() -> None:
    msft = _peer("MSFT")
    googl = _peer("GOOGL")

    comparables = Comparables(ticker="AAPL", peers=[msft, googl])

    assert comparables.ticker == "AAPL"
    assert comparables.peers == [msft, googl]
    assert comparables.peers[0].ticker == "MSFT"
    assert comparables.peers[1].ticker == "GOOGL"


def test_comparables_is_immutable() -> None:
    comparables = Comparables(ticker="AAPL", peers=[_peer()])

    with pytest.raises(AttributeError):
        comparables.ticker = "MSFT"  # type: ignore[misc]


def test_comparables_supports_no_peers() -> None:
    """Una empresa sin pares según el proveedor es un caso válido (ver
    FMPComparablesProvider.fetch, 'lista vacía es una respuesta válida')."""
    comparables = Comparables(ticker="AAPL", peers=[])

    assert comparables.peers == []


def test_comparables_preserves_order_of_peers_as_given() -> None:
    """El orden se preserva tal cual se entregue, sin reordenar (ver
    COMPARABLES_PROVIDER.md: la lista de pares se usa tal cual la
    entrega FMP)."""
    peers = [_peer("ZZZ"), _peer("AAA"), _peer("MMM")]

    comparables = Comparables(ticker="AAPL", peers=peers)

    assert [peer.ticker for peer in comparables.peers] == ["ZZZ", "AAA", "MMM"]


def test_each_peer_preserves_its_own_financial_statement_and_market_data() -> None:
    msft = PeerComparable(
        ticker="MSFT",
        financial_statement=_financial_statement(revenue=2_000_000.0),
        market_data=_market_data(price=300.0),
    )
    googl = PeerComparable(
        ticker="GOOGL",
        financial_statement=_financial_statement(revenue=1_500_000.0),
        market_data=_market_data(price=140.0),
    )

    comparables = Comparables(ticker="AAPL", peers=[msft, googl])

    assert comparables.peers[0].financial_statement.revenue == 2_000_000.0
    assert comparables.peers[0].market_data.price == 300.0
    assert comparables.peers[1].financial_statement.revenue == 1_500_000.0
    assert comparables.peers[1].market_data.price == 140.0