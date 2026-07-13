"""Pruebas para el modelo de dominio "Estados financieros normalizados"
(investmentops.data_layer.FinancialStatement).

Cubre la tarea "Definir la estructura del modelo de dominio 'Estados
financieros normalizados' (ingresos, beneficios, deuda, con fuente y
fecha)" (TASKS.md, Fase 1, "Contratos e interfaces"). No prueba ninguna
transformación desde datos crudos de un proveedor, ni series históricas
(varios periodos): eso corresponde a tareas posteriores (ver TASKS.md,
"Normalización y almacenamiento" y Fase 3).
"""

from datetime import date

import pytest

from investmentops.data_layer import FinancialStatement


def test_financial_statement_holds_basic_figures_with_source_and_date() -> None:
    statement = FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="example_provider",
        period_end=date(2025, 12, 31),
    )

    assert statement.revenue == 1_000_000.0
    assert statement.net_income == 150_000.0
    assert statement.debt == 400_000.0
    assert statement.source == "example_provider"
    assert statement.period_end == date(2025, 12, 31)


def test_financial_statement_is_immutable() -> None:
    statement = FinancialStatement(
        revenue=1_000_000.0,
        net_income=150_000.0,
        debt=400_000.0,
        source="example_provider",
        period_end=date(2025, 12, 31),
    )

    with pytest.raises(AttributeError):
        statement.revenue = 2_000_000.0  # type: ignore[misc]


def test_financial_statement_supports_negative_net_income() -> None:
    """Una empresa con pérdidas debe poder representarse sin casos especiales."""
    statement = FinancialStatement(
        revenue=500_000.0,
        net_income=-50_000.0,
        debt=300_000.0,
        source="example_provider",
        period_end=date(2025, 6, 30),
    )

    assert statement.net_income == -50_000.0
