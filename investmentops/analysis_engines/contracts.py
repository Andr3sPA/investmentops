"""Contrato de "Analysis Engine" (Motores de análisis / Agentes de IA).

Ver ARCHITECTURE.md, componente 5 ("Motores de análisis"), y TASKS.md,
Fase 1, sección "Contratos e interfaces": *"Definir el contrato de
'analysis engine' / agente de IA (entrada: modelo de dominio normalizado +
métricas precalculadas cuando aplique; salida: resultado estructurado)."*

Este módulo NO implementa ningún agente concreto (eso es una tarea
posterior, ver TASKS.md, secciones "Agente de análisis: salud financiera"
y "Agente de análisis: valoración"). Solo define el contrato que todo
motor de análisis debe cumplir, de forma que:

- El orquestador (investmentops.core) pueda invocar cualquier agente sin
  conocer su implementación concreta.
- Agregar un nuevo tipo de análisis (ej. riesgos, comparables, una nueva
  estrategia de inversión en la Fase 6) no requiera modificar el
  orquestador ni los agentes ya existentes (ver ARCHITECTURE.md,
  "Extensibilidad").

Resumen del contrato (ver ARCHITECTURE.md, componente 5):

- **Entrada:** el modelo de dominio normalizado de una empresa (producido
  por investmentops.data_layer) y, cuando aplica, métricas ya calculadas
  de forma determinística a partir de ese modelo (ej. ratios de liquidez,
  múltiplos de valoración). El cálculo determinístico de esas métricas es
  responsabilidad del propio agente o de una función auxiliar suya, nunca
  del modelo de lenguaje: la IA solo interpreta números ya calculados en
  código, jamás los produce (ver ARCHITECTURE.md, principio "La IA es un
  mecanismo central, no un accesorio", y GOALS.md, "El sistema informa, no
  decide").
- **Salida:** un "Resultado de análisis" estructurado — identificador del
  análisis, hallazgos (interpretación en lenguaje natural producida por el
  agente de IA), métricas de soporte, advertencias/limitaciones, y
  metadatos de procedencia (qué proveedor y modelo de IA generó la
  interpretación, y cuándo).
- **Fallos:** un agente que no puede completar su análisis (el proveedor
  de IA no responde, la respuesta no se puede interpretar, faltan datos
  imprescindibles) debe señalarlo mediante `AnalysisEngineError`, nunca
  inventando hallazgos ni devolviendo una interpretación parcial como si
  fuera completa. Igual que con `DataProviderError`
  (investmentops.data_providers.contracts), esto es lo que le permite al
  orquestador continuar con los demás análisis y dejar el fallo explícito
  en el resultado final (ver ARCHITECTURE.md, "Manejo de errores y
  limitaciones").
- **Restricción de contenido:** ningún `AnalysisResult` debe contener una
  recomendación de compra/venta ni un veredicto final. Esta es una
  restricción de contenido (lo que el agente redacta, guiado por su
  prompt), no algo que este contrato pueda forzar estructuralmente; queda
  documentada aquí como recordatorio para quien implemente cada agente y
  su prompt (ver `prompts/README.md` y ARCHITECTURE.md, "El sistema
  informa, no decide").

Fuera de alcance de este módulo:
- Cualquier implementación concreta de agente (invocación al proveedor de
  IA, cálculo de métricas específicas, parseo de la respuesta del
  modelo): eso corresponde a cada agente concreto (ver TASKS.md).
- La forma exacta del modelo de dominio normalizado que reciben los
  agentes (`company_data` abajo): su estructura vive en
  investmentops.data_layer y aún no está definida (ver TASKS.md,
  "Contratos e interfaces" > estructuras "Empresa", "Estados financieros
  normalizados", "Datos de mercado"). Este contrato lo trata como `Any`
  para no acoplarse a un diseño que todavía no existe; una vez definido,
  los agentes concretos lo tipan con precisión sin que este contrato
  genérico deba cambiar.
- La interfaz de proveedores de IA que cada agente usa internamente para
  invocar al modelo de lenguaje: eso vive en
  investmentops.ai_providers (ver TASKS.md, "Definir el contrato de 'AI
  provider'", tarea aún pendiente).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable


class AnalysisEngineError(RuntimeError):
    """Error al ejecutar un motor de análisis (agente de IA).

    Cubre cualquier fallo que impida producir un resultado de análisis
    completo y confiable: el proveedor de IA configurado no responde,
    devuelve un formato que no se puede parsear al resultado estructurado,
    o faltan datos de entrada imprescindibles para el análisis. El
    orquestador (investmentops.core) captura este tipo de excepción para
    continuar con los demás motores de análisis en vez de detener todo el
    flujo (ver ARCHITECTURE.md, "Manejo de errores y limitaciones").
    """


@dataclass(frozen=True)
class AnalysisProvenance:
    """Procedencia de la interpretación producida por un agente de IA.

    Attributes
    ----------
    ai_provider:
        Identificador del proveedor de IA que generó la interpretación
        (ej. ``"anthropic"``, ``"ollama"``), tal como se configura en
        `config.local.toml` bajo `[ai_providers.<nombre>]` (ver
        CONFIGURATION.md).
    ai_model:
        Identificador del modelo concreto usado dentro de ese proveedor
        (ej. ``"claude-sonnet-5"``).
    generated_at:
        Fecha y hora en que se generó esta interpretación.
    """

    ai_provider: str
    ai_model: str
    generated_at: datetime


@dataclass(frozen=True)
class AnalysisResult:
    """Resultado estructurado que produce todo motor de análisis.

    Este es el tipo de salida común a todos los agentes de análisis (ver
    ARCHITECTURE.md, "Modelo de datos interno", entrada "Resultado de
    análisis"). El orquestador ensambla los `AnalysisResult` de todos los
    agentes ejecutados en un único "Resultado de investigación" (ver
    investmentops.core).

    Attributes
    ----------
    analysis_id:
        Identificador del análisis (ej. ``"financial_health"``,
        ``"valuation"``). Es el mismo identificador que usa el agente para
        localizar su propio archivo de prompt en `prompts/` (ver
        `prompts/README.md`).
    findings:
        Hallazgos/interpretación producidos por el agente de IA, en
        lenguaje natural, a partir de las métricas de soporte. Nunca debe
        incluir una recomendación de compra/venta ni un veredicto final
        (ver ARCHITECTURE.md, "El sistema informa, no decide").
    supporting_metrics:
        Métricas de soporte que respaldan los hallazgos, calculadas de
        forma determinística en código (no por el modelo de lenguaje)
        antes de invocar al proveedor de IA. Es lo que hace reproducibles
        los números del análisis, independientemente de la interpretación.
    limitations:
        Advertencias o limitaciones explícitas del análisis (ej. "cálculo
        basado en datos parciales", "sin datos de los últimos dos
        trimestres"), conforme a ARCHITECTURE.md, "Manejo de errores y
        limitaciones".
    provenance:
        Procedencia de la interpretación: qué proveedor y modelo de IA la
        generó, y cuándo (ver `AnalysisProvenance`).
    """

    analysis_id: str
    findings: Sequence[str]
    supporting_metrics: Mapping[str, Any]
    limitations: Sequence[str]
    provenance: AnalysisProvenance


@runtime_checkable
class AnalysisEngine(Protocol):
    """Contrato común que debe cumplir todo motor de análisis.

    Cualquier módulo bajo investmentops.analysis_engines que implemente
    este contrato puede ser invocado por el orquestador sin que este
    último conozca su implementación concreta (ver ARCHITECTURE.md,
    "Regla de dependencia" y "Extensibilidad").

    Se define como `Protocol` (tipado estructural), igual que
    `investmentops.data_providers.contracts.DataProvider`: cualquier
    objeto que exponga un método `analyze` con esta firma cumple el
    contrato, sin necesidad de heredar de una clase concreta. Esto deja
    abierta la implementación de cada agente (salud financiera,
    valoración, y los que se agreguen en fases posteriores) para las
    tareas correspondientes en TASKS.md.
    """

    def analyze(
        self,
        company_data: Any,
        metrics: Mapping[str, Any] | None = None,
    ) -> AnalysisResult:
        """Produce un resultado de análisis a partir del modelo normalizado.

        Parameters
        ----------
        company_data:
            El modelo de dominio normalizado de la empresa a analizar
            (producido por investmentops.data_layer). Se tipa como `Any`
            en este contrato genérico porque la estructura concreta de
            ese modelo aún no está definida (ver TASKS.md, "Contratos e
            interfaces"); cada agente concreto puede tiparlo con más
            precisión una vez exista.
        metrics:
            Métricas ya calculadas de forma determinística a partir de
            `company_data`, cuando el agente las necesita como entrada
            (ej. ratios de liquidez ya calculados para el agente de salud
            financiera). Es opcional porque no todo agente requiere un
            precálculo separado: algunos pueden calcular sus propias
            métricas internamente a partir de `company_data` y exponerlas
            luego en `AnalysisResult.supporting_metrics`.

        Returns
        -------
        AnalysisResult
            El resultado estructurado del análisis, incluyendo hallazgos,
            métricas de soporte, limitaciones y procedencia.

        Raises
        ------
        AnalysisEngineError
            Si el agente no puede producir un resultado completo y
            confiable (el proveedor de IA no responde, su respuesta no se
            puede interpretar, o faltan datos imprescindibles). Nunca debe
            devolver hallazgos inventados o parciales como si fueran
            completos.
        """
        ...
