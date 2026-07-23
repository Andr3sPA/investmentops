"""Agente de estrategia: Value investing — invocación al proveedor de IA
y parseo de su respuesta al resultado estructurado del agente.

Cubre dos tareas de TASKS.md, Fase 6, "Motores de análisis por estrategia":

- "Implementar la invocación al proveedor de IA configurado para el
  agente 'value', enviando los datos normalizados ya existentes (sin
  nuevas fuentes ni cálculos adicionales) junto con el prompt." (ya
  completada, ver PROGRESS.md).
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'value' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no un
  veredicto)." (esta tarea).

Sobre el mapeo de datos ya fijado en
`investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md`: este agente
reutiliza, sin recalcularlas, las métricas ya calculadas de forma
determinística por los motores existentes de Fase 1 —
`ValuationMetrics` (`price_to_earnings`, `price_to_sales`, vía
`calculate_valuation_metrics`) y `FinancialHealthMetrics` (`net_margin`,
`debt_to_revenue`, vía `calculate_financial_health_metrics`) — junto con
`MarketData`/`FinancialStatement` normalizados, como contexto adicional
para el modelo de lenguaje. No introduce ningún cálculo nuevo (ver
`STRATEGY_DATA_MAPPING.md`, "Principio común: ningún cálculo nuevo, solo
reinterpretación").

`invoke_value_agent` sigue exactamente el mismo patrón ya usado por
`investmentops.analysis_engines.financial_health.invoke_financial_health_agent`/
`investmentops.analysis_engines.valuation.invoke_valuation_agent`:

1. Carga el prompt del agente desde `prompts/value.md` (ver
   `investmentops.analysis_engines.prompts.load_prompt` y
   `prompts/README.md`, "Prompts como artefactos, no como código").
2. Resuelve qué proveedor/modelo le corresponde al agente ``"value"``
   según `config.local.toml` (ver
   `investmentops.ai_providers.selection.resolve_agent_provider` y
   CONFIGURATION.md, sección `[agents]`).
3. Construye la instancia concreta de `AIProvider` correspondiente (ver
   `investmentops.ai_providers.factory.build_ai_provider`; hoy solo
   `AnthropicAIProvider` está implementada).
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   el `MarketData`/`FinancialStatement` normalizados y las
   `ValuationMetrics`/`FinancialHealthMetrics` ya calculadas (nunca
   recalculadas por la IA, conforme a `ARCHITECTURE.md`, "La IA es un
   mecanismo central, no un accesorio").

Esta función devuelve el `AIProviderResponse` crudo (texto de respuesta +
metadatos de procedencia). No interpreta ni parsea ese texto por sí
misma: ese trabajo lo hace `parse_value_response` (esta tarea).

## Parseo de la respuesta a `AnalysisResult` (`parse_value_response`, esta tarea)

Traduce un `AIProviderResponse` (más las `ValuationMetrics`/
`FinancialHealthMetrics` ya calculadas, las mismas que se enviaron al
proveedor de IA) a la estructura común `AnalysisResult` definida en
`investmentops.analysis_engines.contracts`, mismo criterio ya aplicado
por `parse_financial_health_response`/`parse_valuation_response`:

- `analysis_id`: siempre `AGENT_ID` (``"value"``).
- `findings`: el texto de interpretación del modelo (`response.content`),
  como un único hallazgo. Igual que `prompts/financial_health.md`/
  `prompts/valuation.md`, `prompts/value.md` no le pide al modelo un
  formato estructurado: es texto libre en español.
- `supporting_metrics`: las mismas `ValuationMetrics`/
  `FinancialHealthMetrics` ya calculadas de forma determinística
  (`price_to_earnings`, `price_to_sales`, `net_margin`,
  `debt_to_revenue`) — nunca un valor nuevo derivado del texto del
  modelo, conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central,
  no un accesorio").
- `limitations`: siempre incluye `FRAMEWORK_LIMITATION` — la limitación
  explícita que exige esta tarea ("dejando explícito que es una lectura
  desde un marco particular, no un veredicto"), declarando que esta
  interpretación corresponde únicamente al marco de value investing, no
  a una evaluación general de la empresa ni a las demás estrategias
  (growth, calidad) — seguida de cualquier advertencia de
  `valuation_metrics.warnings`/`health_metrics.warnings` (ej. los casos
  `net_income <= 0`, `revenue == 0`).
- `provenance`: `AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`, tomado
  directamente de los metadatos que ya entrega el proveedor de IA.

`FRAMEWORK_LIMITATION` se declara siempre (no depende de ningún caso
degenerado de los datos), mismo criterio ya usado por
`LIQUIDITY_LIMITATION` (`financial_health.py`) y
`PRICE_TO_BOOK_LIMITATION`/`EV_EBITDA_LIMITATION` (`valuation.py`): es
una limitación estructural del propio diseño del agente (una lectura
parcial desde un marco concreto), no un caso degenerado de los números
recibidos.

## Función de conveniencia `analyze_value`

Encadena `calculate_valuation_metrics`/`calculate_financial_health_metrics`
(si no se pasan ya calculadas) → `invoke_value_agent` →
`parse_value_response`, mismo criterio ya aplicado por
`analyze_financial_health`/`analyze_valuation`. No traduce las
excepciones de las funciones que invoca (`PromptError`,
`AgentProviderSelectionError`, `AIProviderError`) a
`AnalysisEngineError`: esa decisión de integración corresponde al
"Orquestador" (ver TASKS.md, Fase 6, "Orquestador"), no a esta tarea.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/value.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `ValuationMetrics`/`FinancialHealthMetrics`: ya
  implementado en Fase 1, reutilizado tal cual, sin modificaciones ni
  duplicación.
- Registrar este agente en el orquestador e incorporar su resultado al
  `ResearchResult`: tarea separada y posterior (ver TASKS.md, Fase 6,
  "Orquestador").
"""

from __future__ import annotations

from typing import Any

from investmentops.ai_providers import (
    AIProviderResponse,
    build_ai_provider,
    resolve_agent_provider,
)
from investmentops.analysis_engines.contracts import AnalysisProvenance, AnalysisResult
from investmentops.analysis_engines.financial_health import (
    FinancialHealthMetrics,
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.analysis_engines.valuation import (
    ValuationMetrics,
    calculate_valuation_metrics,
)
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/value.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`.
AGENT_ID = "value"

#: Limitación explícita que declara que esta interpretación corresponde
#: únicamente al marco de value investing: una lectura particular sobre
#: los mismos datos ya calculados, no una evaluación general de la
#: empresa ni un veredicto de inversión (ver "Parseo de la respuesta a
#: AnalysisResult" en el docstring del módulo). Se declara siempre en
#: `AnalysisResult.limitations`, mismo criterio ya usado por
#: `LIQUIDITY_LIMITATION` (`investmentops.analysis_engines.financial_health`)
#: y `PRICE_TO_BOOK_LIMITATION`/`EV_EBITDA_LIMITATION`
#: (`investmentops.analysis_engines.valuation`).
FRAMEWORK_LIMITATION = (
    "Esta interpretación corresponde exclusivamente al marco de value "
    "investing: es una lectura particular de los mismos datos ya "
    "calculados, no una evaluación general de la empresa, ni un "
    "veredicto de inversión, ni equivalente a otras lecturas por "
    "estrategia (ej. growth, calidad)."
)


def invoke_value_agent(
    market_data: MarketData,
    statement: FinancialStatement,
    valuation_metrics: ValuationMetrics,
    health_metrics: FinancialHealthMetrics,
    *,
    config: dict[str, Any] | None = None,
) -> AIProviderResponse:
    """Invoca al proveedor de IA configurado para el agente de estrategia 'value'.

    Combina el prompt del agente (`prompts/value.md`), el
    proveedor/modelo resuelto para ``"value"`` según `config.local.toml`,
    y los datos ya normalizados/calculados en fases anteriores (nunca
    recalculados aquí), para obtener una interpretación del modelo de
    lenguaje desde el marco de value investing.

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
    valuation_metrics:
        Las `ValuationMetrics` ya calculadas por
        `calculate_valuation_metrics` (Fase 1) para
        `market_data`/`statement`. Se envían tal cual, incluyendo
        `warnings` si algún múltiplo no se pudo calcular.
    health_metrics:
        Las `FinancialHealthMetrics` ya calculadas por
        `calculate_financial_health_metrics` (Fase 1) para `statement`.
        Se envían tal cual, como contexto de calidad del negocio detrás
        del precio (ver `prompts/value.md`), incluyendo `warnings` si
        alguna métrica no se pudo calcular.
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
        (ver `parse_value_response`).

    Raises
    ------
    PromptError
        Si no se puede cargar `prompts/value.md` (ver
        `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para el agente
        ``"value"`` según la configuración (ver
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
        "valuation_metrics": {
            "price_to_earnings": valuation_metrics.price_to_earnings,
            "price_to_sales": valuation_metrics.price_to_sales,
            "warnings": list(valuation_metrics.warnings),
        },
        "financial_health_metrics": {
            "net_margin": health_metrics.net_margin,
            "debt_to_revenue": health_metrics.debt_to_revenue,
            "warnings": list(health_metrics.warnings),
        },
    }

    return provider.complete(prompt, data=data)


def parse_value_response(
    response: AIProviderResponse,
    valuation_metrics: ValuationMetrics,
    health_metrics: FinancialHealthMetrics,
) -> AnalysisResult:
    """Traduce la respuesta cruda del proveedor de IA a un `AnalysisResult`.

    Empaqueta el texto de interpretación del modelo (`response.content`)
    como el único hallazgo del agente, adjunta las mismas
    `ValuationMetrics`/`FinancialHealthMetrics` ya calculadas de forma
    determinística (nunca un valor nuevo derivado del texto del modelo),
    declara siempre `FRAMEWORK_LIMITATION` (esta interpretación es una
    lectura desde el marco de value investing, no un veredicto ni una
    evaluación general) y construye la procedencia a partir de los
    metadatos que ya entrega el proveedor de IA. Mismo patrón ya usado
    por
    `investmentops.analysis_engines.financial_health.parse_financial_health_response`/
    `investmentops.analysis_engines.valuation.parse_valuation_response`.

    Parameters
    ----------
    response:
        La respuesta cruda devuelta por `invoke_value_agent` (texto de
        interpretación + proveedor/modelo/fecha de generación).
    valuation_metrics:
        Las mismas `ValuationMetrics` que se enviaron al proveedor de IA
        en `invoke_value_agent` (no se recalculan ni se derivan de
        `response`).
    health_metrics:
        Las mismas `FinancialHealthMetrics` que se enviaron al proveedor
        de IA en `invoke_value_agent` (no se recalculan ni se derivan de
        `response`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"value"``).
        - `findings`: una lista con un único elemento, el texto de
          `response.content` (sin recortar ni reformatear: el prompt no
          exige un formato estructurado, ver docstring del módulo).
        - `supporting_metrics`: `{"price_to_earnings": ...,
          "price_to_sales": ..., "net_margin": ..., "debt_to_revenue": ...}`,
          tomados directamente de `valuation_metrics`/`health_metrics`.
        - `limitations`: siempre incluye `FRAMEWORK_LIMITATION` (primero),
          seguida de cualquier advertencia en `valuation_metrics.warnings`
          y luego `health_metrics.warnings` (ej. los casos
          `net_income <= 0` o `revenue == 0`).
        - `provenance`: `AnalysisProvenance(ai_provider=response.provider,
          ai_model=response.model, generated_at=response.generated_at)`.
    """
    findings = [response.content]
    supporting_metrics = {
        "price_to_earnings": valuation_metrics.price_to_earnings,
        "price_to_sales": valuation_metrics.price_to_sales,
        "net_margin": health_metrics.net_margin,
        "debt_to_revenue": health_metrics.debt_to_revenue,
    }
    limitations = [
        FRAMEWORK_LIMITATION,
        *valuation_metrics.warnings,
        *health_metrics.warnings,
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


def analyze_value(
    market_data: MarketData,
    statement: FinancialStatement,
    valuation_metrics: ValuationMetrics | None = None,
    health_metrics: FinancialHealthMetrics | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Produce el `AnalysisResult` completo de la estrategia 'value' para una empresa.

    Función de conveniencia que encadena, en orden,
    `calculate_valuation_metrics`/`calculate_financial_health_metrics`
    (solo si `valuation_metrics`/`health_metrics` no se indican),
    `invoke_value_agent` y `parse_value_response`. No traduce las
    excepciones que puedan levantar esas funciones (ver "Fuera de
    alcance" en el docstring del módulo): quien invoque esta función es
    responsable de capturarlas si necesita continuar el flujo ante un
    fallo parcial (ese manejo es responsabilidad del "Orquestador", ver
    TASKS.md, Fase 6). Mismo patrón ya usado por
    `investmentops.analysis_engines.financial_health.analyze_financial_health`/
    `investmentops.analysis_engines.valuation.analyze_valuation`.

    Parameters
    ----------
    market_data:
        El `MarketData` normalizado de la empresa a analizar.
    statement:
        El `FinancialStatement` normalizado de la misma empresa.
    valuation_metrics:
        Métricas de valoración ya calculadas, si se quiere evitar
        recalcularlas. Si no se indica, se calculan aquí mismo con
        `calculate_valuation_metrics`.
    health_metrics:
        Métricas de salud financiera ya calculadas, si se quiere evitar
        recalcularlas. Si no se indica, se calculan aquí mismo con
        `calculate_financial_health_metrics`.
    config:
        Configuración ya cargada, propagada a `invoke_value_agent`.

    Returns
    -------
    AnalysisResult
        El resultado estructurado completo del agente de estrategia
        'value'.
    """
    resolved_valuation_metrics = (
        valuation_metrics
        if valuation_metrics is not None
        else calculate_valuation_metrics(market_data, statement)
    )
    resolved_health_metrics = (
        health_metrics
        if health_metrics is not None
        else calculate_financial_health_metrics(statement)
    )
    response = invoke_value_agent(
        market_data,
        statement,
        resolved_valuation_metrics,
        resolved_health_metrics,
        config=config,
    )
    return parse_value_response(
        response, resolved_valuation_metrics, resolved_health_metrics
    )