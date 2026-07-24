"""Agente de estrategia: Calidad (quality investing) — invocación al
proveedor de IA y parseo de su respuesta al resultado estructurado del
agente.

Cubre dos tareas de TASKS.md, Fase 6, "Motores de análisis por estrategia":

- "Implementar la invocación al proveedor de IA configurado para el
  agente 'calidad', enviando los datos normalizados ya existentes junto
  con el prompt." (ya completada, ver PROGRESS.md).
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente 'calidad' (hallazgos, procedencia de IA,
  dejando explícito que es una lectura desde un marco particular, no un
  veredicto)." (esta tarea).

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
misma: ese trabajo lo hace `parse_quality_response` (esta tarea).

## Parseo de la respuesta a `AnalysisResult` (`parse_quality_response`, esta tarea)

Traduce un `AIProviderResponse` (más las `FinancialHealthMetrics` ya
calculadas, las mismas que se enviaron al proveedor de IA) a la
estructura común `AnalysisResult` definida en
`investmentops.analysis_engines.contracts`, mismo criterio ya aplicado
por `parse_value_response`/`parse_growth_response` (Fase 6) y
`parse_financial_health_response`/`parse_valuation_response` (Fase 1):

- `analysis_id`: siempre `AGENT_ID` (``"quality"``).
- `findings`: el texto de interpretación del modelo (`response.content`),
  como un único hallazgo. Igual que `prompts/value.md`/`prompts/growth.md`,
  `prompts/quality.md` no le pide al modelo un formato estructurado: es
  texto libre en español.
- `supporting_metrics`: las mismas `FinancialHealthMetrics` ya calculadas
  de forma determinística (`net_margin`, `debt_to_revenue`) — nunca un
  valor nuevo derivado del texto del modelo, conforme a
  `ARCHITECTURE.md` ("La IA es un mecanismo central, no un accesorio").
- `limitations`: siempre incluye `FRAMEWORK_LIMITATION` — la limitación
  explícita que exige esta tarea ("dejando explícito que es una lectura
  desde un marco particular, no un veredicto"), declarando que esta
  interpretación corresponde únicamente al marco de quality investing,
  no a una evaluación general de la empresa ni a las demás estrategias
  (value, growth) ni al diagnóstico general de salud financiera de Fase
  1 — seguida de cualquier advertencia de `health_metrics.warnings`
  (ej. el caso `revenue == 0`).
- `provenance`: `AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`, tomado
  directamente de los metadatos que ya entrega el proveedor de IA.

`FRAMEWORK_LIMITATION` se declara siempre (no depende de ningún caso
degenerado de los datos), mismo criterio ya usado por
`value.FRAMEWORK_LIMITATION`/`growth.FRAMEWORK_LIMITATION`: es una
limitación estructural del propio diseño del agente (una lectura
parcial desde un marco concreto), no un caso degenerado de los números
recibidos.

## Función de conveniencia `analyze_quality`

Encadena `calculate_financial_health_metrics` (si no se pasa ya
calculada) → `invoke_quality_agent` → `parse_quality_response`, mismo
criterio ya aplicado por `analyze_value`/`analyze_growth`/
`analyze_financial_health`. No traduce las excepciones de las funciones
que invoca (`PromptError`, `AgentProviderSelectionError`,
`AIProviderError`) a `AnalysisEngineError`: esa decisión de integración
corresponde al "Orquestador" (ver TASKS.md, Fase 6, "Orquestador"), no a
esta tarea.

Fuera de alcance de este módulo:
- El contenido del prompt en sí (vive en `prompts/quality.md`, fuera del
  código Python, ver `prompts/README.md`).
- El cálculo de `FinancialHealthMetrics`: ya implementado en Fase 1
  (`investmentops.analysis_engines.financial_health.calculate_financial_health_metrics`),
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
from investmentops.analysis_engines.financial_health import (
    FinancialHealthMetrics,
    calculate_financial_health_metrics,
)
from investmentops.analysis_engines.prompts import load_prompt
from investmentops.config import load_config
from investmentops.data_layer.financial_statements import FinancialStatement

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/quality.md`, ver `prompts/README.md`) como para
#: resolver su proveedor de IA configurado (`config.local.toml`, sección
#: `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`.
AGENT_ID = "quality"

#: Limitación explícita que declara que esta interpretación corresponde
#: únicamente al marco de quality investing: una lectura particular de
#: la solidez financiera subyacente ya calculada, no una evaluación
#: general de la empresa, ni un veredicto de inversión, ni equivalente
#: a otras lecturas por estrategia (value, growth) ni al diagnóstico
#: general de salud financiera de Fase 1 (ver "Parseo de la respuesta a
#: AnalysisResult" en el docstring del módulo). Se declara siempre en
#: `AnalysisResult.limitations`, mismo criterio ya usado por
#: `value.FRAMEWORK_LIMITATION`/`growth.FRAMEWORK_LIMITATION`.
FRAMEWORK_LIMITATION = (
    "Esta interpretación corresponde exclusivamente al marco de quality "
    "investing: es una lectura particular de la solidez financiera "
    "subyacente ya calculada, no una evaluación general de la empresa, "
    "ni un veredicto de inversión, ni equivalente a otras lecturas por "
    "estrategia (ej. value, growth) ni al diagnóstico general de salud "
    "financiera presentado en otra sección del reporte."
)


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
        (ver `parse_quality_response`).

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


def parse_quality_response(
    response: AIProviderResponse,
    health_metrics: FinancialHealthMetrics,
) -> AnalysisResult:
    """Traduce la respuesta cruda del proveedor de IA a un `AnalysisResult`.

    Empaqueta el texto de interpretación del modelo (`response.content`)
    como el único hallazgo del agente, adjunta las mismas
    `FinancialHealthMetrics` ya calculadas de forma determinística (nunca
    un valor nuevo derivado del texto del modelo), declara siempre
    `FRAMEWORK_LIMITATION` (esta interpretación es una lectura desde el
    marco de quality investing, no un veredicto ni una evaluación
    general) y construye la procedencia a partir de los metadatos que ya
    entrega el proveedor de IA. Mismo patrón ya usado por
    `investmentops.analysis_engines.value.parse_value_response`/
    `investmentops.analysis_engines.growth.parse_growth_response`.

    Parameters
    ----------
    response:
        La respuesta cruda devuelta por `invoke_quality_agent` (texto de
        interpretación + proveedor/modelo/fecha de generación).
    health_metrics:
        Las mismas `FinancialHealthMetrics` que se enviaron al proveedor
        de IA en `invoke_quality_agent` (no se recalculan ni se derivan
        de `response`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"quality"``).
        - `findings`: una lista con un único elemento, el texto de
          `response.content` (sin recortar ni reformatear: el prompt no
          exige un formato estructurado, ver docstring del módulo).
        - `supporting_metrics`: `{"net_margin": ..., "debt_to_revenue": ...}`,
          tomados directamente de `health_metrics`.
        - `limitations`: siempre incluye `FRAMEWORK_LIMITATION` (primero),
          seguida de cualquier advertencia en `health_metrics.warnings`
          (ej. el caso `revenue == 0`).
        - `provenance`: `AnalysisProvenance(ai_provider=response.provider,
          ai_model=response.model, generated_at=response.generated_at)`.
    """
    findings = [response.content]
    supporting_metrics = {
        "net_margin": health_metrics.net_margin,
        "debt_to_revenue": health_metrics.debt_to_revenue,
    }
    limitations = [FRAMEWORK_LIMITATION, *health_metrics.warnings]
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


def analyze_quality(
    statement: FinancialStatement,
    health_metrics: FinancialHealthMetrics | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Produce el `AnalysisResult` completo de la estrategia 'calidad' para una empresa.

    Función de conveniencia que encadena, en orden,
    `calculate_financial_health_metrics` (solo si `health_metrics` no se
    indica), `invoke_quality_agent` y `parse_quality_response`. No
    traduce las excepciones que puedan levantar esas funciones (ver
    "Fuera de alcance" en el docstring del módulo): quien invoque esta
    función es responsable de capturarlas si necesita continuar el flujo
    ante un fallo parcial (ese manejo es responsabilidad del
    "Orquestador", ver TASKS.md, Fase 6). Mismo patrón ya usado por
    `investmentops.analysis_engines.value.analyze_value`/
    `investmentops.analysis_engines.growth.analyze_growth`.

    Parameters
    ----------
    statement:
        El `FinancialStatement` normalizado de la empresa a analizar.
    health_metrics:
        Métricas de salud financiera ya calculadas, si se quiere evitar
        recalcularlas. Si no se indica, se calculan aquí mismo con
        `calculate_financial_health_metrics`.
    config:
        Configuración ya cargada, propagada a `invoke_quality_agent`.

    Returns
    -------
    AnalysisResult
        El resultado estructurado completo del agente de estrategia
        'calidad'.
    """
    resolved_health_metrics = (
        health_metrics
        if health_metrics is not None
        else calculate_financial_health_metrics(statement)
    )
    response = invoke_quality_agent(statement, resolved_health_metrics, config=config)
    return parse_quality_response(response, resolved_health_metrics)