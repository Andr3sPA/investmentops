"""Motor de análisis: posicionamiento relativo — cálculo de las métricas
clave lado a lado (empresa investigada vs. cada empresa par), y ensamblado
del resultado estructurado del motor.

Cubre dos tareas de TASKS.md, Fase 5, "Motor de análisis: posicionamiento
relativo":

- "Implementar el cálculo de la posición relativa de la empresa frente a
  sus pares en cada métrica." (`calculate_entity_metrics`, `compare_metric`,
  `calculate_relative_positioning`, ya completada, ver PROGRESS.md).
- "Ensamblar el resultado estructurado del motor (hallazgos, tabla
  comparativa, advertencias si faltan datos de algún par)."
  (`assemble_comparables_analysis`, `ComparablesAnalysisResult`, esta
  tarea).

Sobre las métricas ya decididas en
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
  para esa métrica — nunca se inventa una posición cuando falta un dato.

`calculate_relative_positioning` encadena `calculate_entity_metrics` para
la empresa investigada y para cada `PeerComparable` de un `Comparables`
ya normalizado (ver `investmentops.data_layer.comparables`), y construye,
para cada una de las cuatro métricas, una comparación contra cada par
(`MetricComparison`), en el mismo orden en que los pares ya vienen en
`Comparables.peers` (sin reordenar).

Ambas funciones son puramente determinísticas (sin IA), conforme al mismo
principio ya aplicado por los motores de salud financiera/valoración.

## Ensamblado del resultado estructurado del motor (`assemble_comparables_analysis`, esta tarea)

Cubre la tarea "Ensamblar el resultado estructurado del motor (hallazgos,
tabla comparativa, advertencias si faltan datos de algún par)" (TASKS.md,
Fase 5). Dado un `RelativePositioning` ya calculado (por
`calculate_relative_positioning`), esta función produce un
`ComparablesAnalysisResult`:

- **`findings`**: un hallazgo por métrica (`METRIC_NAMES`), generado por
  plantilla determinista (no vía IA, mismo criterio ya aplicado por
  `_describe_trend` en `investmentops.analysis_engines.trends` y por
  `_describe_relevant_news_count` en
  `investmentops.analysis_engines.news_relevance`), indicando cuántos
  pares quedan por encima/por debajo/igual, y cuántos no se pudieron
  comparar por falta de datos (`MetricComparison.position is None`). Si
  la empresa no tiene pares (`RelativePositioning.peers == []`), se
  produce un único hallazgo explícito señalando esa ausencia, en vez de
  un hallazgo vacío o por métrica sin contenido.
- **`supporting_metrics`**: las cuatro métricas ya calculadas de la
  empresa investigada (`"company"`) y la tabla comparativa completa
  (`"comparisons"`), un mapeo por métrica con una entrada
  `{peer_ticker, company_value, peer_value, position}` por cada par, en
  el mismo orden que `RelativePositioning.peers` — mismo criterio de
  serialización explícita ya usado por `revenue_growth_by_period` en
  `assemble_trend_analysis` y por `relevant_news` en
  `assemble_news_relevance_analysis`.
- **`limitations`**: siempre incluye `GROWTH_LIMITATION` (la limitación
  explícita de "crecimiento" ya documentada en `COMPARABLES_METRICS.md`:
  el modelo de dominio de comparables no expone series históricas por
  par), más `NO_PEERS_LIMITATION` si la empresa no tiene pares, más
  cualquier advertencia de `calculate_entity_metrics` — tanto de la
  empresa investigada como de cada par (identificando el ticker del par
  afectado en el propio texto de la advertencia, para que sea trazable a
  qué comparación concreta corresponde).

### Por qué no se usa `AnalysisResult`/`AnalysisProvenance`

Mismo criterio ya aplicado por `TrendAnalysisResult`
(`investmentops.analysis_engines.trends`) y `NewsRelevanceResult`
(`investmentops.analysis_engines.news_relevance`): este motor no invoca
ningún proveedor de IA en las tareas ya definidas para él en `TASKS.md`
— sus hallazgos se generan por plantilla determinista a partir de
comparaciones ya calculadas, no por interpretación de un modelo de
lenguaje. Forzar el contrato `AnalysisResult` (que exige una
`AnalysisProvenance` real) implicaría fabricar una procedencia de IA
inexistente. `ComparablesAnalysisResult` define, en su lugar,
exactamente los campos que pide la tarea (`findings`,
`supporting_metrics`, `limitations`) más un `analysis_id` para
identificar este motor, sin `provenance`. Cómo este resultado se
incorpora al `ResearchResult` común es una decisión que corresponde a
una futura tarea de "Orquestador y CLI" (TASKS.md, Fase 5), no a esta.

Fuera de alcance de este módulo:
- Registrar este motor en el orquestador o incorporar su resultado al
  `ResearchResult`: tareas separadas y posteriores de "Orquestador y
  CLI".
- La presentación de este resultado en los reportes Markdown/HTML: tareas
  separadas y posteriores de la misma fase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from investmentops.analysis_engines.financial_health import (
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.valuation import calculate_valuation_metrics
from investmentops.data_layer.comparables import Comparables
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Identificador de este motor de análisis, usado como
#: `ComparablesAnalysisResult.analysis_id`. No se usa para localizar un
#: archivo de prompt (este motor no invoca ningún proveedor de IA, ver
#: "Por qué no se usa AnalysisResult/AnalysisProvenance" en el docstring
#: del módulo).
AGENT_ID = "comparables"

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

#: Etiquetas legibles en español de cada métrica, usadas por
#: `_describe_metric_positioning` para construir los hallazgos.
_METRIC_LABELS: Mapping[str, str] = {
    "net_margin": "margen neto",
    "debt_to_revenue": "deuda sobre ingresos",
    "price_to_earnings": "P/E",
    "price_to_sales": "P/S",
}

#: Limitación explícita de "crecimiento", conforme a
#: `COMPARABLES_METRICS.md`: el modelo de dominio de comparables no
#: expone series históricas por empresa par, por lo que este motor nunca
#: calcula ni aproxima una comparación de crecimiento. Se declara siempre
#: en `ComparablesAnalysisResult.limitations`, en vez de omitir el tema
#: en silencio.
GROWTH_LIMITATION = (
    "No se compara el crecimiento (variación periodo a periodo) frente a "
    "los pares: el modelo de dominio de comparables no expone series "
    "históricas por empresa par."
)

#: Advertencia usada cuando la empresa investigada no tiene ninguna
#: empresa par según el proveedor de comparables
#: (`Comparables.peers == []`, caso válido, ver
#: `investmentops.data_layer.comparables.Comparables`).
NO_PEERS_LIMITATION = (
    "No se encontraron empresas pares (comparables) para esta empresa "
    "según el proveedor de datos; no es posible calcular su "
    "posicionamiento relativo."
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


@dataclass(frozen=True)
class ComparablesAnalysisResult:
    """Resultado estructurado del motor de análisis de posicionamiento
    relativo (ver "Ensamblado del resultado estructurado del motor" en el
    docstring del módulo).

    A diferencia de `investmentops.analysis_engines.contracts.AnalysisResult`
    (usado por los motores de salud financiera y valoración, Fase 1), este
    tipo no lleva `provenance`: este motor no invoca ningún proveedor de
    IA (ver "Por qué no se usa AnalysisResult/AnalysisProvenance" en el
    docstring del módulo). Mismo patrón ya usado por
    `investmentops.analysis_engines.trends.TrendAnalysisResult` y
    `investmentops.analysis_engines.news_relevance.NewsRelevanceResult`.

    Attributes
    ----------
    analysis_id:
        Identificador de este motor de análisis (siempre `AGENT_ID`,
        ``"comparables"``).
    findings:
        Hallazgos en lenguaje natural, generados por plantilla
        determinista (no por un modelo de lenguaje) a partir del
        posicionamiento relativo ya calculado, uno por métrica (o un
        único hallazgo si la empresa no tiene pares).
    supporting_metrics:
        Métricas de soporte: las cuatro métricas de la empresa
        investigada y la tabla comparativa completa por par (ver
        `assemble_comparables_analysis`).
    limitations:
        Advertencias explícitas: la limitación de crecimiento (siempre
        presente), la ausencia de pares (si aplica), y cualquier
        advertencia de métrica no calculable, tanto de la empresa
        investigada como de cada par.
    """

    analysis_id: str
    findings: Sequence[str]
    supporting_metrics: Mapping[str, Any]
    limitations: Sequence[str]


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


def _describe_metric_positioning(
    metric_name: str, comparisons: Sequence[MetricComparison]
) -> str:
    """Genera un hallazgo en lenguaje natural para una métrica concreta.

    Plantilla determinista, no generada por un modelo de lenguaje (ver
    "Ensamblado del resultado estructurado del motor" en el docstring del
    módulo). Cuenta cuántos pares quedan por encima/por debajo/igual, y
    cuántas comparaciones no fueron posibles por falta de datos
    (`position is None`).
    """
    label = _METRIC_LABELS[metric_name]
    total = len(comparisons)
    above = sum(1 for c in comparisons if c.position == "por_encima")
    below = sum(1 for c in comparisons if c.position == "por_debajo")
    equal = sum(1 for c in comparisons if c.position == "igual")
    missing = total - above - below - equal

    text = (
        f"En {label}, la empresa está por encima de {above}, por debajo de "
        f"{below}, e igual a {equal} de {total} par(es) comparable(s)."
    )
    if missing:
        text += (
            f" No se pudo comparar con {missing} par(es) por falta de datos."
        )
    return text


def assemble_comparables_analysis(
    positioning: RelativePositioning,
) -> ComparablesAnalysisResult:
    """Ensambla el resultado estructurado del motor de posicionamiento
    relativo a partir de un `RelativePositioning` ya calculado.

    Encadena la lectura de `positioning` (ya producido por
    `calculate_relative_positioning`) y produce un
    `ComparablesAnalysisResult` (ver "Ensamblado del resultado
    estructurado del motor" en el docstring del módulo).

    Parameters
    ----------
    positioning:
        El `RelativePositioning` ya calculado por
        `calculate_relative_positioning` para una empresa y su conjunto
        de comparables.

    Returns
    -------
    ComparablesAnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"comparables"``).
        - `findings`: un hallazgo por métrica (`METRIC_NAMES`), o un
          único hallazgo explícito si la empresa no tiene pares.
        - `supporting_metrics`: `{"company": {...}, "comparisons": {...}}`,
          con las cuatro métricas de la empresa investigada y la tabla
          comparativa completa por par y por métrica.
        - `limitations`: siempre incluye `GROWTH_LIMITATION`;
          `NO_PEERS_LIMITATION` si `positioning.peers` está vacío; más
          cualquier advertencia de `calculate_entity_metrics` (empresa
          investigada y cada par, identificando el ticker del par
          afectado).
    """
    total_peers = len(positioning.peers)

    if total_peers == 0:
        return ComparablesAnalysisResult(
            analysis_id=AGENT_ID,
            findings=[
                "No hay empresas pares disponibles para calcular el "
                "posicionamiento relativo."
            ],
            supporting_metrics={
                "company": {
                    "ticker": positioning.company.ticker,
                    **{
                        name: getattr(positioning.company, name)
                        for name in METRIC_NAMES
                    },
                },
                "comparisons": {name: [] for name in METRIC_NAMES},
            },
            limitations=[GROWTH_LIMITATION, NO_PEERS_LIMITATION, *positioning.company.warnings],
        )

    findings = [
        _describe_metric_positioning(name, positioning.comparisons[name])
        for name in METRIC_NAMES
    ]

    supporting_metrics: dict[str, Any] = {
        "company": {
            "ticker": positioning.company.ticker,
            **{name: getattr(positioning.company, name) for name in METRIC_NAMES},
        },
        "comparisons": {
            name: [
                {
                    "peer_ticker": comparison.peer_ticker,
                    "company_value": comparison.company_value,
                    "peer_value": comparison.peer_value,
                    "position": comparison.position,
                }
                for comparison in positioning.comparisons[name]
            ]
            for name in METRIC_NAMES
        },
    }

    limitations: list[str] = [GROWTH_LIMITATION]
    limitations.extend(positioning.company.warnings)
    for peer in positioning.peers:
        for warning in peer.warnings:
            limitations.append(f"{peer.ticker}: {warning}")

    return ComparablesAnalysisResult(
        analysis_id=AGENT_ID,
        findings=findings,
        supporting_metrics=supporting_metrics,
        limitations=limitations,
    )