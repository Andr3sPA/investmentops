"""Motor de análisis: posicionamiento relativo — cálculo de las métricas
clave lado a lado (empresa investigada vs. cada empresa par).

Cubre la tarea "Implementar el cálculo de la posición relativa de la
empresa frente a sus pares en cada métrica" (TASKS.md, Fase 5, "Motor de
análisis: posicionamiento relativo"), sobre las métricas ya decididas en
`investmentops/analysis_engines/COMPARABLES_METRICS.md`: `net_margin`,
`debt_to_revenue` (vía `calculate_financial_health_metrics`, Fase 1) y
`price_to_earnings`, `price_to_sales` (vía `calculate_valuation_metrics`,
Fase 1), aplicadas tanto a la empresa investigada como a cada
`PeerComparable`.

Este módulo no define ningún cálculo de métrica nuevo: reutiliza, sin
duplicarlas, las dos funciones ya implementadas en Fase 1
(`investmentops.analysis_engines.financial_health.calculate_financial_health_metrics`,
`investmentops.analysis_engines.valuation.calculate_valuation_metrics`),
tal como decide `COMPARABLES_METRICS.md` ("comparar significa aplicar el
mismo cálculo ya existente a cada empresa... no definir una fórmula
nueva"). Por eso hereda, sin redefinirlo, el mismo manejo de casos
degenerados ya decidido en esas tareas (periodo base en cero, beneficio
neto no positivo → métrica `None` con advertencia explícita, nunca
`ZeroDivisionError` ni un valor inventado).

## Cálculo por entidad (`calculate_entity_metrics`)

Dado un ticker (de la empresa investigada o de un par) junto con su
`FinancialStatement`/`MarketData` ya normalizados, calcula las cuatro
métricas y agrega, en una única lista, las advertencias que puedan haber
producido ambos cálculos (ej. `revenue == 0` para salud financiera,
`net_income <= 0` para valoración).

## Comparación posicional (`compare_metric` / `calculate_relative_positioning`)

Para cada métrica y cada par, `compare_metric` compara el valor de la
empresa investigada contra el del par:

- `"por_encima"` si el valor de la empresa es mayor que el del par.
- `"por_debajo"` si es menor.
- `"igual"` si son exactamente iguales.
- `None` si alguno de los dos valores (empresa o par) no fue calculable
  para esa métrica — nunca se inventa una posición cuando falta un dato,
  mismo principio ya aplicado en todo el proyecto.

`calculate_relative_positioning` encadena `calculate_entity_metrics` para
la empresa investigada y para cada `PeerComparable` de un `Comparables`
ya normalizado (ver `investmentops.data_layer.comparables`), y construye,
para cada una de las cuatro métricas, una comparación contra cada par
(`MetricComparison`), en el mismo orden en que los pares ya vienen en
`Comparables.peers` (sin reordenar, mismo criterio ya aplicado por
`Comparables` desde su propia definición).

Esta función es puramente determinística (sin IA), conforme al mismo
principio ya aplicado por los motores de salud financiera/valoración
("La IA es un mecanismo central, no un accesorio... El cálculo
determinístico de métricas es una entrada, no un sustituto de la
interpretación").

Fuera de alcance de este módulo:
- El ensamblado del resultado estructurado del motor (hallazgos, tabla
  comparativa, advertencias si faltan datos de algún par, incluyendo la
  limitación explícita de "crecimiento" ya documentada en
  `COMPARABLES_METRICS.md`): tarea separada y siguiente en la misma
  sección de `TASKS.md`.
- Cualquier interpretación en lenguaje natural de estas comparaciones: no
  hay hoy una tarea que defina un prompt para este motor (mismo criterio
  ya aplicado por los motores de tendencia y noticias relevantes, que no
  invocan IA).
- Registrar este motor en el orquestador o incorporar su resultado al
  `ResearchResult`: tareas separadas y posteriores de "Orquestador y
  CLI".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from investmentops.analysis_engines.financial_health import (
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.valuation import calculate_valuation_metrics
from investmentops.data_layer.comparables import Comparables
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Nombres de las cuatro métricas ya decididas en `COMPARABLES_METRICS.md`,
#: en el orden en que se calculan y se comparan. Usado tanto para
#: recorrer `EntityMetrics` de forma genérica como para tipar las claves
#: de `RelativePositioning.comparisons`.
METRIC_NAMES: tuple[str, ...] = (
    "net_margin",
    "debt_to_revenue",
    "price_to_earnings",
    "price_to_sales",
)


@dataclass(frozen=True)
class EntityMetrics:
    """Las cuatro métricas clave ya calculadas para una empresa (investigada o par).

    Attributes
    ----------
    ticker:
        Identificador de la empresa a la que corresponden estas métricas
        (la empresa investigada, o el ticker de un par concreto).
    net_margin:
        Margen neto (ver
        `investmentops.analysis_engines.financial_health.FinancialHealthMetrics.net_margin`),
        o ``None`` si no fue calculable.
    debt_to_revenue:
        Deuda sobre ingresos (ver
        `investmentops.analysis_engines.financial_health.FinancialHealthMetrics.debt_to_revenue`),
        o ``None`` si no fue calculable.
    price_to_earnings:
        Múltiplo P/E (ver
        `investmentops.analysis_engines.valuation.ValuationMetrics.price_to_earnings`),
        o ``None`` si no fue calculable.
    price_to_sales:
        Múltiplo P/S (ver
        `investmentops.analysis_engines.valuation.ValuationMetrics.price_to_sales`),
        o ``None`` si no fue calculable.
    warnings:
        Advertencias agregadas de ambos cálculos (salud financiera y
        valoración), en ese orden. Vacío si las cuatro métricas se
        calcularon sin problema.
    """

    ticker: str
    net_margin: float | None
    debt_to_revenue: float | None
    price_to_earnings: float | None
    price_to_sales: float | None
    warnings: Sequence[str]


@dataclass(frozen=True)
class MetricComparison:
    """Comparación de una métrica entre la empresa investigada y un par.

    Attributes
    ----------
    peer_ticker:
        Identificador de la empresa par contra la que se comparó.
    company_value:
        Valor de la métrica para la empresa investigada, o ``None`` si no
        fue calculable.
    peer_value:
        Valor de la misma métrica para el par, o ``None`` si no fue
        calculable.
    position:
        ``"por_encima"``/``"por_debajo"``/``"igual"`` según la
        comparación de `company_value` contra `peer_value`, o ``None`` si
        alguno de los dos es ``None`` (ver `compare_metric`).
    """

    peer_ticker: str
    company_value: float | None
    peer_value: float | None
    position: str | None


@dataclass(frozen=True)
class RelativePositioning:
    """Resultado del cálculo de posicionamiento relativo de una empresa.

    Attributes
    ----------
    company:
        Las `EntityMetrics` de la empresa investigada.
    peers:
        Las `EntityMetrics` de cada empresa par, en el mismo orden que
        `Comparables.peers`.
    comparisons:
        Mapeo de nombre de métrica (ver `METRIC_NAMES`) a la lista de
        `MetricComparison` de esa métrica contra cada par, en el mismo
        orden que `peers`.
    """

    company: EntityMetrics
    peers: Sequence[EntityMetrics]
    comparisons: Mapping[str, Sequence[MetricComparison]]


def calculate_entity_metrics(
    ticker: str,
    financial_statement: FinancialStatement,
    market_data: MarketData,
) -> EntityMetrics:
    """Calcula las cuatro métricas clave para una empresa (investigada o par).

    Reutiliza, sin duplicarlas, `calculate_financial_health_metrics`
    (`net_margin`, `debt_to_revenue`) y `calculate_valuation_metrics`
    (`price_to_earnings`, `price_to_sales`), ambas ya implementadas en
    Fase 1.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a la que corresponden `financial_statement`/
        `market_data`.
    financial_statement:
        Estados financieros normalizados de la empresa.
    market_data:
        Datos de mercado normalizados de la misma empresa.

    Returns
    -------
    EntityMetrics
        Las cuatro métricas ya calculadas, con las advertencias de ambos
        cálculos agregadas en una única lista.
    """
    health_metrics = calculate_financial_health_metrics(financial_statement)
    valuation_metrics = calculate_valuation_metrics(market_data, financial_statement)

    warnings = [*health_metrics.warnings, *valuation_metrics.warnings]

    return EntityMetrics(
        ticker=ticker,
        net_margin=health_metrics.net_margin,
        debt_to_revenue=health_metrics.debt_to_revenue,
        price_to_earnings=valuation_metrics.price_to_earnings,
        price_to_sales=valuation_metrics.price_to_sales,
        warnings=warnings,
    )


def compare_metric(
    company_value: float | None, peer_value: float | None
) -> str | None:
    """Compara el valor de una métrica de la empresa investigada contra un par.

    Parameters
    ----------
    company_value:
        Valor de la métrica para la empresa investigada, o ``None`` si no
        fue calculable.
    peer_value:
        Valor de la misma métrica para el par, o ``None`` si no fue
        calculable.

    Returns
    -------
    str | None
        ``"por_encima"`` si ``company_value > peer_value``,
        ``"por_debajo"`` si ``company_value < peer_value``, ``"igual"``
        si son exactamente iguales. ``None`` si `company_value` o
        `peer_value` es ``None`` — nunca se inventa una posición cuando
        falta uno de los dos datos.
    """
    if company_value is None or peer_value is None:
        return None
    if company_value > peer_value:
        return "por_encima"
    if company_value < peer_value:
        return "por_debajo"
    return "igual"


def calculate_relative_positioning(
    company_ticker: str,
    company_financial_statement: FinancialStatement,
    company_market_data: MarketData,
    comparables: Comparables,
) -> RelativePositioning:
    """Calcula la posición relativa de una empresa frente a sus pares.

    Calcula las cuatro métricas clave (ver `METRIC_NAMES`) para la
    empresa investigada y para cada `PeerComparable` de `comparables`
    (vía `calculate_entity_metrics`), y compara cada métrica de la
    empresa investigada contra cada par (vía `compare_metric`), sin
    reordenar los pares.

    Parameters
    ----------
    company_ticker:
        Identificador de la empresa investigada.
    company_financial_statement:
        Estados financieros normalizados de la empresa investigada.
    company_market_data:
        Datos de mercado normalizados de la misma empresa.
    comparables:
        El `Comparables` ya normalizado (ver
        `investmentops.data_layer.comparables`) con las cifras ya
        normalizadas de cada empresa par.

    Returns
    -------
    RelativePositioning
        Las métricas de la empresa investigada, las de cada par (mismo
        orden que `comparables.peers`), y las comparaciones por métrica.
        Si `comparables.peers` está vacío, `peers` y cada lista de
        `comparisons` quedan vacías, sin lanzar ninguna excepción (una
        empresa sin pares es un caso válido, ver
        `investmentops.data_layer.comparables.Comparables`).
    """
    company_metrics = calculate_entity_metrics(
        company_ticker, company_financial_statement, company_market_data
    )
    peer_metrics = [
        calculate_entity_metrics(peer.ticker, peer.financial_statement, peer.market_data)
        for peer in comparables.peers
    ]

    comparisons: dict[str, list[MetricComparison]] = {name: [] for name in METRIC_NAMES}
    for peer in peer_metrics:
        for name in METRIC_NAMES:
            company_value = getattr(company_metrics, name)
            peer_value = getattr(peer, name)
            comparisons[name].append(
                MetricComparison(
                    peer_ticker=peer.ticker,
                    company_value=company_value,
                    peer_value=peer_value,
                    position=compare_metric(company_value, peer_value),
                )
            )

    return RelativePositioning(
        company=company_metrics,
        peers=peer_metrics,
        comparisons=comparisons,
    )