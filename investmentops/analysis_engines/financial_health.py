"""Agente de análisis: salud financiera.

Cubre, en un mismo módulo, cuatro tareas relacionadas de TASKS.md, Fase 1,
"Agente de análisis: salud financiera":

- "Implementar el cálculo determinístico de ratios de liquidez,
  endeudamiento y rentabilidad a partir del modelo normalizado (entrada
  del agente, no su resultado final)." (`calculate_financial_health_metrics`).
- "Implementar la invocación al proveedor de IA configurado con esas
  métricas + el prompt." (`invoke_financial_health_agent`).
- "Implementar el parseo de la respuesta del modelo al resultado
  estructurado del agente (hallazgos, métricas, advertencias si faltan
  datos, proveedor/modelo usado)." (`parse_financial_health_response`).
- Función de conveniencia que encadena las tres anteriores
  (`analyze_financial_health`), necesaria para que quien registre este
  agente en el futuro orquestador (ver TASKS.md, "Orquestador mínimo") no
  tenga que reimplementar el encadenado calcular → invocar → parsear.

## Cálculo determinístico de métricas

Implementa exactamente las métricas ya decididas en
`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`:

- **Rentabilidad:** ``net_margin = net_income / revenue``.
- **Endeudamiento:** ``debt_to_revenue = debt / revenue``.
- **Liquidez:** fuera de alcance (limitación documentada en
  `FINANCIAL_HEALTH_METRICS.md`; `FinancialStatement` no expone
  `current_assets`/`current_liabilities`). Este módulo no calcula ni
  aproxima ningún ratio de liquidez.

Conforme a `ARCHITECTURE.md` ("La IA es un mecanismo central, no un
accesorio" / "El cálculo determinístico de métricas... es una entrada
para el agente, no un sustituto de su interpretación"), este cálculo es
puro Python, sin invocar ningún proveedor de IA.

### Manejo de `revenue == 0`

Ambos ratios definidos aquí (`net_margin`, `debt_to_revenue`) tienen
`revenue` como denominador. Si `revenue == 0`, calcularlos produciría una
división por cero. Este caso **no** se trata como un error inesperado ni
se aproxima con un valor inventado: `calculate_financial_health_metrics`
devuelve ambos ratios como ``None`` y agrega una advertencia explícita en
`FinancialHealthMetrics.warnings`.

## Invocación al proveedor de IA

`invoke_financial_health_agent` combina las piezas ya construidas en
tareas anteriores para invocar realmente al proveedor de IA configurado
para este agente:

1. Carga el prompt del agente desde `prompts/financial_health.md` (ver
   `investmentops.analysis_engines.prompts.load_prompt` y
   `prompts/README.md`, "Prompts como artefactos, no como código").
2. Resuelve qué proveedor/modelo le corresponde al agente
   ``"financial_health"`` según `config.local.toml` (ver
   `investmentops.ai_providers.selection.resolve_agent_provider` y
   CONFIGURATION.md, sección `[agents]`).
3. Construye la instancia concreta de `AIProvider` correspondiente (ver
   `investmentops.ai_providers.factory.build_ai_provider`; hoy solo
   `AnthropicAIProvider` está implementada).
4. Invoca `AIProvider.complete(prompt, data=...)`, enviando como `data`
   el `FinancialStatement` normalizado y las `FinancialHealthMetrics` ya
   calculadas (nunca al revés: la IA nunca calcula estas métricas, solo
   las interpreta, conforme a `ARCHITECTURE.md`).

Esta función devuelve el `AIProviderResponse` crudo (texto de respuesta +
metadatos de procedencia). No interpreta ni parsea ese texto por sí
misma: ese trabajo lo hace `parse_financial_health_response`.

## Parseo de la respuesta a `AnalysisResult`

`parse_financial_health_response` traduce un `AIProviderResponse` (más
las `FinancialHealthMetrics` ya calculadas, las mismas que se enviaron al
proveedor de IA) a la estructura común `AnalysisResult` definida en
`investmentops.analysis_engines.contracts`:

- `analysis_id`: siempre `AGENT_ID` (``"financial_health"``).
- `findings`: el texto de interpretación del modelo
  (`response.content`), como un único hallazgo. El prompt
  (`prompts/financial_health.md`) no le pide al modelo un formato
  estructurado (JSON, secciones marcadas): es texto libre en español, por
  lo que "parsear" aquí significa empaquetar ese texto como hallazgo, no
  extraer campos de una respuesta estructurada (ver nota dejada en
  PROGRESS.md para esta tarea).
- `supporting_metrics`: las mismas `FinancialHealthMetrics` ya calculadas
  de forma determinística (`net_margin`, `debt_to_revenue`) — nunca un
  valor nuevo derivado del texto del modelo, conforme a
  `ARCHITECTURE.md` ("La IA es un mecanismo central, no un accesorio").
- `limitations`: siempre incluye la limitación de liquidez ya documentada
  en `FINANCIAL_HEALTH_METRICS.md` (este agente no calcula liquidez), más
  cualquier advertencia de `FinancialHealthMetrics.warnings` (ej. el caso
  `revenue == 0`).
- `provenance`: `AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`, tomado
  directamente de los metadatos que ya entrega el proveedor de IA.

## Función de conveniencia `analyze_financial_health`

Encadena `calculate_financial_health_metrics` (si no se pasan métricas ya
calculadas) → `invoke_financial_health_agent` → 
`parse_financial_health_response`, para que quien quiera un
`AnalysisResult` completo a partir de un `FinancialStatement` no tenga
que orquestar manualmente las tres funciones. No traduce las excepciones
de las funciones que invoca (`PromptError`, `AgentProviderSelectionError`,
`AIProviderError`) a `AnalysisEngineError`: decidir si este módulo debe
exponer una implementación que cumpla literalmente el protocolo
`AnalysisEngine` (incluyendo esa traducción de errores) es una decisión
de integración que corresponde al "Orquestador mínimo" (ver TASKS.md),
no a esta tarea de parseo.

Fuera de alcance de este módulo:
- Cualquier ratio de liquidez: ver `FINANCIAL_HEALTH_METRICS.md`.
- El contenido del prompt en sí (vive en `prompts/financial_health.md`,
  fuera del código Python, ver `prompts/README.md`).
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

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/financial_health.md`, ver `prompts/README.md`) como
#: para resolver su proveedor de IA configurado (`config.local.toml`,
#: sección `[agents]`, ver CONFIGURATION.md) y como `AnalysisResult.analysis_id`.
AGENT_ID = "financial_health"

#: Limitación explícita de liquidez, conforme a
#: `FINANCIAL_HEALTH_METRICS.md`: el modelo de dominio normalizado no
#: expone `current_assets`/`current_liabilities`, por lo que este agente
#: nunca calcula ni aproxima un ratio de liquidez. Se declara siempre en
#: `AnalysisResult.limitations`, en vez de omitir el tema en silencio.
LIQUIDITY_LIMITATION = (
    "No se dispone de datos de liquidez (activos/pasivos corrientes) en el "
    "modelo de dominio normalizado actual; este análisis no incluye un "
    "ratio de liquidez."
)


@dataclass(frozen=True)
class FinancialHealthMetrics:
    """Ratios de salud financiera calculados de forma determinística.

    Es el tipo de salida de `calculate_financial_health_metrics`, pensado
    para alimentar el campo `metrics` que recibe
    `invoke_financial_health_agent` y, a través de
    `parse_financial_health_response`, `AnalysisResult.supporting_metrics`.

    Attributes
    ----------
    net_margin:
        Margen neto (`net_income / revenue`), o ``None`` si no se pudo
        calcular (ver "Manejo de `revenue == 0`" en el docstring del
        módulo).
    debt_to_revenue:
        Deuda sobre ingresos (`debt / revenue`), o ``None`` si no se pudo
        calcular, por la misma razón que `net_margin`.
    warnings:
        Advertencias explícitas sobre métricas que no se pudieron
        calcular (ej. por `revenue == 0`). Vacío si ambos ratios se
        calcularon sin problema. No incluye la limitación de liquidez
        (esa es una ausencia estructural del modelo, no un caso
        degenerado de los datos, y ya está documentada aparte en
        `FINANCIAL_HEALTH_METRICS.md` y en `LIQUIDITY_LIMITATION`).
    """

    net_margin: float | None
    debt_to_revenue: float | None
    warnings: Sequence[str]


def calculate_financial_health_metrics(
    statement: FinancialStatement,
) -> FinancialHealthMetrics:
    """Calcula `net_margin` y `debt_to_revenue` a partir de un `FinancialStatement`.

    Cálculo puramente determinístico (sin IA), conforme a
    `FINANCIAL_HEALTH_METRICS.md`:

    - ``net_margin = statement.net_income / statement.revenue``
    - ``debt_to_revenue = statement.debt / statement.revenue``

    Parameters
    ----------
    statement:
        El `FinancialStatement` ya normalizado (ver
        investmentops.data_layer) del que se derivan estos ratios.

    Returns
    -------
    FinancialHealthMetrics
        Los ratios calculados. Si ``statement.revenue == 0``, ambos
        campos de ratio son ``None`` y `warnings` contiene una
        advertencia explícita, en vez de lanzar una excepción o inventar
        un valor.
    """
    if statement.revenue == 0:
        return FinancialHealthMetrics(
            net_margin=None,
            debt_to_revenue=None,
            warnings=(
                "No se pudieron calcular 'net_margin' ni 'debt_to_revenue': "
                "los ingresos (revenue) son 0, lo que produciría una "
                "división por cero.",
            ),
        )

    net_margin = statement.net_income / statement.revenue
    debt_to_revenue = statement.debt / statement.revenue

    return FinancialHealthMetrics(
        net_margin=net_margin,
        debt_to_revenue=debt_to_revenue,
        warnings=(),
    )


def invoke_financial_health_agent(
    statement: FinancialStatement,
    metrics: FinancialHealthMetrics,
    *,
    config: dict[str, Any] | None = None,
) -> AIProviderResponse:
    """Invoca al proveedor de IA configurado para el agente de salud financiera.

    Combina el prompt del agente (`prompts/financial_health.md`), el
    proveedor/modelo resuelto para ``"financial_health"`` según
    `config.local.toml`, y las métricas ya calculadas de forma
    determinística (`metrics`, nunca recalculadas por la IA), para
    obtener una interpretación del modelo de lenguaje.

    Parameters
    ----------
    statement:
        El `FinancialStatement` normalizado de la empresa, enviado como
        parte de `data` para que el modelo tenga el contexto completo
        (ingresos, beneficio neto, deuda, fuente y fecha de corte), no
        solo los ratios ya derivados.
    metrics:
        Las `FinancialHealthMetrics` ya calculadas por
        `calculate_financial_health_metrics` para `statement`. Se envían
        tal cual, incluyendo `warnings` si algún ratio no se pudo
        calcular (ver prompt del agente, que instruye a declarar esa
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
        (`AnalysisResult`); ver `parse_financial_health_response`.

    Raises
    ------
    PromptError
        Si no se puede cargar `prompts/financial_health.md` (ver
        `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para el agente
        ``"financial_health"`` según la configuración (ver
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
        "metrics": {
            "net_margin": metrics.net_margin,
            "debt_to_revenue": metrics.debt_to_revenue,
            "warnings": list(metrics.warnings),
        },
    }

    return provider.complete(prompt, data=data)


def parse_financial_health_response(
    response: AIProviderResponse,
    metrics: FinancialHealthMetrics,
) -> AnalysisResult:
    """Traduce la respuesta cruda del proveedor de IA a un `AnalysisResult`.

    Empaqueta el texto de interpretación del modelo (`response.content`)
    como el único hallazgo del agente, adjunta las mismas métricas ya
    calculadas de forma determinística (nunca un valor nuevo derivado del
    texto del modelo) y construye la procedencia a partir de los
    metadatos que ya entrega el proveedor de IA.

    Parameters
    ----------
    response:
        La respuesta cruda devuelta por `invoke_financial_health_agent`
        (texto de interpretación + proveedor/modelo/fecha de generación).
    metrics:
        Las mismas `FinancialHealthMetrics` que se enviaron al proveedor
        de IA en `invoke_financial_health_agent` (no se recalculan ni se
        derivan de `response`).

    Returns
    -------
    AnalysisResult
        - `analysis_id`: siempre `AGENT_ID` (``"financial_health"``).
        - `findings`: una lista con un único elemento, el texto de
          `response.content` (sin recortar ni reformatear: el prompt no
          exige un formato estructurado, ver docstring del módulo).
        - `supporting_metrics`: `{"net_margin": ..., "debt_to_revenue": ...}`,
          tomados directamente de `metrics`.
        - `limitations`: siempre incluye `LIQUIDITY_LIMITATION`, seguida
          de cualquier advertencia en `metrics.warnings` (ej. el caso
          `revenue == 0`).
        - `provenance`: `AnalysisProvenance(ai_provider=response.provider,
          ai_model=response.model, generated_at=response.generated_at)`.
    """
    findings = [response.content]
    supporting_metrics = {
        "net_margin": metrics.net_margin,
        "debt_to_revenue": metrics.debt_to_revenue,
    }
    limitations = [LIQUIDITY_LIMITATION, *metrics.warnings]
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


def analyze_financial_health(
    statement: FinancialStatement,
    metrics: FinancialHealthMetrics | None = None,
    *,
    config: dict[str, Any] | None = None,
) -> AnalysisResult:
    """Produce el `AnalysisResult` completo de salud financiera para una empresa.

    Función de conveniencia que encadena, en orden, `calculate_
    financial_health_metrics` (solo si `metrics` no se indica),
    `invoke_financial_health_agent` y `parse_financial_health_response`.
    No traduce las excepciones que puedan levantar esas funciones (ver
    "Fuera de alcance" en el docstring del módulo): quien invoque esta
    función es responsable de capturarlas si necesita continuar el flujo
    ante un fallo parcial (ese manejo es responsabilidad del "Orquestador
    mínimo", ver TASKS.md).

    Parameters
    ----------
    statement:
        El `FinancialStatement` normalizado de la empresa a analizar.
    metrics:
        Métricas ya calculadas, si se quiere evitar recalcularlas (por
        ejemplo, si ya se calcularon antes para otro propósito). Si no
        se indica, se calculan aquí mismo con
        `calculate_financial_health_metrics`.
    config:
        Configuración ya cargada, propagada a `invoke_financial_health_agent`.

    Returns
    -------
    AnalysisResult
        El resultado estructurado completo del agente de salud
        financiera.
    """
    resolved_metrics = (
        metrics if metrics is not None else calculate_financial_health_metrics(statement)
    )
    response = invoke_financial_health_agent(statement, resolved_metrics, config=config)
    return parse_financial_health_response(response, resolved_metrics)
