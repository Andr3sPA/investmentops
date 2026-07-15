"""Cálculo determinístico de métricas de salud financiera.

Cubre la tarea "Implementar el cálculo determinístico de ratios de
liquidez, endeudamiento y rentabilidad a partir del modelo normalizado
(entrada del agente, no su resultado final)" (TASKS.md, Fase 1, "Agente
de análisis: salud financiera").

Este módulo implementa exactamente las métricas ya decididas en
`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md` (tarea
anterior de la misma sección):

- **Rentabilidad:** ``net_margin = net_income / revenue``.
- **Endeudamiento:** ``debt_to_revenue = debt / revenue``.
- **Liquidez:** fuera de alcance (limitación documentada en
  `FINANCIAL_HEALTH_METRICS.md`; `FinancialStatement` no expone
  `current_assets`/`current_liabilities`). Este módulo no calcula ni
  aproxima ningún ratio de liquidez.

Conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un
accesorio" / "El cálculo determinístico de métricas... es una entrada
para el agente, no un sustituto de su interpretación"), este cálculo es
puro Python, sin invocar ningún proveedor de IA: el resultado de este
módulo es la entrada (`metrics`) que más adelante recibirá el agente de
salud financiera (ver `investmentops.analysis_engines.contracts.AnalysisEngine.analyze`),
no su resultado final interpretado.

## Manejo de `revenue == 0`

Ambos ratios definidos aquí (`net_margin`, `debt_to_revenue`) tienen
`revenue` como denominador. Si `revenue == 0`, calcularlos produciría una
división por cero. Siguiendo el mismo criterio ya aplicado en el resto
del proyecto (ver `investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`,
"Limitación conocida", y `investmentops/data_layer/cache.py`, manejo de
datos corruptos vs. ausentes), este caso **no** se trata como un error
inesperado ni se aproxima con un valor inventado: `calculate_financial_health_metrics`
devuelve ambos ratios como ``None`` y agrega una advertencia explícita en
`FinancialHealthMetrics.warnings`, dejando que sea el resultado del
agente (`AnalysisResult.limitations`, tarea posterior) quien la
propague de forma legible, en vez de lanzar una excepción no controlada
(`ZeroDivisionError`) o devolver ``float("inf")`` como si fuera un dato
válido.

Fuera de alcance de este módulo:
- El prompt del agente de salud financiera y la invocación al proveedor
  de IA (tareas separadas y posteriores en la misma sección de
  TASKS.md).
- El parseo de la respuesta del modelo de lenguaje al `AnalysisResult`
  final del agente (tarea posterior).
- Cualquier ratio de liquidez: ver `FINANCIAL_HEALTH_METRICS.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from investmentops.data_layer.financial_statements import FinancialStatement


@dataclass(frozen=True)
class FinancialHealthMetrics:
    """Ratios de salud financiera calculados de forma determinística.

    Es el tipo de salida de `calculate_financial_health_metrics`, pensado
    para alimentar el campo `metrics` que recibirá el futuro agente de
    salud financiera (ver
    `investmentops.analysis_engines.contracts.AnalysisEngine.analyze`) y,
    eventualmente, `AnalysisResult.supporting_metrics` una vez ese agente
    esté implementado.

    Attributes
    ----------
    net_margin:
        Margen neto (`net_income / revenue`), o ``None`` si no se pudo
        calcular (ver "Manejo de `revenue == 0`" en el docstring del
        módulo).
    debt_to_revenue:
        Deuda sobre ingresos (`debt / revenue`), o ``None`` si no se pudo
        calcular, por la misma razón que `net_margin`.
    warnings:
        Advertencias explícitas sobre métricas que no se pudieron
        calcular (ej. por `revenue == 0`). Vacío si ambos ratios se
        calcularon sin problema. No incluye la limitación de liquidez
        (esa es una ausencia estructural del modelo, no un caso
        degenerado de los datos, y ya está documentada aparte en
        `FINANCIAL_HEALTH_METRICS.md`).
    """

    net_margin: float | None
    debt_to_revenue: float | None
    warnings: Sequence[str]


def calculate_financial_health_metrics(
    statement: FinancialStatement,
) -> FinancialHealthMetrics:
    """Calcula `net_margin` y `debt_to_revenue` a partir de un `FinancialStatement`.

    Cálculo puramente determinístico (sin IA), conforme a
    `FINANCIAL_HEALTH_METRICS.md`:

    - ``net_margin = statement.net_income / statement.revenue``
    - ``debt_to_revenue = statement.debt / statement.revenue``

    Parameters
    ----------
    statement:
        El `FinancialStatement` ya normalizado (ver
        investmentops.data_layer) del que se derivan estos ratios.

    Returns
    -------
    FinancialHealthMetrics
        Los ratios calculados. Si ``statement.revenue == 0``, ambos
        campos de ratio son ``None`` y `warnings` contiene una
        advertencia explícita, en vez de lanzar una excepción o inventar
        un valor.
    """
    if statement.revenue == 0:
        return FinancialHealthMetrics(
            net_margin=None,
            debt_to_revenue=None,
            warnings=(
                "No se pudieron calcular 'net_margin' ni 'debt_to_revenue': "
                "los ingresos (revenue) son 0, lo que produciría una "
                "división por cero.",
            ),
        )

    net_margin = statement.net_income / statement.revenue
    debt_to_revenue = statement.debt / statement.revenue

    return FinancialHealthMetrics(
        net_margin=net_margin,
        debt_to_revenue=debt_to_revenue,
        warnings=(),
    )
