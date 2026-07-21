"""Pruebas para la consulta de métricas clave de empresas pares
(investmentops.core.orchestrator.fetch_peer_tickers /
fetch_peer_key_metrics).

Cubre la tarea "Implementar la consulta de métricas clave (las ya
normalizadas en fases previas) para cada empresa par" (TASKS.md, Fase 5,
"Fuente de datos de comparables"). No prueba de nuevo `FMPComparablesProvider`
(ya cubierto en `test_data_providers_comparables.py`) ni `fetch_and_normalize`
(ya cubierto en `test_core_orchestrator.py`) más allá de lo necesario para
confirmar que `fetch_peer_key_metrics` los encadena correctamente. No
prueba procedencia por empresa par individual: tarea separada y posterior
de la misma sección.
"""

from datetime import date, datetime, timezone

import pytest

from investmentops.core.orchestrator import (
    PeerMetrics,
    fetch_peer_key_metrics,
    fetch_peer_tickers,
)
from investmentops.data_layer import FinancialStatement, MarketData
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyComparablesProvider:
    """Proveedor mínimo de prueba con la misma forma que `FMPComparablesProvider`."""

    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload
        self.received_ticker: str | None = None

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_ticker = ticker
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_comparables_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingComparablesProvider:
    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"No se pudo obtener comparables para '{ticker}'")


class _DummyFundamentalsProvider:
    """Proveedor mínimo de prueba con la misma forma que `FMPFundamentalsProvider`."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.received_tickers: list[str] = []

    def fetch(self, ticker: str) -> RawProviderData:
        self.received_tickers.append(ticker)
        return RawProviderData(
            ticker=ticker,
            payload=self._payload,
            metadata=ProviderMetadata(
                source="dummy_fundamentals_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingFundamentalsProvider:
    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


def _peers_payload(peers: list[str]) -> list[dict]:
    return [
        {
            "symbol": "AAPL",
            "companyName": "Apple Inc.",
            "peersList": peers,
        }
    ]


def _complete_fundamentals_payload() -> dict:
    return {
        "income_statement": [
            {"date": "2025-12-31", "revenue": 1_000_000.0, "netIncome": 150_000.0}
        ],
        "balance_sheet_statement": [{"date": "2025-12-31", "totalDebt": 400_000.0}],
        "quote": [
            {"price": 185.5, "marketCap": 2_900_000_000_000.0, "timestamp": 1735689600}
        ],
    }


# --- fetch_peer_tickers -------------------------------------------------------


def test_fetch_peer_tickers_returns_peers_from_payload() -> None:
    provider = _DummyComparablesProvider(_peers_payload(["MSFT", "GOOG", "GOOGL"]))

    result = fetch_peer_tickers("AAPL", provider=provider)

    assert result == ["MSFT", "GOOG", "GOOGL"]


def test_fetch_peer_tickers_passes_ticker_to_provider() -> None:
    provider = _DummyComparablesProvider(_peers_payload(["MSFT"]))

    fetch_peer_tickers("AAPL", provider=provider)

    assert provider.received_ticker == "AAPL"


def test_fetch_peer_tickers_returns_empty_list_when_payload_empty() -> None:
    provider = _DummyComparablesProvider([])

    result = fetch_peer_tickers("AAPL", provider=provider)

    assert result == []


def test_fetch_peer_tickers_returns_empty_list_when_peers_list_missing() -> None:
    provider = _DummyComparablesProvider(
        [{"symbol": "AAPL", "companyName": "Apple Inc."}]
    )

    result = fetch_peer_tickers("AAPL", provider=provider)

    assert result == []


def test_fetch_peer_tickers_propagates_provider_failure() -> None:
    with pytest.raises(DataProviderError, match="No se pudo obtener comparables"):
        fetch_peer_tickers("AAPL", provider=_FailingComparablesProvider())


def test_fetch_peer_tickers_preserves_order() -> None:
    provider = _DummyComparablesProvider(_peers_payload(["ZZZ", "AAA", "MMM"]))

    result = fetch_peer_tickers("AAPL", provider=provider)

    assert result == ["ZZZ", "AAA", "MMM"]


# --- fetch_peer_key_metrics ---------------------------------------------------


def test_fetch_peer_key_metrics_returns_one_entry_per_peer() -> None:
    comparables_provider = _DummyComparablesProvider(_peers_payload(["MSFT", "GOOG"]))
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    result = fetch_peer_key_metrics(
        "AAPL",
        comparables_provider=comparables_provider,
        fundamentals_provider=fundamentals_provider,
    )

    assert len(result) == 2
    assert all(isinstance(entry, PeerMetrics) for entry in result)
    assert [entry.ticker for entry in result] == ["MSFT", "GOOG"]


def test_fetch_peer_key_metrics_queries_fundamentals_provider_for_each_peer() -> None:
    comparables_provider = _DummyComparablesProvider(_peers_payload(["MSFT", "GOOG"]))
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    fetch_peer_key_metrics(
        "AAPL",
        comparables_provider=comparables_provider,
        fundamentals_provider=fundamentals_provider,
    )

    assert fundamentals_provider.received_tickers == ["MSFT", "GOOG"]


def test_fetch_peer_key_metrics_reuses_fetch_and_normalize_output() -> None:
    comparables_provider = _DummyComparablesProvider(_peers_payload(["MSFT"]))
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    result = fetch_peer_key_metrics(
        "AAPL",
        comparables_provider=comparables_provider,
        fundamentals_provider=fundamentals_provider,
    )

    entry = result[0]
    assert isinstance(entry.financial_statement, FinancialStatement)
    assert entry.financial_statement.revenue == 1_000_000.0
    assert entry.financial_statement.net_income == 150_000.0
    assert entry.financial_statement.debt == 400_000.0
    assert entry.financial_statement.period_end == date(2025, 12, 31)
    assert isinstance(entry.market_data, MarketData)
    assert entry.market_data.price == 185.5
    assert entry.market_data.market_cap == 2_900_000_000_000.0


def test_fetch_peer_key_metrics_returns_empty_list_when_no_peers() -> None:
    comparables_provider = _DummyComparablesProvider([])
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    result = fetch_peer_key_metrics(
        "AAPL",
        comparables_provider=comparables_provider,
        fundamentals_provider=fundamentals_provider,
    )

    assert result == []
    assert fundamentals_provider.received_tickers == []


def test_fetch_peer_key_metrics_propagates_comparables_provider_failure() -> None:
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    with pytest.raises(DataProviderError, match="No se pudo obtener comparables"):
        fetch_peer_key_metrics(
            "AAPL",
            comparables_provider=_FailingComparablesProvider(),
            fundamentals_provider=fundamentals_provider,
        )


def test_fetch_peer_key_metrics_propagates_peer_fundamentals_failure() -> None:
    comparables_provider = _DummyComparablesProvider(_peers_payload(["MSFT"]))

    with pytest.raises(DataProviderError, match="no encontrado"):
        fetch_peer_key_metrics(
            "AAPL",
            comparables_provider=comparables_provider,
            fundamentals_provider=_FailingFundamentalsProvider(),
        )


def test_peer_metrics_is_immutable() -> None:
    comparables_provider = _DummyComparablesProvider(_peers_payload(["MSFT"]))
    fundamentals_provider = _DummyFundamentalsProvider(_complete_fundamentals_payload())

    result = fetch_peer_key_metrics(
        "AAPL",
        comparables_provider=comparables_provider,
        fundamentals_provider=fundamentals_provider,
    )

    with pytest.raises(AttributeError):
        result[0].ticker = "OTHER"  # type: ignore[misc]