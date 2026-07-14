"""Integración concreta con Anthropic — implementación de `AIProvider`.

Cubre las tareas de TASKS.md, Fase 1, "Interfaz de proveedores de IA":

- "Implementar al menos una integración concreta (por ejemplo, un
  proveedor) que cumpla la interfaz."
- "Implementar manejo de error básico cuando el proveedor de IA no
  responde o devuelve un formato inesperado."

Ambas tareas se implementan en conjunto por el mismo motivo que llevó a
implementar juntas las tareas equivalentes de "Fuente de datos
fundamentales" (ver `investmentops/data_providers/fundamentals.py` y
PROGRESS.md): el contrato `AIProvider`
(investmentops.ai_providers.contracts) exige que cualquier fallo se
señale mediante `AIProviderError`, nunca devolviendo una respuesta vacía
o inventada; no es posible entregar una integración "mínima" funcional
sin ese manejo de error, porque sin él cualquier fallo de red o de
formato dejaría escapar una excepción de `requests` incumpliendo el
contrato ya definido en Fase 1.

Este módulo implementa el contrato `AIProvider`: recibe un prompt (texto)
y datos estructurados opcionales, invoca la API de mensajes de Anthropic
(`POST /v1/messages`), y devuelve una `AIProviderResponse` con el texto
de respuesta y los metadatos de procedencia (proveedor, modelo, fecha).
No interpreta ni parsea el contenido de la respuesta más allá de extraer
el texto: esa interpretación (ej. a `AnalysisResult`) es responsabilidad
de quien invoca esta interfaz (un agente de investmentops.analysis_engines,
ver TASKS.md, "Agente de análisis: salud financiera" y "Agente de
análisis: valoración").

Fuera de alcance de este módulo:
- El mecanismo de selección de proveedor/modelo por agente vía
  configuración local (`config.local.toml`, sección `[agents]`): eso es
  una tarea separada y posterior (ver TASKS.md, "Interfaz de proveedores
  de IA" > "Definir el mecanismo de selección de proveedor/modelo por
  agente vía configuración local").
- Las integraciones restantes (Gemini, OpenAI, Ollama): quedan
  documentadas como pendientes en TASKS.md, no implementadas aquí.
- Streaming de respuestas, uso de herramientas (tool use), o cualquier
  característica de la API de Anthropic más allá de una llamada simple de
  prompt + datos -> texto de respuesta, que es todo lo que exige el
  contrato `AIProvider` en esta fase.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

import requests

from investmentops.ai_providers.contracts import AIProviderError, AIProviderResponse
from investmentops.config import load_config

DEFAULT_BASE_URL = "https://api.anthropic.com/v1"
DEFAULT_MODEL = "claude-sonnet-5"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicAIProvider:
    """Proveedor de IA que cumple el contrato `AIProvider` usando Anthropic.

    Ver investmentops.ai_providers.contracts.AIProvider: cualquier objeto
    con un método `complete(prompt, data=None) -> AIProviderResponse`
    cumple el contrato de forma estructural (`Protocol`), sin necesidad de
    heredar de una clase base. Esta clase es una implementación concreta
    de ese contrato para Anthropic, elegido como el primer proveedor de
    IA soportado (ver PROGRESS.md).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        *,
        config: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> None:
        """Crea el proveedor, resolviendo credenciales desde argumentos o config.

        Parameters
        ----------
        api_key:
            API key de Anthropic. Si no se indica, se intenta leer desde
            `config.local.toml`, sección `[ai_providers.anthropic]` (ver
            CONFIGURATION.md).
        model:
            Identificador del modelo a usar (ej. ``"claude-sonnet-5"``).
            Si no se indica, se intenta leer desde
            `[ai_providers.default]` en la configuración; si tampoco está
            ahí, se usa `DEFAULT_MODEL`. La selección de modelo por
            agente (`[agents]`) es una tarea separada (ver TASKS.md).
        base_url:
            URL base de la API de Anthropic. Si no se indica, se intenta
            leer desde `[ai_providers.anthropic]`; si tampoco está ahí,
            se usa `DEFAULT_BASE_URL`.
        config:
            Diccionario de configuración ya cargado (como el que devuelve
            `investmentops.config.load_config`). Útil para pruebas, para
            no depender de un `config.local.toml` real en disco. Si no se
            indica y falta algún dato, se llama a `load_config()`.
        timeout:
            Tiempo máximo (segundos) de espera por solicitud HTTP.
        """
        if api_key is None or base_url is None or model is None:
            cfg = config if config is not None else load_config()
            ai_providers_cfg = cfg.get("ai_providers", {})
            anthropic_cfg = ai_providers_cfg.get("anthropic", {})
            default_cfg = ai_providers_cfg.get("default", {})
            api_key = api_key or anthropic_cfg.get("api_key")
            base_url = base_url or anthropic_cfg.get("base_url")
            model = model or default_cfg.get("model")

        if not api_key:
            raise AIProviderError(
                "Falta la API key de Anthropic. Configúrala en "
                "config.local.toml, sección [ai_providers.anthropic] "
                "(ver CONFIGURATION.md)."
            )

        self._api_key = api_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._model = model or DEFAULT_MODEL
        self._timeout = timeout

    def complete(
        self,
        prompt: str,
        data: Mapping[str, Any] | None = None,
    ) -> AIProviderResponse:
        """Invoca a Anthropic con un prompt y datos estructurados opcionales.

        Los datos estructurados (`data`), si se entregan, se serializan a
        JSON y se anexan al texto del prompt como parte del único mensaje
        de usuario enviado al modelo: la API de mensajes de Anthropic no
        tiene un campo separado para "datos estructurados", por lo que
        incorporarlos al texto del mensaje es la forma en que este
        proveedor cumple con la parte de "datos estructurados" del
        contrato `AIProvider.complete`.

        Raises
        ------
        AIProviderError
            Si el prompt está vacío, los datos no se pueden serializar,
            Anthropic no responde (error de red), la API key es
            inválida, se excede el límite de tasa, o la respuesta no se
            puede interpretar. Nunca devuelve una respuesta vacía o
            inventada como si fuera válida.
        """
        if not prompt or not prompt.strip():
            raise AIProviderError("El prompt no puede estar vacío.")

        message_content = prompt
        if data:
            try:
                serialized_data = json.dumps(
                    data, ensure_ascii=False, indent=2, default=str
                )
            except TypeError as exc:
                raise AIProviderError(
                    f"Los datos proporcionados no se pudieron serializar a "
                    f"JSON: {exc}"
                ) from exc
            message_content = f"{prompt}\n\nDatos:\n{serialized_data}"

        url = f"{self._base_url}/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": self._model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": message_content}],
        }

        try:
            response = requests.post(
                url, headers=headers, json=body, timeout=self._timeout
            )
        except requests.RequestException as exc:
            raise AIProviderError(
                f"No se pudo contactar al proveedor de IA Anthropic: {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise AIProviderError(
                "Anthropic rechazó la solicitud (API key inválida o sin "
                "permisos)."
            )
        if response.status_code == 429:
            raise AIProviderError(
                "Anthropic respondió con un límite de tasa excedido (429)."
            )
        if response.status_code >= 400:
            raise AIProviderError(
                f"Anthropic respondió con un error ({response.status_code})."
            )

        try:
            response_json = response.json()
        except ValueError as exc:
            raise AIProviderError(
                "Anthropic devolvió una respuesta que no se pudo "
                "interpretar como JSON."
            ) from exc

        content_blocks = response_json.get("content")
        if not content_blocks:
            raise AIProviderError(
                "Anthropic devolvió una respuesta sin contenido "
                "interpretable."
            )

        text_parts = [
            block.get("text", "")
            for block in content_blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        content_text = "".join(text_parts).strip()
        if not content_text:
            raise AIProviderError(
                "Anthropic devolvió una respuesta sin texto interpretable."
            )

        return AIProviderResponse(
            content=content_text,
            provider="anthropic",
            model=response_json.get("model", self._model),
            generated_at=datetime.now(timezone.utc),
        )
