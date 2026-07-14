# Cómo agregar un nuevo proveedor de IA

Cubre la tarea "Dejar documentado (sin implementar aún si no es necesario
para el MVP) cómo se sumarían las integraciones restantes (Gemini,
Claude, OpenAI, Ollama) sin modificar la interfaz ni los agentes"
(TASKS.md, Fase 1, "Interfaz de proveedores de IA").

Este documento **no implementa** ninguna integración nueva: Anthropic
(`investmentops/ai_providers/anthropic_provider.py`) sigue siendo, por
ahora, la única integración concreta (ver PROGRESS.md). Su propósito es
dejar registrado el procedimiento para sumar Gemini, OpenAI y Ollama (o
cualquier proveedor futuro) cuando se necesiten, de forma que quien lo
haga no tenga que redescubrir el patrón ni, por error, termine
modificando el contrato (`investmentops.ai_providers.contracts`), el
mecanismo de selección (`investmentops.ai_providers.selection`) o
cualquier agente de análisis ya implementado.

## Por qué esto no requiere tocar la interfaz ni los agentes

`AIProvider` (ver `contracts.py`) es un `Protocol` estructural: cualquier
objeto con un método `complete(prompt, data=None) -> AIProviderResponse`
lo cumple, sin heredar de una clase base ni registrarse en ningún lugar
central. Los agentes de análisis (Fase 1, tareas "Agente de análisis:
salud financiera" y "Agente de análisis: valoración") reciben una
instancia que cumple ese contrato; no conocen ni les importa si por
dentro es Anthropic, Gemini, OpenAI u Ollama. Por eso agregar un
proveedor nuevo es un cambio puramente aditivo.

## Procedimiento (tomando `anthropic_provider.py` como plantilla)

1. **Crear un módulo nuevo** en `investmentops/ai_providers/`, por
   ejemplo `gemini_provider.py`, `openai_provider.py` u
   `ollama_provider.py`. No modificar `anthropic_provider.py` ni
   `contracts.py`.

2. **Implementar una clase con un método `complete`** con la misma
   firma que exige `AIProvider.complete` (`prompt: str`,
   `data: Mapping[str, Any] | None = None`) que devuelva
   `AIProviderResponse(content=..., provider=..., model=..., generated_at=...)`.
   El campo `provider` debe ser el identificador de texto libre que se
   usará como nombre de sección en `config.local.toml` (ej.
   `"gemini"`, `"openai"`, `"ollama"`), consistente con
   `ProviderMetadata.source` y con `[ai_providers.<nombre>]` en
   `config.example.toml` (ver CONFIGURATION.md).

3. **Resolver credenciales desde `config.local.toml` cuando no se
   pasan por argumento**, igual que `AnthropicAIProvider.__init__`:
   - `api_key` desde `[ai_providers.<nombre>]` (Ollama normalmente no
     la necesita, ya que corre localmente).
   - `base_url` desde `[ai_providers.<nombre>]`, con un valor por
     defecto razonable si no está configurado (ej. la URL local de
     Ollama, ya presente como ejemplo en `config.example.toml`:
     `http://localhost:11434`).
   - `model` desde `[ai_providers.default].model`, siguiendo el mismo
     criterio ya documentado en `selection.py` (no existe hoy un campo
     `model` por proveedor).
   - Si falta una credencial imprescindible (ej. `api_key` en Gemini u
     OpenAI), levantar `AIProviderError` en el constructor, nunca
     continuar con un valor inventado.

4. **Traducir cualquier fallo a `AIProviderError`**, nunca dejar
   escapar una excepción específica del SDK/HTTP del proveedor (de
   red, autenticación, límite de tasa, formato de respuesta
   inesperado, respuesta sin texto interpretable). Ver
   `anthropic_provider.py` para los casos mínimos a cubrir.

5. **No modificar `investmentops/ai_providers/selection.py`.** Ese
   módulo solo resuelve *qué nombre* de proveedor le corresponde a un
   agente (ej. `"gemini"`); no instancia ninguna clase concreta. Sumar
   un proveedor nuevo no cambia esa resolución.

6. **No modificar ningún agente de análisis.** Un agente recibe la
   instancia de `AIProvider` ya construida (por quien lo construye/
   registra, tarea de "Agente de análisis: salud financiera" /
   "valoración" en TASKS.md); no decide ni conoce qué proveedor es.

7. **(Opcional) Re-exportar la clase nueva** desde
   `investmentops/ai_providers/__init__.py`, siguiendo el mismo patrón
   ya usado — aunque esto no es estrictamente necesario, ya que nada
   impide importar `GeminiAIProvider` directamente desde su módulo.

8. **Escribir pruebas mockeando la llamada HTTP/SDK del proveedor**
   (nunca hacer una llamada de red real en las pruebas), siguiendo el
   mismo patrón de `investmentops/tests/test_ai_providers_anthropic.py`.

## Quién decide qué clase concreta instanciar

Ese paso — tomar el `provider` (texto) que devuelve
`resolve_agent_provider` y construir la clase `AIProvider` concreta
correspondiente (`AnthropicAIProvider`, `GeminiAIProvider`, etc.) — no
existe todavía como mecanismo genérico (ej. un mapeo
`{"anthropic": AnthropicAIProvider, ...}}`). Es responsabilidad de quien
construya cada agente de análisis (tareas pendientes "Agente de
análisis: salud financiera" y "Agente de análisis: valoración" en
TASKS.md), no de este módulo. Si en el futuro se agregan varios
proveedores y ese mapeo se repite en cada agente, extraerlo a una
función común sería una tarea de refactor explícita y posterior, no algo
a anticipar aquí.

## Fuera de alcance de este documento

- Implementar cualquiera de las integraciones (Gemini, OpenAI, Ollama):
  se hará como tarea separada solo si el MVP lo requiere.
- Un registro/factory central de proveedores de IA: no existe evidencia
  todavía de que se necesite antes de tener más de una integración
  concreta más allá de Anthropic.
