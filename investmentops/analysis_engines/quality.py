"""Agente de estrategia: Calidad (quality investing) — invocación al
proveedor de IA.

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
para el agente 'calidad', enviando los datos normalizados ya existentes
junto con el prompt" (TASKS.md, Fase 6, "Motores de análisis por
estrategia").

Sobre el mapeo de datos ya fijado en
`investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md`: este agente
reutiliza, sin recalcularlas, las `FinancialHealthMetrics` ya calculadas
por `calculate_financial_health_metrics` (Fase 1) — `net_margin`,
`debt_to_revenue` — junto con el `FinancialStatement` normalizado como
contexto base. A diferencia del agente "value"
(`investmentops.analysis_engines.value`), que además envía `MarketData`/
`ValuationMetrics`, "calidad" no utiliza ningún dato de mercado ni
múltiplo de valoración: su lectura se limita exclusivamente a la
solidez financiera subyacente (ver STRATEGY_DATA_MAPPING.md, "Qué NO
utiliza"). No introduce ningún cálculo nuevo (ver
`STRATEGY_DATA_MAPPING.md`, "Principio común: ningún cálculo nuevo, solo
reinterpretación").

`invoke_quality_agent` sigue exactamente el mismo patrón ya usado por
`investmentops.analysis_engines.value.invoke_value_agent`/
`investmentops.analysis_engines.growth.invoke_growth_agent`:

1. Carga el prompt del agente desde `prompts/quality.md` (ver
   `investmentops.analysis_engines.prompts.load_prompt` y
   `prompts/README.md`, "Prompts como artefactos, no como código").
2. Resuelve qué proveedor/modelo le corresponde al agente ``"quality"``
   según `config.local.toml` (ver
   `investmentops.ai_providers.selection.resolve_agent_provider` y
   CONFIGURATION.md, sección `[agents]`).
3. Construye la instancia concreta de `AIProvider` correspondiente (ver
   `investmentops.ai_providers.factory.build_ai_provider`; hoy solo
   `AnthropicAIProvider` está implementada).
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   el `FinancialStatement` normalizado y las `FinancialHealthMetrics`
   ya calculadas (nunca recalculadas aquí ni por la IA, conforme a
   `ARCHITECTURE.md`, "La IA es un mecanismo central, no un
   accesorio").

Esta función devuelve el `AIProviderResponse` crudo (texto de respuesta +
metadatos de procedencia). No interpreta ni parsea ese texto por sí
misma: el parseo a `AnalysisResult` es una tarea separada y posterior de
esta misma sección de TASKS.md.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/quality.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `FinancialHealthMetrics`: ya implementado en Fase 1
  (`investmentops.analysis_engines.financial_health.calculate_financial_health_metrics`),
  reutilizado tal cual, sin modificaciones ni duplicación.
- El parseo de la respuesta del modelo al resultado estructurado del
  agente (`AnalysisResult`): tarea separada y siguiente en la misma
  sección de `TASKS.md`.
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
from investmentops.analysis_engines.financial_health import FinancialHealthMetrics
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/quality.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`
#: (en la tarea de parseo, todavía pendiente).
AGENT_ID = "quality"


def invoke_quality_agent(
    statement: FinancialStatement,
    health_metrics: FinancialHealthMetrics,
    *,
    config: dict[str, Any] | None = None,
) -> AIProviderResponse:
    """Invoca al proveedor de IA configurado para el agente de estrategia 'calidad'.

    Combina el prompt del agente (`prompts/quality.md`), el
    proveedor/modelo resuelto para ``"quality"`` según `config.local.toml`,
    y el `FinancialStatement`/`FinancialHealthMetrics` ya normalizados/
    calculados en fases anteriores (nunca recalculados aquí), para
    obtener una interpretación del modelo de lenguaje desde el marco de
    quality investing.

    Parameters
    ----------
    statement:
        El `FinancialStatement` normalizado de la empresa, enviado como
        parte de `data` para que el modelo tenga el contexto completo
        (ingresos, beneficio neto, deuda, fuente y fecha de corte), no
        solo los ratios ya derivados.
    health_metrics:
        Las `FinancialHealthMetrics` ya calculadas por
        `calculate_financial_health_metrics` (Fase 1) para `statement`.
        Se envían tal cual, incluyendo `warnings` si alguna métrica no
        se pudo calcular (ej. `revenue == 0`).
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
        (tarea separada y posterior).

    Raises
    ------
    PromptError
        Si no se puede cargar `prompts/quality.md` (ver
        `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para el agente
        ``"quality"`` según la configuración (ver
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
        "financial_statement": {
            "revenue": statement.revenue,
            "net_income": statement.net_income,
            "debt": statement.debt,
            "source": statement.source,
            "period_end": statement.period_end.isoformat(),
        },
        "financial_health_metrics": {
            "net_margin": health_metrics.net_margin,
            "debt_to_revenue": health_metrics.debt_to_revenue,
            "warnings": list(health_metrics.warnings),
        },
    }

    return provider.complete(prompt, data=data)