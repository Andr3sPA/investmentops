# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'AI provider' (entrada: prompt + datos estructurados; salida: respuesta del modelo + metadatos de proveedor/modelo usado), común para Gemini, Claude, OpenAI y Ollama."*

## Cambios realizados

- Se creó `investmentops/ai_providers/contracts.py`, que define el contrato común que debe cumplir toda integración de proveedor de IA (ver ARCHITECTURE.md, componente 5bis):
  - `AIProviderError`: excepción común para señalar cualquier fallo del proveedor (no responde, error de autenticación, límite de tasa excedido, respuesta en formato inesperado), de forma que quien invoca la interfaz (típicamente un agente de `investmentops.analysis_engines`) pueda capturarla y traducirla a su propia `AnalysisEngineError`, sin detener el resto del flujo de investigación.
  - `AIProviderResponse`: dataclass inmutable con `content` (texto de respuesta del modelo, sin procesar), `provider`, `model` y `generated_at` — la base con la que un agente construye su propia `AnalysisProvenance` (ver `investmentops.analysis_engines.contracts`).
  - `AIProvider`: `Protocol` (tipado estructural, `runtime_checkable`) con un único método `complete(prompt, data=None) -> AIProviderResponse`. Cualquier objeto que exponga ese método cumple el contrato, sin necesidad de heredar de una clase base concreta.
- Se actualizó `investmentops/ai_providers/__init__.py` para re-exportar `AIProvider`, `AIProviderError` y `AIProviderResponse` desde `contracts.py`, de forma que el resto del sistema los importe directamente desde `investmentops.ai_providers`. También se documentaron ahí las tareas siguientes de esta misma sección (implementación concreta, selección de proveedor/modelo por agente, manejo de error).
- Se agregó `investmentops/tests/test_ai_providers_contracts.py`, con un proveedor mínimo de prueba (`_DummyProvider`) que cumple el contrato y otro que falla (`_FailingProvider`), cubriendo: cumplimiento del protocolo `AIProvider`, forma de la respuesta (`AIProviderResponse`), el carácter opcional del parámetro `data`, propagación de `AIProviderError`, e inmutabilidad de la dataclass de respuesta.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/ai_providers/contracts.py`
- `investmentops/tests/test_ai_providers_contracts.py`

Modificados:
- `investmentops/ai_providers/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `investmentops/config/__init__.py`, `investmentops/__main__.py`, `investmentops/__init__.py`, `investmentops/data_providers/__init__.py`, `investmentops/data_providers/contracts.py`, `investmentops/analysis_engines/__init__.py`, `investmentops/analysis_engines/contracts.py`, `investmentops/tests/test_environment.py`, `investmentops/tests/test_config.py`, `investmentops/tests/test_data_providers_contracts.py`, `investmentops/tests/test_analysis_engines_contracts.py`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `data_layer`, `reports`), que siguen sin implementación.

No se implementó ninguna integración concreta de proveedor de IA (Anthropic, Gemini, OpenAI, Ollama): eso corresponde a las tareas siguientes de la sección "Interfaz de proveedores de IA" en `TASKS.md`. Este trabajo solo define el contrato/interfaz.

## Decisiones técnicas importantes

- **Mismo patrón que `investmentops.data_providers.contracts` y `investmentops.analysis_engines.contracts`**: `Protocol` + `runtime_checkable`, una dataclass `frozen=True` para la respuesta, y una excepción propia (`AIProviderError`) heredando de `RuntimeError`. Mantener el mismo patrón entre los tres contratos reduce la carga cognitiva al leer el código y refuerza el principio de `ARCHITECTURE.md` de que quien invoca conoce interfaces, no implementaciones concretas.
- **Un único método `complete(prompt, data=None)`** en vez de separar "enviar prompt" y "enviar datos" en dos pasos: `ARCHITECTURE.md` describe la entrada como "prompt + datos estructurados + parámetros básicos" en una sola llamada, y esto es lo que un agente de análisis necesita: una invocación atómica que reciba su prompt (cargado desde `prompts/`) junto con las métricas ya calculadas.
- **`data: Mapping[str, Any] | None = None`**: se deja opcional porque no toda invocación necesita datos estructurados adicionales al prompt (por ejemplo, un futuro agente de reporte podría enviar solo texto ya compuesto). El contrato no impone estructura sobre `data`; cada proveedor concreto decide cómo incorporarlo a su llamada (ej. interpolarlo en el prompt final, o enviarlo como bloque de contexto separado según la API del proveedor).
- **`content: str` sin estructura forzada**: igual que `RawProviderData.payload` y `company_data` en los otros dos contratos, el texto de respuesta se deja como texto plano sin parsear. La interpretación de ese texto a hallazgos estructurados es responsabilidad de cada agente concreto (ver `investmentops.analysis_engines`), no de esta interfaz transversal.
- **`AIProviderError` separado de `DataProviderError` y `AnalysisEngineError`**: mantener los tres tipos distintos permite que, más adelante, un agente de análisis distinga en su propio manejo de errores si el fallo vino de invocar al proveedor de IA (`AIProviderError`, que el agente captura y traduce a su propia `AnalysisEngineError`) o de otra causa (datos de entrada faltantes, por ejemplo), sin mezclar responsabilidades entre capas.
- **Sin mecanismo de reintentos, streaming, ni parámetros de modelo (temperatura, máximo de tokens, etc.) en el contrato**: `ARCHITECTURE.md` menciona "parámetros básicos" pero no los especifica; se dejan fuera de este contrato mínimo para no comprometer una API concreta antes de implementar la primera integración real. Si resultan necesarios, se agregarán como argumentos opcionales de `complete` en la tarea de implementación, sin romper este contrato base (los proveedores concretos seguirían cumpliendo la misma firma mínima).
- **Sin manejo de selección de proveedor/modelo por agente en este módulo**: ese mecanismo consume `config.local.toml` (sección `[agents]`, ver `CONFIGURATION.md`) y es una tarea separada y posterior ("Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local"), no algo que el contrato en sí deba resolver.

## Problemas encontrados

Ninguno. Se verificó manualmente que:
- Un proveedor mínimo que implementa `complete(prompt, data=None) -> AIProviderResponse` satisface `isinstance(proveedor, AIProvider)`.
- `AIProviderResponse` es inmutable (intentar reasignar un atributo lanza `AttributeError`).
- Un proveedor que levanta `AIProviderError` propaga el error correctamente y con su mensaje.
- El parámetro `data` es efectivamente opcional: al omitirlo, el proveedor de prueba responde igual usando solo el prompt.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir la estructura del modelo de dominio 'Empresa' (ticker, nombre, sector, mercado)."*
