"""Agente de análisis: valoración — cálculo determinístico de múltiplos.

Cubre la tarea "Implementar el cálculo determinístico de esos múltiplos a
partir del modelo normalizado" (TASKS.md, Fase 1, "Agente de análisis:
valoración").

Implementa exactamente los múltiplos ya decididos en
`investmentops/analysis_engines/VALUATION_METRICS.md`:

- **P/E** (`price_to_earnings`) = ``market_cap / net_income``.
- **P/S** (`price_to_sales`) = ``market_cap / revenue``.
- **P/B y EV/EBITDA:** fuera de alcance (limitaciones explícitas
  documentadas en `VALUATION_METRICS.md`; ni `MarketData` ni
  `FinancialStatement` exponen `equity`, `ebitda` o `cash`). Este módulo
  no calcula ni aproxima ninguno de los dos.

Conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un
accesorio" / "El cálculo determinístico de métricas... es una entrada
para el agente, no un sustituto de su interpretación"), este cálculo es
puro Python, sin invocar ningún proveedor de IA.

## Manejo de casos degenerados

Mismo criterio ya sentado en
`investmentops.analysis_engines.financial_health.calculate_financial_health_metrics`
para `revenue == 0`, ya anticipado en `VALUATION_METRICS.md`:

- Si ``statement.net_income <= 0``, `price_to_earnings` no es un
  múltiplo interpretable de la forma habitual (sin ganancias que
  "pagar múltiples veces", o un resultado negativo engañoso sin
  contexto). Se devuelve como ``None`` junto con una advertencia
  explícita en `ValuationMetrics.warnings`, en vez de lanzar una
  excepción o devolver un número negativo/cero sin contexto.
- Si ``statement.revenue == 0``, `price_to_sales` produciría una
  división por cero. Se devuelve como ``None`` junto con una advertencia
  explícita, mismo criterio que `debt_to_revenue`/`net_margin` en
  `financial_health.py`.
- Ambos casos pueden coexistir en la misma llamada (ej. una empresa con
  pérdidas e ingresos en cero): en ese caso `warnings` incluye ambas
  advertencias, una por cada métrica no calculable.

Fuera de alcance de este módulo:
- P/B y EV/EBITDA: limitaciones ya documentadas en
  `VALUATION_METRICS.md`; se declararán más adelante en
  `AnalysisResult.limitations`, en la tarea de parseo de la respuesta
  del agente (no en esta tarea de cálculo determinístico).
- El prompt del agente de valoración y la invocación al proveedor de IA
  configurado: tareas separadas y posteriores (ver TASKS.md, "Agente de
  análisis: valoración").
- El parseo de la respuesta del modelo a `AnalysisResult`: tarea
  separada y posterior, análoga a
  `financial_health.parse_financial_health_response`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData


@dataclass(frozen=True)
class ValuationMetrics:
    """Múltiplos de valoración calculados de forma determinística.

    Es el tipo de salida de `calculate_valuation_metrics`, pensado para
    alimentar, en una tarea posterior, el campo `metrics` que recibirá la
    invocación al proveedor de IA del agente de valoración (mismo patrón
    ya usado por `FinancialHealthMetrics` en
    `investmentops.analysis_engines.financial_health`).

    Attributes
    ----------
    price_to_earnings:
        Múltiplo P/E (``market_cap / net_income``), o ``None`` si no se
        pudo calcular porque ``net_income <= 0`` (ver "Manejo de casos
        degenerados" en el docstring del módulo).
    price_to_sales:
        Múltiplo P/S (``market_cap / revenue``), o ``None`` si no se pudo
        calcular porque ``revenue == 0``.
    warnings:
        Advertencias explícitas sobre múltiplos que no se pudieron
        calcular (ej. por `net_income <= 0` o `revenue == 0`). Vacío si
        ambos múltiplos se calcularon sin problema. No incluye las
        limitaciones de P/B ni EV/EBITDA (ausencias estructurales del
        modelo de dominio, no casos degenerados de los datos; ya
        documentadas aparte en `VALUATION_METRICS.md` y a declarar en la
        tarea de parseo del agente).
    """

    price_to_earnings: float | None
    price_to_sales: float | None
    warnings: Sequence[str]


def calculate_valuation_metrics(
    market_data: MarketData,
    statement: FinancialStatement,
) -> ValuationMetrics:
    """Calcula `price_to_earnings` y `price_to_sales` de forma determinística.

    Cálculo puramente determinístico (sin IA), conforme a
    `VALUATION_METRICS.md`:

    - ``price_to_earnings = market_data.market_cap / statement.net_income``
    - ``price_to_sales = market_data.market_cap / statement.revenue``

    Parameters
    ----------
    market_data:
        El `MarketData` ya normalizado (ver investmentops.data_layer) de
        la empresa, del que se toma `market_cap`.
    statement:
        El `FinancialStatement` ya normalizado de la misma empresa, del
        que se toman `net_income` y `revenue`.

    Returns
    -------
    ValuationMetrics
        Los múltiplos calculados. Si ``statement.net_income <= 0``,
        `price_to_earnings` es ``None`` con una advertencia explícita en
        `warnings`. Si ``statement.revenue == 0``, `price_to_sales` es
        ``None`` con su propia advertencia explícita. Ambos casos pueden
        coexistir; nunca se lanza una excepción ni se inventa un valor
        sustituto.
    """
    warnings: list[str] = []

    if statement.net_income <= 0:
        price_to_earnings = None
        warnings.append(
            "No se pudo calcular 'price_to_earnings' (P/E): el beneficio "
            "neto (net_income) es 0 o negativo, por lo que el múltiplo no "
            "es interpretable de la forma habitual."
        )
    else:
        price_to_earnings = market_data.market_cap / statement.net_income

    if statement.revenue == 0:
        price_to_sales = None
        warnings.append(
            "No se pudo calcular 'price_to_sales' (P/S): los ingresos "
            "(revenue) son 0, lo que produciría una división por cero."
        )
    else:
        price_to_sales = market_data.market_cap / statement.revenue

    return ValuationMetrics(
        price_to_earnings=price_to_earnings,
        price_to_sales=price_to_sales,
        warnings=tuple(warnings),
    )
