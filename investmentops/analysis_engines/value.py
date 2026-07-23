"""Agente de estrategia: Value investing — invocación al proveedor de IA.

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
para el agente 'value', enviando los datos normalizados ya existentes
(sin nuevas fuentes ni cálculos adicionales) junto con el prompt"
(TASKS.md, Fase 6, "Motores de análisis por estrategia").

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
misma: ese trabajo es alcance de la tarea siguiente ("Implementar el
parseo de la respuesta del modelo al resultado estructurado del agente
'value'").

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/value.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `ValuationMetrics`/`FinancialHealthMetrics`: ya
  implementado en Fase 1
  (`investmentops.analysis_engines.valuation.calculate_valuation_metrics`,
  `investmentops.analysis_engines.financial_health.calculate_financial_health_metrics`),
  reutilizado tal cual, sin modificaciones ni duplicación.
- El parseo de la respuesta a un resultado estructurado del agente
  (hallazgos, procedencia de IA): tarea separada y siguiente en la misma
  sección de `TASKS.md`.
"""

from __future__ import annotations

from typing import Any

from investmentops.ai_providers import (
    AIProviderResponse,
    build_ai_provider,
    resolve_agent_provider,
)
from investmentops.analysis_engines.financial_health import FinancialHealthMetrics
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.analysis_engines.valuation import ValuationMetrics
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/value.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y, en la tarea siguiente, como
#: `AnalysisResult.analysis_id`.
AGENT_ID = "value"


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
        (tarea separada y siguiente en `TASKS.md`).

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