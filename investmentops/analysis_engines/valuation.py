"""Agente de análisis: valoración — cálculo determinístico de múltiplos,
invocación al proveedor de IA configurado y parseo de su respuesta.

Cubre, en un mismo módulo, tres tareas relacionadas de TASKS.md, Fase 1,
"Agente de análisis: valoración":

- "Implementar el cálculo determinístico de esos múltiplos a partir del
  modelo normalizado." (`calculate_valuation_metrics`).
- "Implementar la invocación al proveedor de IA configurado con esos
  múltiplos + el prompt." (`invoke_valuation_agent`).
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente de valoración." (`parse_valuation_response`).

Se agrega además `analyze_valuation`, una función de conveniencia que
encadena las tres piezas anteriores, mismo criterio ya aplicado en
`investmentops.analysis_engines.financial_health.analyze_financial_health`
para el agente de salud financiera.

Implementa exactamente los múltiplos ya decididos en
`investmentops/analysis_engines/VALUATION_METRICS.md`:

- **P/E** (`price_to_earnings`) = ``market_cap / net_income``.
- **P/S** (`price_to_sales`) = ``market_cap / revenue``.
- **P/B y EV/EBITDA:** fuera de alcance (limitaciones explícitas
  documentadas en `VALUATION_METRICS.md`; ni `MarketData` ni
  `FinancialStatement` exponen `equity`, `ebitda` o `cash`). Este módulo
  no calcula ni aproxima ninguno de los dos, y `parse_valuation_response`
  declara ambas ausencias explícitamente en
  `AnalysisResult.limitations`, mismo criterio ya usado por
  `LIQUIDITY_LIMITATION` en
  `investmentops.analysis_engines.financial_health`.

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
misma: ese trabajo lo hace `parse_valuation_response`.

## Parseo de la respuesta a `AnalysisResult`

`parse_valuation_response` traduce un `AIProviderResponse` (más las
`ValuationMetrics` ya calculadas, las mismas que se enviaron al
proveedor de IA) a la estructura común `AnalysisResult` definida en
`investmentops.analysis_engines.contracts`, mismo criterio ya aplicado
por `parse_financial_health_response`:

- `analysis_id`: siempre `AGENT_ID` (``"valuation"``).
- `findings`: el texto de interpretación del modelo
  (`response.content`), como un único hallazgo. Igual que
  `prompts/financial_health.md`, `prompts/valuation.md` no le pide al
  modelo un formato estructurado: es texto libre en español, por lo que
  "parsear" aquí significa empaquetar ese texto como hallazgo, no
  extraer campos de una respuesta estructurada.
- `supporting_metrics`: las mismas `ValuationMetrics` ya calculadas de
  forma determinística (`price_to_earnings`, `price_to_sales`) — nunca
  un valor nuevo derivado del texto del modelo, conforme a
  `ARCHITECTURE.md` ("La IA es un mecanismo central, no un accesorio").
- `limitations`: siempre incluye las limitaciones de P/B y EV/EBITDA ya
  documentadas en `VALUATION_METRICS.md` (este agente no calcula ninguno
  de los dos), más cualquier advertencia de `ValuationMetrics.warnings`
  (ej. los casos `net_income <= 0` o `revenue == 0`).
- `provenance`: `AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`, tomado
  directamente de los metadatos que ya entrega el proveedor de IA.

## Función de conveniencia `analyze_valuation`

Encadena `calculate_valuation_metrics` (si no se pasan métricas ya
calculadas) → `invoke_valuation_agent` → `parse_valuation_response`,
mismo criterio ya aplicado por
`investmentops.analysis_engines.financial_health.analyze_financial_health`.
No traduce las excepciones de las funciones que invoca (`PromptError`,
`AgentProviderSelectionError`, `AIProviderError`) a `AnalysisEngineError`:
esa decisión de integración corresponde al "Orquestador mínimo" (ver
TASKS.md), no a esta tarea de parseo.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/valuation.md`, fuera
  del código Python, ver `prompts/README.md`).
- Traducir los errores de este agente a `AnalysisEngineError` para
  cumplir literalmente el protocolo `AnalysisEngine`: tarea separada
  (ver TASKS.md, "Orquestador mínimo").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from investmentops.ai_providers import (
    AIProviderResponse,
    build_ai_provider,
    resolve_agent_provider,
)
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/valuation.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`.
AGENT_ID = "valuation"

#: Limitación explícita de Price/Book (P/B), conforme a
#: `VALUATION_METRICS.md`: el modelo de dominio normalizado no expone
#: patrimonio (`equity`/`book_value`), por lo que este agente nunca
#: calcula ni aproxima P/B. Se declara siempre en
#: `AnalysisResult.limitations`, en vez de omitir el tema en silencio.
PRICE_TO_BOOK_LIMITATION = (
    "No se dispone de datos de patrimonio (equity/book_value) en el "
    "modelo de dominio normalizado actual; este análisis no incluye el "
    "múltiplo Price/Book (P/B)."
)

#: Limitación explícita de EV/EBITDA, conforme a `VALUATION_METRICS.md`:
#: el modelo de dominio normalizado no expone EBITDA ni efectivo (`cash`),
#: por lo que este agente nunca calcula ni aproxima EV/EBITDA. Se declara
#: siempre en `AnalysisResult.limitations`, en vez de omitir el tema en
#: silencio.
EV_EBITDA_LIMITATION = (
    "No se dispone de datos de EBITDA ni de efectivo (cash) en el modelo "
    "de dominio normalizado actual; este análisis no incluye el múltiplo "
    "EV/EBITDA."
)


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
        documentadas aparte en `VALUATION_METRICS.md` y declaradas en
        `parse_valuation_response` vía `PRICE_TO_BOOK_LIMITATION` y
        `EV_EBITDA_LIMITATION`).
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
        (`AnalysisResult`); ver `parse_valuation_response`.

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


def parse_valuation_response(
    response: AIProviderResponse,
    metrics: ValuationMetrics,
) -> AnalysisResult:
    """Traduce la respuesta cruda del proveedor de IA a un `AnalysisResult`.

    Empaqueta el texto de interpretación del modelo (`response.content`)
    como el único hallazgo del agente, adjunta las mismas métricas ya
    calculadas de forma determinística (nunca un valor nuevo derivado del
    texto del modelo) y construye la procedencia a partir de los
    metadatos que ya entrega el proveedor de IA. Mismo patrón ya usado
    por
    `investmentops.analysis_engines.financial_health.parse_financial_health_response`.

    Parameters
    ----------
    response:
        La respuesta cruda devuelta por `invoke_valuation_agent` (texto
        de interpretación + proveedor/modelo/fecha de generación).
    metrics:
        Las mismas `ValuationMetrics` que se enviaron al proveedor de IA
        en `invoke_valuation_agent` (no se recalculan ni se derivan de
        `response`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"valuation"``).
        - `findings`: una lista con un único elemento, el texto de
          `response.content` (sin recortar ni reformatear: el prompt no
          exige un formato estructurado, ver docstring del módulo).
        - `supporting_metrics`: `{"price_to_earnings": ..., "price_to_sales": ...}`,
          tomados directamente de `metrics`.
        - `limitations`: siempre incluye `PRICE_TO_BOOK_LIMITATION` y
          `EV_EBITDA_LIMITATION`, seguidas de cualquier advertencia en
          `metrics.warnings` (ej. los casos `net_income <= 0` o
          `revenue == 0`).
        - `provenance`: `AnalysisProvenance(ai_provider=response.provider,
          ai_model=response.model, generated_at=response.generated_at)`.
    """
    findings = [response.content]
    supporting_metrics = {
        "price_to_earnings": metrics.price_to_earnings,
        "price_to_sales": metrics.price_to_sales,
    }
    limitations = [
        PRICE_TO_BOOK_LIMITATION,
        EV_EBITDA_LIMITATION,
        *metrics.warnings,
    ]
    provenance = AnalysisProvenance(
        ai_provider=response.provider,
        ai_model=response.model,
        generated_at=response.generated_at,
    )

    return AnalysisResult(
        analysis_id=AGENT_ID,
        findings=findings,
        supporting_metrics=supporting_metrics,
        limitations=limitations,
        provenance=provenance,
    )


def analyze_valuation(
    market_data: MarketData,
    statement: FinancialStatement,
    metrics: ValuationMetrics | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Produce el `AnalysisResult` completo de valoración para una empresa.

    Función de conveniencia que encadena, en orden,
    `calculate_valuation_metrics` (solo si `metrics` no se indica),
    `invoke_valuation_agent` y `parse_valuation_response`. No traduce las
    excepciones que puedan levantar esas funciones (ver "Fuera de
    alcance" en el docstring del módulo): quien invoque esta función es
    responsable de capturarlas si necesita continuar el flujo ante un
    fallo parcial (ese manejo es responsabilidad del "Orquestador
    mínimo", ver TASKS.md). Mismo patrón ya usado por
    `investmentops.analysis_engines.financial_health.analyze_financial_health`.

    Parameters
    ----------
    market_data:
        El `MarketData` normalizado de la empresa a analizar.
    statement:
        El `FinancialStatement` normalizado de la misma empresa.
    metrics:
        Métricas ya calculadas, si se quiere evitar recalcularlas (por
        ejemplo, si ya se calcularon antes para otro propósito). Si no
        se indica, se calculan aquí mismo con
        `calculate_valuation_metrics`.
    config:
        Configuración ya cargada, propagada a `invoke_valuation_agent`.

    Returns
    -------
    AnalysisResult
        El resultado estructurado completo del agente de valoración.
    """
    resolved_metrics = (
        metrics
        if metrics is not None
        else calculate_valuation_metrics(market_data, statement)
    )
    response = invoke_valuation_agent(
        market_data, statement, resolved_metrics, config=config
    )
    return parse_valuation_response(response, resolved_metrics)
