"""Agente de estrategia: Growth investing — invocación al proveedor de IA.

Cubre la tarea "Implementar la invocación al proveedor de IA configurado
para el agente 'growth', enviando los datos normalizados ya existentes
junto con el prompt" (TASKS.md, Fase 6, "Motores de análisis por
estrategia").

Sobre el mapeo de datos ya fijado en
`investmentops/analysis_engines/STRATEGY_DATA_MAPPING.md`: este agente
reutiliza, sin recalcularlo, el resultado ya producido por
`investmentops.analysis_engines.trends.assemble_trend_analysis` (Fase 3)
— `revenue_trend`, `net_income_trend` (tendencia agregada) y
`revenue_growth_by_period`, `net_income_growth_by_period` (variación por
periodo) — como único contexto enviado al modelo de lenguaje. No
introduce ningún cálculo nuevo (ver `STRATEGY_DATA_MAPPING.md`,
"Principio común: ningún cálculo nuevo, solo reinterpretación").

`invoke_growth_agent` sigue exactamente el mismo patrón ya usado por
`investmentops.analysis_engines.value.invoke_value_agent`:

1. Carga el prompt del agente desde `prompts/growth.md` (ver
   `investmentops.analysis_engines.prompts.load_prompt` y
   `prompts/README.md`, "Prompts como artefactos, no como código").
2. Resuelve qué proveedor/modelo le corresponde al agente ``"growth"``
   según `config.local.toml` (ver
   `investmentops.ai_providers.selection.resolve_agent_provider` y
   CONFIGURATION.md, sección `[agents]`).
3. Construye la instancia concreta de `AIProvider` correspondiente (ver
   `investmentops.ai_providers.factory.build_ai_provider`; hoy solo
   `AnthropicAIProvider` está implementada).
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   la tendencia agregada y la variación por periodo ya calculadas por
   `assemble_trend_analysis` (nunca recalculadas aquí ni por la IA,
   conforme a `ARCHITECTURE.md`, "La IA es un mecanismo central, no un
   accesorio").

Esta función devuelve el `AIProviderResponse` crudo (texto de respuesta +
metadatos de procedencia). No interpreta ni parsea ese texto por sí
misma: el parseo a `AnalysisResult` es una tarea separada y posterior de
esta misma sección de TASKS.md.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/growth.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `TrendAnalysisResult`: ya implementado en Fase 3
  (`investmentops.analysis_engines.trends.assemble_trend_analysis`),
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
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.analysis_engines.trends import TrendAnalysisResult
from investmentops.config import load_config

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/growth.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`
#: (en la tarea de parseo, todavía pendiente).
AGENT_ID = "growth"


def invoke_growth_agent(
    trend_result: TrendAnalysisResult,
    *,
    config: dict[str, Any] | None = None,
) -> AIProviderResponse:
    """Invoca al proveedor de IA configurado para el agente de estrategia 'growth'.

    Combina el prompt del agente (`prompts/growth.md`), el
    proveedor/modelo resuelto para ``"growth"`` según `config.local.toml`,
    y el resultado ya calculado de forma determinística por
    `assemble_trend_analysis` (nunca recalculado aquí), para obtener una
    interpretación del modelo de lenguaje desde el marco de growth
    investing.

    Parameters
    ----------
    trend_result:
        El `TrendAnalysisResult` ya producido por
        `investmentops.analysis_engines.trends.assemble_trend_analysis`
        para la serie histórica de la empresa. Se envía tal cual: la
        tendencia agregada (`revenue_trend`/`net_income_trend`) y la
        variación por periodo (`revenue_growth_by_period`/
        `net_income_growth_by_period`), tomadas de
        `trend_result.supporting_metrics`, más las advertencias ya
        producidas (`trend_result.limitations`, ej. periodo base en
        cero, serie de un solo periodo, huecos irregulares).
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
        (tarea separada y posterior de esta misma sección).

    Raises
    ------
    PromptError
        Si no se puede cargar `prompts/growth.md` (ver
        `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para el agente
        ``"growth"`` según la configuración (ver
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
        "revenue_trend": trend_result.supporting_metrics.get("revenue_trend"),
        "net_income_trend": trend_result.supporting_metrics.get("net_income_trend"),
        "revenue_growth_by_period": trend_result.supporting_metrics.get(
            "revenue_growth_by_period"
        ),
        "net_income_growth_by_period": trend_result.supporting_metrics.get(
            "net_income_growth_by_period"
        ),
        "warnings": list(trend_result.limitations),
    }

    return provider.complete(prompt, data=data)