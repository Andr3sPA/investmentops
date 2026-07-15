"""Agente de análisis: salud financiera.

Cubre, en un mismo módulo, dos tareas relacionadas de TASKS.md, Fase 1,
"Agente de análisis: salud financiera":

- "Implementar el cálculo determinístico de ratios de liquidez,
  endeudamiento y rentabilidad a partir del modelo normalizado (entrada
  del agente, no su resultado final)." (`calculate_financial_health_metrics`).
- "Implementar la invocación al proveedor de IA configurado con esas
  métricas + el prompt." (`invoke_financial_health_agent`).

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
metadatos de procedencia). **No** interpreta ni parsea ese texto a la
estructura final `AnalysisResult` del agente (hallazgos, métricas de
soporte, limitaciones, procedencia): eso es la tarea siguiente y
separada en TASKS.md ("Implementar el parseo de la respuesta del modelo
al resultado estructurado del agente"), explícitamente fuera de alcance
aquí.

Fuera de alcance de este módulo:
- El parseo de la respuesta del modelo de lenguaje al `AnalysisResult`
  final del agente (tarea posterior, ver arriba).
- Cualquier ratio de liquidez: ver `FINANCIAL_HEALTH_METRICS.md`.
- El contenido del prompt en sí (vive en `prompts/financial_health.md`,
  fuera del código Python, ver `prompts/README.md`).
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

#: Identificador de este agente, usado tanto para localizar su archivo de
#: prompt (`prompts/financial_health.md`, ver `prompts/README.md`) como
#: para resolver su proveedor de IA configurado (`config.local.toml`,
#: sección `[agents]`, ver CONFIGURATION.md).
AGENT_ID = "financial_health"


@dataclass(frozen=True)
class FinancialHealthMetrics:
    """Ratios de salud financiera calculados de forma determinística.

    Es el tipo de salida de `calculate_financial_health_metrics`, pensado
    para alimentar el campo `metrics` que recibirá el futuro agente de
    salud financiera (ver
    `investmentops.analysis_engines.contracts.AnalysisEngine.analyze`) y,
    eventualmente, `AnalysisResult.supporting_metrics` una vez ese agente
    esté implementado.

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
        `FINANCIAL_HEALTH_METRICS.md`).
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
        (`AnalysisResult`); ese parseo es una tarea separada y posterior
        (ver TASKS.md).

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
