# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Interfaz de proveedores de IA → *"Implementar al menos una integración concreta (por ejemplo, un proveedor) que cumpla la interfaz."*, junto con *"Implementar manejo de error básico cuando el proveedor de IA no responde o devuelve un formato inesperado."* de la misma sección.

Antes de implementar, se verificó la tarea inmediatamente anterior de la misma sección — *"Implementar la interfaz común de proveedor de IA (envío de prompt + datos, recepción de respuesta + metadatos)."* — y se confirmó que ya estaba satisfecha: es la misma interfaz ya definida como el `Protocol` `AIProvider` en `investmentops/ai_providers/contracts.py` (tarea "Definir el contrato de 'AI provider'" de "Contratos e interfaces"). No había nada nuevo que implementar ahí, así que se marcó como completada sin escribir código duplicado y se continuó con la siguiente tarea real.

Las dos tareas efectivamente implementadas en esta conversación se hicieron en conjunto por el mismo motivo que llevó a implementar juntas las tareas equivalentes de "Fuente de datos fundamentales" (ver entrada anterior de este archivo): el contrato `AIProvider` ya exige, en su propia definición, que cualquier fallo se señale mediante `AIProviderError`; una integración "mínima" sin ese manejo de error dejaría escapar excepciones de `requests` e incumpliría el contrato ya definido en Fase 1.

## Qué se implementó

**`investmentops/ai_providers/anthropic_provider.py`** — nuevo módulo con la clase `AnthropicAIProvider`, que:

- Cumple el contrato `AIProvider` (método `complete(prompt, data=None) -> AIProviderResponse`).
- Invoca el endpoint de mensajes de Anthropic (`POST {base_url}/messages`), incorporando los datos estructurados opcionales (`data`) al mensaje de usuario como un bloque de JSON serializado anexado al prompt — la API de mensajes de Anthropic no tiene un campo separado para "datos estructurados", así que esta es la forma en que este proveedor concreto cumple esa parte del contrato.
- Extrae el texto de respuesta de los bloques de tipo `"text"` devueltos por la API y lo expone como `AIProviderResponse.content`, junto con `provider="anthropic"`, el modelo efectivamente usado (tomado de la respuesta de la API cuando está presente) y la fecha de generación.
- Lee `api_key` y (opcionalmente) `base_url` desde `config.local.toml`, sección `[ai_providers.anthropic]`, y el `model` desde `[ai_providers.default]` si no se indica explícitamente, usando `investmentops.config.load_config`; también acepta un diccionario de configuración inyectado (parámetro `config`) para pruebas, y `api_key`/`model`/`base_url` explícitos para uso directo. Si no hay modelo configurado, usa `DEFAULT_MODEL = "claude-sonnet-5"` como valor por defecto.
- Traduce a `AIProviderError` los siguientes casos de fallo: prompt vacío, datos no serializables a JSON, error de red/tiempo de espera, API key inválida o sin permisos (401/403), límite de tasa excedido (429), cualquier otro error HTTP ≥ 400, respuesta que no se puede interpretar como JSON, y respuesta sin contenido de texto interpretable. En ningún caso se propaga una excepción cruda de `requests` ni se devuelve una respuesta vacía o inventada como si fuera válida.

**`investmentops/tests/test_ai_providers_anthropic.py`** — pruebas que mockean `requests.post` (sin llamadas de red reales ni API key válida), cubriendo: cumplimiento del protocolo `AIProvider`, resultado exitoso con datos estructurados incorporados al mensaje, envío correcto de la API key y el prompt, `data` opcional, prompt vacío, fallo de red, error de autenticación, límite de tasa, error de servidor, JSON inválido, respuesta sin bloques de contenido, respuesta sin bloques de texto, y la resolución de credenciales/modelo (falta de API key, lectura desde config, valores por defecto).

## Decisiones tomadas

- **Primer proveedor de IA concreto: Anthropic.** Es el proveedor cuya sección de configuración (`[ai_providers.anthropic]`) y ejemplos de identificador de modelo (`"claude-sonnet-5"`) ya aparecían como ejemplo recurrente en la documentación existente (`ai_providers/contracts.py`, `config.example.toml`), y es consistente con el entorno en el que se está desarrollando este proyecto.
- **Cómo incorporar `data` al llamado:** dado que la API de mensajes de Anthropic no separa "prompt" de "datos estructurados" en su payload, `data` se serializa a JSON y se anexa como texto adicional al mensaje de usuario, en vez de intentar forzar una estructura que la API no soporta. Esto mantiene el contrato `AIProvider.complete(prompt, data=None)` sin modificarlo.
- **Resolución de `model`:** se lee de `[ai_providers.default].model` en vez de agregar un campo `model` a `[ai_providers.anthropic]`, para no adelantar trabajo de la tarea pendiente "Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local" (sección `[agents]`), que es una tarea separada y posterior.
- **Uso de `requests` en vez del SDK oficial de Anthropic.** Mismo criterio que con `FMPFundamentalsProvider`: una única dependencia HTTP ya presente en el proyecto, sin sumar un SDK adicional solo para tres campos de la API (`x-api-key`, `anthropic-version`, `content-type`).
- **No se implementó el mecanismo de selección de proveedor/modelo por agente ni la documentación de las integraciones restantes.** Ambas son tareas explícitas y separadas en `TASKS.md`, no parte de "implementar al menos una integración concreta".

## Archivos creados o modificados

Creados:
- `investmentops/ai_providers/anthropic_provider.py`
- `investmentops/tests/test_ai_providers_anthropic.py`

Modificados:
- `TASKS.md` (tarea "Implementar la interfaz común de proveedor de IA..." marcada como completada, con referencia inline a por qué ya estaba satisfecha; tareas "Implementar al menos una integración concreta..." e "Implementar manejo de error básico..." marcadas como completadas, con referencia inline a esta implementación)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `.python-version`, `pyproject.toml`, y el resto de `investmentops/` (código y tests) no mencionado arriba.

## Problemas encontrados

Ninguno. El contrato `AIProvider`/`AIProviderResponse`/`AIProviderError` ya definido en Fase 1 ("Contratos e interfaces") encajó sin fricción con esta integración concreta.

## Próxima tarea recomendada

Con la primera integración concreta de IA lista, las siguientes tareas pendientes en `TASKS.md`, sección "Interfaz de proveedores de IA", son:

1. *"Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local."* — probablemente consiste en implementar una función que, dado un identificador de agente (ej. `"financial_health"`) y la configuración ya cargada, resuelva qué sección de `[ai_providers.*]` y qué modelo usar, mirando primero `[agents]` y cayendo de vuelta a `[ai_providers.default]` si el agente no aparece ahí (ver CONFIGURATION.md).
2. *"Dejar documentado (sin implementar aún si no es necesario para el MVP) cómo se sumarían las integraciones restantes (Gemini, Claude, OpenAI, Ollama) sin modificar la interfaz ni los agentes."* — es una tarea de documentación, no de código.

Nota para la próxima conversación:
- Ambas tareas restantes de esta sección no requieren un nuevo proveedor de datos ni tocar `AnthropicAIProvider`; son trabajo de "cableado" de configuración y documentación, respectivamente.
- Con esas dos tareas completas, la sección "Interfaz de proveedores de IA" quedaría cerrada por completo, dejando el proyecto listo para empezar "Normalización y almacenamiento" (la siguiente sección sin marcar en `TASKS.md`).
