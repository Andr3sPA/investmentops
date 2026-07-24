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
"""Agente de estrategia: Growth investing — invocación al proveedor de IA
y parseo de su respuesta al resultado estructurado del agente.

Cubre dos tareas de TASKS.md, Fase 6, "Motores de análisis por estrategia":

- "Implementar la invocación al proveedor de IA configurado para el
  agente 'growth', enviando los datos normalizados ya existentes junto
  con el prompt." (ya completada, ver PROGRESS.md).
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'growth' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no un
  veredicto)." (esta tarea).

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
misma: ese trabajo lo hace `parse_growth_response` (esta tarea).

## Parseo de la respuesta a `AnalysisResult` (`parse_growth_response`, esta tarea)

Traduce un `AIProviderResponse` (más el `TrendAnalysisResult` ya
calculado, el mismo que se envió al proveedor de IA) a la estructura
común `AnalysisResult` definida en
`investmentops.analysis_engines.contracts`, mismo criterio ya aplicado
por `parse_value_response` (Fase 6, "value") y
`parse_financial_health_response`/`parse_valuation_response` (Fase 1):

- `analysis_id`: siempre `AGENT_ID` (``"growth"``).
- `findings`: el texto de interpretación del modelo (`response.content`),
  como un único hallazgo. Igual que `prompts/value.md`, `prompts/growth.md`
  no le pide al modelo un formato estructurado: es texto libre en
  español.
- `supporting_metrics`: las mismas cuatro claves ya calculadas por
  `assemble_trend_analysis` (`revenue_trend`, `net_income_trend`,
  `revenue_growth_by_period`, `net_income_growth_by_period`), tomadas
  tal cual de `trend_result.supporting_metrics` — nunca un valor nuevo
  derivado del texto del modelo, conforme a `ARCHITECTURE.md` ("La IA es
  un mecanismo central, no un accesorio").
- `limitations`: siempre incluye `FRAMEWORK_LIMITATION` — la limitación
  explícita que exige esta tarea ("dejando explícito que es una lectura
  desde un marco particular, no un veredicto"), declarando que esta
  interpretación corresponde únicamente al marco de growth investing, no
  a una evaluación general de la empresa ni a las demás estrategias
  (value, calidad) — seguida de cualquier advertencia ya producida por
  `assemble_trend_analysis` (`trend_result.limitations`: periodo base en
  cero, serie de un solo periodo, huecos irregulares en el calendario).
- `provenance`: `AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`, tomado
  directamente de los metadatos que ya entrega el proveedor de IA.

`FRAMEWORK_LIMITATION` se declara siempre (no depende de ningún caso
degenerado de los datos), mismo criterio ya usado por
`value.FRAMEWORK_LIMITATION`: es una limitación estructural del propio
diseño del agente (una lectura parcial desde un marco concreto), no un
caso degenerado de los números recibidos.

## Función de conveniencia `analyze_growth`

Encadena `assemble_trend_analysis` (si no se pasa ya calculado) →
`invoke_growth_agent` → `parse_growth_response`, mismo criterio ya
aplicado por `analyze_value`/`analyze_financial_health`/`analyze_valuation`.
No traduce las excepciones de las funciones que invoca (`PromptError`,
`AgentProviderSelectionError`, `AIProviderError`) a
`AnalysisEngineError`: esa decisión de integración corresponde al
"Orquestador" (ver TASKS.md, Fase 6, "Orquestador"), no a esta tarea.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/growth.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `TrendAnalysisResult`: ya implementado en Fase 3
  (`investmentops.analysis_engines.trends.assemble_trend_analysis`),
  reutilizado tal cual, sin modificaciones ni duplicación.
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
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.analysis_engines.trends import TrendAnalysisResult, assemble_trend_analysis
from investmentops.config import load_config
from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/growth.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`.
AGENT_ID = "growth"

#: Limitación explícita que declara que esta interpretación corresponde
#: únicamente al marco de growth investing: una lectura particular de la
#: evolución en el tiempo ya calculada, no una evaluación general de la
#: empresa ni un veredicto de inversión (ver "Parseo de la respuesta a
#: AnalysisResult" en el docstring del módulo). Se declara siempre en
#: `AnalysisResult.limitations`, mismo criterio ya usado por
#: `value.FRAMEWORK_LIMITATION`.
FRAMEWORK_LIMITATION = (
    "Esta interpretación corresponde exclusivamente al marco de growth "
    "investing: es una lectura particular de la evolución de ingresos y "
    "beneficios ya calculada, no una evaluación general de la empresa, "
    "ni un veredicto de inversión, ni equivalente a otras lecturas por "
    "estrategia (ej. value, calidad)."
)


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
        (ver `parse_growth_response`).

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


def parse_growth_response(
    response: AIProviderResponse,
    trend_result: TrendAnalysisResult,
) -> AnalysisResult:
    """Traduce la respuesta cruda del proveedor de IA a un `AnalysisResult`.

    Empaqueta el texto de interpretación del modelo (`response.content`)
    como el único hallazgo del agente, adjunta las mismas métricas ya
    calculadas de forma determinística por `assemble_trend_analysis`
    (nunca un valor nuevo derivado del texto del modelo), declara siempre
    `FRAMEWORK_LIMITATION` (esta interpretación es una lectura desde el
    marco de growth investing, no un veredicto ni una evaluación general)
    y construye la procedencia a partir de los metadatos que ya entrega
    el proveedor de IA. Mismo patrón ya usado por
    `investmentops.analysis_engines.value.parse_value_response`.

    Parameters
    ----------
    response:
        La respuesta cruda devuelta por `invoke_growth_agent` (texto de
        interpretación + proveedor/modelo/fecha de generación).
    trend_result:
        El mismo `TrendAnalysisResult` que se envió al proveedor de IA en
        `invoke_growth_agent` (no se recalcula ni se deriva de
        `response`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"growth"``).
        - `findings`: una lista con un único elemento, el texto de
          `response.content` (sin recortar ni reformatear: el prompt no
          exige un formato estructurado, ver docstring del módulo).
        - `supporting_metrics`: `{"revenue_trend": ...,
          "net_income_trend": ..., "revenue_growth_by_period": ...,
          "net_income_growth_by_period": ...}`, tomados directamente de
          `trend_result.supporting_metrics`.
        - `limitations`: siempre incluye `FRAMEWORK_LIMITATION` (primero),
          seguida de cualquier advertencia en `trend_result.limitations`
          (ej. periodo base en cero, serie de un solo periodo, huecos
          irregulares en el calendario).
        - `provenance`: `AnalysisProvenance(ai_provider=response.provider,
          ai_model=response.model, generated_at=response.generated_at)`.
    """
    findings = [response.content]
    supporting_metrics = {
        "revenue_trend": trend_result.supporting_metrics.get("revenue_trend"),
        "net_income_trend": trend_result.supporting_metrics.get("net_income_trend"),
        "revenue_growth_by_period": trend_result.supporting_metrics.get(
            "revenue_growth_by_period"
        ),
        "net_income_growth_by_period": trend_result.supporting_metrics.get(
            "net_income_growth_by_period"
        ),
    }
    limitations = [FRAMEWORK_LIMITATION, *trend_result.limitations]
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


def analyze_growth(
    series: FinancialStatementSeries,
    trend_result: TrendAnalysisResult | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Produce el `AnalysisResult` completo de la estrategia 'growth' para una empresa.

    Función de conveniencia que encadena, en orden,
    `assemble_trend_analysis` (solo si `trend_result` no se indica),
    `invoke_growth_agent` y `parse_growth_response`. No traduce las
    excepciones que puedan levantar esas funciones (ver "Fuera de
    alcance" en el docstring del módulo): quien invoque esta función es
    responsable de capturarlas si necesita continuar el flujo ante un
    fallo parcial (ese manejo es responsabilidad del "Orquestador", ver
    TASKS.md, Fase 6). Mismo patrón ya usado por
    `investmentops.analysis_engines.value.analyze_value`.

    Parameters
    ----------
    series:
        El `FinancialStatementSeries` normalizado de la empresa a
        analizar, usado para calcular `trend_result` si no se indica ya
        calculado.
    trend_result:
        `TrendAnalysisResult` ya calculado, si se quiere evitar
        recalcularlo. Si no se indica, se calcula aquí mismo con
        `assemble_trend_analysis(series)`.
    config:
        Configuración ya cargada, propagada a `invoke_growth_agent`.

    Returns
    -------
    AnalysisResult
        El resultado estructurado completo del agente de estrategia
        'growth'.
    """
    resolved_trend_result = (
        trend_result if trend_result is not None else assemble_trend_analysis(series)
    )
    response = invoke_growth_agent(resolved_trend_result, config=config)
    return parse_growth_response(response, resolved_trend_result)