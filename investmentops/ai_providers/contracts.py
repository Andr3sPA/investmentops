"""Contrato de "AI Provider" (Interfaz de proveedores de IA).

Ver ARCHITECTURE.md, componente 5bis ("Interfaz de proveedores de IA"), y
TASKS.md, Fase 1, sección "Contratos e interfaces": *"Definir el contrato
de 'AI provider' (entrada: prompt + datos estructurados; salida: respuesta
del modelo + metadatos de proveedor/modelo usado), común para Gemini,
Claude, OpenAI y Ollama."*

Este módulo NO implementa ninguna integración concreta con un proveedor de
IA (eso es una tarea posterior, ver TASKS.md, sección "Interfaz de
proveedores de IA"). Solo define el contrato que toda integración debe
cumplir, de forma que:

- Los agentes de análisis (investmentops.analysis_engines) y, más
  adelante, el agente de reporte (investmentops.reports) puedan invocar
  cualquier proveedor de IA sin conocer su implementación concreta ni su
  SDK específico.
- Agregar un nuevo proveedor de IA (o un modelo adicional dentro de un
  proveedor ya soportado) no requiera modificar los agentes que lo
  invocan ni el orquestador (ver ARCHITECTURE.md, "Extensibilidad").
- El proveedor/modelo usado por cada agente pueda cambiarse mediante
  configuración local (`config.local.toml`, sección `[agents]`, ver
  CONFIGURATION.md), sin tocar código.

Resumen del contrato (ver ARCHITECTURE.md, componente 5bis):

- **Entrada:** un prompt (texto de instrucciones, cargado desde un archivo
  independiente por el agente que invoca, ver `prompts/README.md`) y datos
  estructurados (ej. métricas ya calculadas de forma determinística) que
  el proveedor debe incorporar a la llamada al modelo de lenguaje.
- **Salida:** el texto de respuesta del modelo, junto con metadatos de
  procedencia: qué proveedor y qué modelo concreto se usó, y cuándo se
  generó la respuesta. Esto es lo que permite a un agente de análisis
  construir la `AnalysisProvenance` de su propio `AnalysisResult` (ver
  investmentops.analysis_engines.contracts) sin necesidad de conocer
  detalles internos del proveedor de IA.
- **Fallos:** un proveedor que no puede completar la llamada (no responde,
  error de autenticación, límite de tasa excedido, respuesta en un formato
  inesperado) debe señalarlo mediante `AIProviderError`, nunca devolviendo
  una respuesta vacía o inventada como si fuera válida. Igual que con
  `DataProviderError` y `AnalysisEngineError`, esto es lo que le permite a
  quien invoca (un agente de análisis) señalar su propio fallo mediante
  `AnalysisEngineError` en vez de propagar un resultado incompleto o
  fallar de forma opaca.

Fuera de alcance de este módulo:
- Cualquier implementación concreta de proveedor (llamadas HTTP a la API
  de Anthropic, Gemini, OpenAI, o al runtime local de Ollama): eso
  corresponde a la tarea "Implementar al menos una integración concreta"
  (ver TASKS.md, sección "Interfaz de proveedores de IA").
- El mecanismo de selección de proveedor/modelo por agente vía
  configuración local: ese mecanismo consume `config.local.toml` (ver
  CONFIGURATION.md) y es responsabilidad de quien construye/registra cada
  agente, no de este contrato.
- El parseo de la respuesta del modelo a la estructura de `AnalysisResult`
  de un agente concreto: este contrato solo entrega el texto crudo de
  respuesta (`content`) más sus metadatos; interpretar ese texto (ej.
  extraer hallazgos estructurados) es responsabilidad de cada agente (ver
  investmentops.analysis_engines).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable


class AIProviderError(RuntimeError):
    """Error al invocar un proveedor de IA.

    Cubre cualquier fallo que impida obtener una respuesta completa y
    confiable del modelo de lenguaje: el proveedor no responde (caído,
    tiempo de espera agotado), un error de autenticación (API key
    inválida o ausente), un límite de tasa excedido, o una respuesta en un
    formato que no se puede interpretar como texto. Quien invoca esta
    interfaz (típicamente un agente de investmentops.analysis_engines)
    captura este tipo de excepción para señalar su propio fallo mediante
    `AnalysisEngineError`, sin detener el resto del flujo de investigación
    (ver ARCHITECTURE.md, "Manejo de errores y limitaciones").
    """


@dataclass(frozen=True)
class AIProviderResponse:
    """Respuesta estructurada que produce todo proveedor de IA.

    Este es el tipo de salida común a toda integración de proveedor de IA
    (ver ARCHITECTURE.md, componente 5bis). Un agente de análisis consume
    esta respuesta para construir su propio `AnalysisResult`, tomando
    `content` como la interpretación en lenguaje natural a parsear, y
    `provider`/`model`/`generated_at` como base de su `AnalysisProvenance`
    (ver investmentops.analysis_engines.contracts).

    Attributes
    ----------
    content:
        El texto de respuesta devuelto por el modelo de lenguaje, sin
        procesar. Quien invoca la interfaz es responsable de interpretar
        este texto según sus propias necesidades (ej. un agente de
        análisis lo parsea a hallazgos estructurados); este contrato no
        impone ninguna estructura sobre su contenido.
    provider:
        Identificador del proveedor de IA que generó la respuesta (ej.
        ``"anthropic"``, ``"gemini"``, ``"openai"``, ``"ollama"``), tal
        como se configura en `config.local.toml` bajo
        `[ai_providers.<nombre>]` (ver CONFIGURATION.md).
    model:
        Identificador del modelo concreto usado dentro de ese proveedor
        (ej. ``"claude-sonnet-5"``).
    generated_at:
        Fecha y hora en que se generó esta respuesta.
    """

    content: str
    provider: str
    model: str
    generated_at: datetime


@runtime_checkable
class AIProvider(Protocol):
    """Contrato común que debe cumplir toda integración de proveedor de IA.

    Cualquier módulo bajo investmentops.ai_providers que implemente este
    contrato puede ser invocado por un agente de análisis (o, más
    adelante, por el agente de reporte) sin que quien lo invoca conozca su
    implementación concreta ni el SDK específico del proveedor (ver
    ARCHITECTURE.md, "Regla de dependencia" y "Independencia del
    proveedor de IA").

    Se define como `Protocol` (tipado estructural, `runtime_checkable`),
    igual que `DataProvider` y `AnalysisEngine`: cualquier objeto que
    exponga un método `complete` con esta firma cumple el contrato, sin
    necesidad de heredar de una clase concreta. Esto deja abierta la
    implementación de cada integración (Anthropic, Gemini, OpenAI, Ollama)
    para las tareas correspondientes en TASKS.md.
    """

    def complete(
        self,
        prompt: str,
        data: Mapping[str, Any] | None = None,
    ) -> AIProviderResponse:
        """Invoca al modelo de lenguaje con un prompt y datos estructurados.

        Parameters
        ----------
        prompt:
            Texto de instrucciones para el modelo, cargado por quien
            invoca desde un archivo de prompt independiente (ver
            `prompts/README.md`). Este contrato no impone ningún formato
            sobre el prompt: es texto plano tal como lo entrega el agente
            que lo invoca.
        data:
            Datos estructurados que el proveedor debe incorporar a la
            llamada (ej. métricas ya calculadas de forma determinística
            por un agente de análisis). Es opcional porque no toda llamada
            requiere datos adicionales al prompt (ej. un agente de reporte
            podría enviar únicamente texto ya compuesto).

        Returns
        -------
        AIProviderResponse
            La respuesta del modelo, junto con metadatos de qué
            proveedor/modelo la generó y cuándo.

        Raises
        ------
        AIProviderError
            Si el proveedor no responde, falla la autenticación, se
            excede un límite de tasa, o la respuesta no se puede
            interpretar como texto. Nunca debe devolver una respuesta
            vacía o inventada como si fuera válida.
        """
        ...
