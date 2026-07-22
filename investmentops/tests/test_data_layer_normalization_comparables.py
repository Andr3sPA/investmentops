"""Pruebas para la transformación de datos crudos de comparables al
modelo de dominio "Comparables"
(investmentops.data_layer.normalization.comparables_from_raw).

Cubre la tarea "Implementar la transformación de los datos crudos de
comparables al modelo normalizado" (TASKS.md, Fase 5, "Normalización").
No prueba de nuevo `financial_statement_from_raw`/`market_data_from_raw`/
`financial_statement_series_from_raw`/`news_from_raw` (ya cubiertos en
sus propios archivos de prueba), ni la consulta real a FMP
(`FMPComparablesProvider.fetch`, ya cubierta en
`test_data_providers_comparables.py`/
`test_data_providers_comparables_provenance.py`): usa payloads con la
misma forma que ya produce `FMPComparablesProvider.fetch`.
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.data_layer import Comparables, FinancialStatement, MarketData
from investmentops.data_layer.normalization import (
    NormalizationError,
    comparables_from_raw,
)
from investmentops.data_providers.contracts import ProviderMetadata, RawProviderData


def _raw_comparables_data(payload: list, ticker: str = "AAPL") -> RawProviderData:
    return RawProviderData(
        ticker=ticker,
        payload=payload,
        metadata=ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        ),
    )


def _peers_payload(peers: list[str]) -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "peersList": peers,
            "source": "fmp",
            "queried_at": "2026-07-21T00:00:00+00:00",
        }
    ]


def _financial_statement(revenue: float = 1_000_000.0) -> FinancialStatement:
    return FinancialStatement(
        revenue=revenue,
        net_income=150_000.0,
        debt=400_000.0,
        source="fmp",
        period_end=date(2025, 12, 31),
    )


def _market_data(price: float = 300.0) -> MarketData:
    return MarketData(
        price=price,
        market_cap=2_500_000_000_000.0,
        multiples={},
        source="fmp",
        as_of=date(2025, 12, 31),
    )


def test_builds_comparables_with_peers_in_order() -> None:
    raw = _raw_comparables_data(_peers_payload(["MSFT", "GOOG"]))
    peer_data = {
        "MSFT": (_financial_statement(), _market_data()),
        "GOOG": (_financial_statement(), _market_data()),
    }

    comparables = comparables_from_raw(raw, peer_data)

    assert isinstance(comparables, Comparables)
    assert comparables.ticker == "AAPL"
    assert [peer.ticker for peer in comparables.peers] == ["MSFT", "GOOG"]


def test_uses_ticker_from_raw_not_from_payload() -> None:
    raw = _raw_comparables_data(_peers_payload(["MSFT"]), ticker="AAPL")
    peer_data = {"MSFT": (_financial_statement(), _market_data())}

    comparables = comparables_from_raw(raw, peer_data)

    assert comparables.ticker == "AAPL"


def test_each_peer_gets_its_own_financial_statement_and_market_data() -> None:
    raw = _raw_comparables_data(_peers_payload(["MSFT", "GOOG"]))
    msft_statement = _financial_statement(revenue=2_000_000.0)
    msft_market = _market_data(price=310.0)
    goog_statement = _financial_statement(revenue=1_500_000.0)
    goog_market = _market_data(price=140.0)
    peer_data = {
        "MSFT": (msft_statement, msft_market),
        "GOOG": (goog_statement, goog_market),
    }

    comparables = comparables_from_raw(raw, peer_data)

    assert comparables.peers[0].financial_statement == msft_statement
    assert comparables.peers[0].market_data == msft_market
    assert comparables.peers[1].financial_statement == goog_statement
    assert comparables.peers[1].market_data == goog_market


def test_empty_payload_returns_comparables_with_no_peers() -> None:
    raw = _raw_comparables_data([])

    comparables = comparables_from_raw(raw, {})

    assert comparables.ticker == "AAPL"
    assert comparables.peers == []


def test_payload_without_peers_list_returns_no_peers() -> None:
    raw = _raw_comparables_data(
        [{"symbol": "AAPL", "companyName": "Apple Inc.", "source": "fmp"}]
    )

    comparables = comparables_from_raw(raw, {})

    assert comparables.peers == []


def test_raises_when_peer_data_missing_for_a_ticker() -> None:
    raw = _raw_comparables_data(_peers_payload(["MSFT", "GOOG"]))
    peer_data = {"MSFT": (_financial_statement(), _market_data())}

    with pytest.raises(NormalizationError, match="GOOG"):
        comparables_from_raw(raw, peer_data)


def test_ignores_extra_entries_in_peer_data_not_in_peers_list() -> None:
    raw = _raw_comparables_data(_peers_payload(["MSFT"]))
    peer_data = {
        "MSFT": (_financial_statement(), _market_data()),
        "GOOG": (_financial_statement(), _market_data()),
    }

    comparables = comparables_from_raw(raw, peer_data)

    assert [peer.ticker for peer in comparables.peers] == ["MSFT"]


def test_normalization_error_is_a_runtime_error() -> None:
    assert issubclass(NormalizationError, RuntimeError)