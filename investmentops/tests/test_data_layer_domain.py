"""Pruebas para el modelo de dominio "Empresa" (investmentops.data_layer).

Cubre la tarea "Definir la estructura del modelo de dominio 'Empresa'
(ticker, nombre, sector, mercado)" (TASKS.md, Fase 1, "Contratos e
interfaces"). No prueba ninguna transformación desde datos crudos de un
proveedor: eso corresponde a una tarea posterior (ver TASKS.md,
"Normalización y almacenamiento").
"""

import pytest

from investmentops.data_layer import Company


def test_company_holds_basic_identity_fields() -> None:
    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Tecnología",
        market="NASDAQ",
    )

    assert company.ticker == "AAPL"
    assert company.name == "Apple Inc."
    assert company.sector == "Tecnología"
    assert company.market == "NASDAQ"


def test_company_is_immutable() -> None:
    company = Company(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Tecnología",
        market="NASDAQ",
    )

    with pytest.raises(AttributeError):
        company.ticker = "MSFT"  # type: ignore[misc]


def test_company_supports_local_market_tickers() -> None:
    """Confirma que el modelo no impone un formato fijo de ticker/mercado.

    Relevante para GOALS.md (empresas operadas vía Tyba/Trii, que pueden
    incluir tickers del mercado colombiano, ej. Bolsa de Valores de
    Colombia).
    """
    company = Company(
        ticker="ECOPETROL.CL",
        name="Ecopetrol S.A.",
        sector="Energía",
        market="BVC",
    )

    assert company.ticker == "ECOPETROL.CL"
    assert company.market == "BVC"
