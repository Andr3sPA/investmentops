"""Agente de análisis: valoración — cálculo determinístico de múltiplos e
invocación al proveedor de IA configurado.

Cubre, en un mismo módulo, dos tareas relacionadas de TASKS.md, Fase 1,
"Agente de análisis: valoración":

- "Implementar el cálculo determinístico de esos múltiplos a partir del
  modelo normalizado." (`calculate_valuation_metrics`).
- "Implementar la invocación al proveedor de IA configurado con esos
  múltiplos + el prompt." (`invoke_valuation_agent`).

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
para el agente, no un sustituto de su interpretación"), el cálculo de
`calculate_valuation_metrics` es puro Python, sin invocar ningún
proveedor de IA.

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

## Invocación al proveedor de IA

`invoke_valuation_agent` sigue exactamente el mismo patrón ya usado en
`investmentops.analysis_engines.financial_health.invoke_financial_health_agent`:

1. Carga el prompt del agente desde `prompts/valuation.md` (ver
   `investmentops.analysis_engines.prompts.load_prompt` y
   `prompts/README.md`, "Prompts como artefactos, no como código").
2. Resuelve qué proveedor/modelo le corresponde al agente
   ``"valuation"`` según `config.local.toml` (ver
   `investmentops.ai_providers.selection.resolve_agent_provider` y
   CONFIGURATION.md, sección `[agents]`).
3. Construye la instancia concreta de `AIProvider` correspondiente (ver
   `investmentops.ai_providers.factory.build_ai_provider`; hoy solo
   `AnthropicAIProvider` está implementada).
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   el `MarketData` y el `FinancialStatement` normalizados, más las
   `ValuationMetrics` ya calculadas (nunca al revés: la IA nunca calcula
   ni recalcula estos múltiplos, solo los interpreta, conforme a
   `ARCHITECTURE.md`).

Esta función devuelve el `AIProviderResponse` crudo (texto de respuesta +
metadatos de procedencia). No interpreta ni parsea ese texto por sí
misma: el parseo a `AnalysisResult` es una tarea separada y posterior
(ver TASKS.md, "Agente de análisis: valoración" > "Implementar el parseo
de la respuesta del modelo al resultado estructurado del agente de
valoración"), análoga a
`financial_health.parse_financial_health_response`.

Fuera de alcance de este módulo:
- P/B y EV/EBITDA: limitaciones ya documentadas en
  `VALUATION_METRICS.md`; se declararán en `AnalysisResult.limitations`
  en la tarea de parseo, no en este módulo.
- El contenido del prompt en sí (vive en `prompts/valuation.md`, fuera
  del código Python, ver `prompts/README.md`).
- El parseo de la respuesta del modelo a `AnalysisResult`: tarea
  separada y posterior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from investmentops.ai_providers import (
    AIProviderResponse,
    build_ai_provider,
    resolve_agent_provider,
)
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/valuation.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como futuro
#: `AnalysisResult.analysis_id` (tarea de parseo, aún pendiente).
AGENT_ID = "valuation"


@dataclass(frozen=True)
class ValuationMetrics:
    """Múltiplos de valoración calculados de forma determinística.

    Es el tipo de salida de `calculate_valuation_metrics`, y el que
    alimenta el campo `metrics` que recibe `invoke_valuation_agent` (mismo
    patrón ya usado por `FinancialHealthMetrics` en
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


def invoke_valuation_agent(
    market_data: MarketData,
    statement: FinancialStatement,
    metrics: ValuationMetrics,
    *,
    config: dict[str, Any] | None = None,
) -> AIProviderResponse:
    """Invoca al proveedor de IA configurado para el agente de valoración.

    Combina el prompt del agente (`prompts/valuation.md`), el
    proveedor/modelo resuelto para ``"valuation"`` según
    `config.local.toml`, y los múltiplos ya calculados de forma
    determinística (`metrics`, nunca recalculados por la IA), para
    obtener una interpretación del modelo de lenguaje.

    Parameters
    ----------
    market_data:
        El `MarketData` normalizado de la empresa, enviado como parte de
        `data` para que el modelo tenga el contexto completo (precio,
        capitalización, fuente y fecha de corte), no solo los múltiplos
        ya derivados.
    statement:
        El `FinancialStatement` normalizado de la misma empresa, enviado
        por la misma razón (ingresos, beneficio neto, deuda, fuente y
        fecha de corte).
    metrics:
        Las `ValuationMetrics` ya calculadas por
        `calculate_valuation_metrics` para `market_data`/`statement`. Se
        envían tal cual, incluyendo `warnings` si algún múltiplo no se
        pudo calcular (ver prompt del agente, que instruye a declarar esa
        ausencia en vez de inventar un valor).
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`). Útil para pruebas, para no
        depender de un `config.local.toml` real en disco. Si no se
        indica, se llama a `load_config()`.

    Returns
    -------
    AIProviderResponse
        La respuesta cruda del proveedor de IA (texto de interpretación +
        metadatos de procedencia: proveedor, modelo, fecha). Este
        resultado **no** se parsea aquí a la estructura final del agente
        (`AnalysisResult`): esa es una tarea separada y posterior (ver
        TASKS.md).

    Raises
    ------
    PromptError
        Si no se puede cargar `prompts/valuation.md` (ver
        `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para el agente
        ``"valuation"`` según la configuración (ver
        `investmentops.ai_providers.selection.resolve_agent_provider`).
    AIProviderError
        Si el proveedor resuelto no tiene una integración concreta
        implementada (ver
        `investmentops.ai_providers.factory.build_ai_provider`), si
        faltan credenciales imprescindibles para construirlo, o si la
        invocación al modelo de lenguaje falla (no responde, error de
        autenticación, límite de tasa, respuesta sin contenido
        interpretable).
    ConfigError
        Si `config` no se indica y no se puede cargar
        `config.local.toml` (ver `investmentops.config.load_config`).
    """
    cfg = config if config is not None else load_config()

    prompt = load_prompt(AGENT_ID)
    selection = resolve_agent_provider(AGENT_ID, cfg)
    provider = build_ai_provider(selection.provider, config=cfg)

    data = {
        "market_data": {
            "price": market_data.price,
            "market_cap": market_data.market_cap,
            "source": market_data.source,
            "as_of": market_data.as_of.isoformat(),
        },
        "financial_statement": {
            "revenue": statement.revenue,
            "net_income": statement.net_income,
            "debt": statement.debt,
            "source": statement.source,
            "period_end": statement.period_end.isoformat(),
        },
        "metrics": {
            "price_to_earnings": metrics.price_to_earnings,
            "price_to_sales": metrics.price_to_sales,
            "warnings": list(metrics.warnings),
        },
    }

    return provider.complete(prompt, data=data)
