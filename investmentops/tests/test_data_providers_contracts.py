"""Pruebas para el contrato de "data provider" (investmentops.data_providers).

Cubre la tarea "Definir el contrato de 'data provider' (entrada: ticker;
salida: datos crudos + metadatos de procedencia)" (TASKS.md, Fase 1,
"Contratos e interfaces"). No prueba ningún proveedor concreto: eso
corresponde a una tarea posterior (ver TASKS.md, "Fuente de datos
fundamentales").
"""

from datetime import datetime, timezone

import pytest

from investmentops.data_providers import (
    DataProvider,
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)


class _DummyProvider:
    """Proveedor mínimo de prueba que cumple el contrato `DataProvider`."""

    def fetch(self, ticker: str) -> RawProviderData:
        return RawProviderData(
            ticker=ticker,
            payload={"revenue": 1000},
            metadata=ProviderMetadata(
                source="dummy_provider",
                queried_at=datetime.now(timezone.utc),
                reliability="alta",
            ),
        )


class _FailingProvider:
    """Proveedor mínimo de prueba que señala un fallo mediante el contrato."""

    def fetch(self, ticker: str) -> RawProviderData:
        raise DataProviderError(f"Ticker '{ticker}' no encontrado")


def test_dummy_provider_satisfies_data_provider_protocol() -> None:
    provider = _DummyProvider()

    assert isinstance(provider, DataProvider)


def test_fetch_returns_raw_provider_data_with_metadata() -> None:
    provider = _DummyProvider()

    result = provider.fetch("AAPL")

    assert isinstance(result, RawProviderData)
    assert result.ticker == "AAPL"
    assert result.payload == {"revenue": 1000}
    assert isinstance(result.metadata, ProviderMetadata)
    assert result.metadata.source == "dummy_provider"
    assert result.metadata.reliability == "alta"
    assert isinstance(result.metadata.queried_at, datetime)


def test_failing_provider_raises_data_provider_error() -> None:
    provider = _FailingProvider()

    with pytest.raises(DataProviderError, match="no encontrado"):
        provider.fetch("NOPE")


def test_data_provider_error_is_a_runtime_error() -> None:
    assert issubclass(DataProviderError, RuntimeError)


def test_raw_provider_data_is_immutable() -> None:
    metadata = ProviderMetadata(
        source="dummy_provider",
        queried_at=datetime.now(timezone.utc),
        reliability="alta",
    )
    data = RawProviderData(ticker="AAPL", payload={}, metadata=metadata)

    with pytest.raises(AttributeError):
        data.ticker = "MSFT"  # type: ignore[misc]


def test_provider_metadata_is_immutable() -> None:
    metadata = ProviderMetadata(
        source="dummy_provider",
        queried_at=datetime.now(timezone.utc),
        reliability="alta",
    )

    with pytest.raises(AttributeError):
        metadata.source = "otro_proveedor"  # type: ignore[misc]
