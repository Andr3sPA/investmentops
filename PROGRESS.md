# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'data provider' (entrada: ticker; salida: datos crudos + metadatos de procedencia)."*

## Cambios realizados

- Se creó `investmentops/data_providers/contracts.py`, que define el contrato común que debe cumplir todo proveedor de datos (ver ARCHITECTURE.md, componente 3):
  - `DataProviderError`: excepción común para señalar cualquier fallo del proveedor (no responde, ticker inexistente, formato inesperado), de forma que el orquestador pueda capturarla y continuar con las demás fuentes en vez de detener todo el flujo o devolver datos inventados.
  - `ProviderMetadata`: dataclass inmutable con los metadatos de procedencia exigidos por `ARCHITECTURE.md` — `source` (fuente), `queried_at` (fecha/hora de consulta) y `reliability` (confiabilidad, texto libre).
  - `RawProviderData`: dataclass inmutable que agrupa `ticker`, `payload` (datos crudos sin normalizar, forma libre) y `metadata` (`ProviderMetadata`). Es el tipo de salida que todo proveedor debe devolver.
  - `DataProvider`: `Protocol` (tipado estructural, `runtime_checkable`) con un único método `fetch(ticker: str) -> RawProviderData`. Cualquier objeto que exponga ese método cumple el contrato, sin necesidad de heredar de una clase base concreta.
- Se actualizó `investmentops/data_providers/__init__.py` para re-exportar `DataProvider`, `DataProviderError`, `ProviderMetadata` y `RawProviderData` desde `contracts.py`, de forma que el resto del sistema los importe directamente desde `investmentops.data_providers`.
- Se agregó `tests/test_data_providers_contracts.py`, con un proveedor mínimo de prueba (`_DummyProvider`) que cumple el contrato y otro que falla (`_FailingProvider`), cubriendo: cumplimiento del protocolo `DataProvider`, forma del resultado (`RawProviderData` + `ProviderMetadata`), propagación de `DataProviderError`, e inmutabilidad de ambas dataclasses.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/contracts.py`
- `tests/test_data_providers_contracts.py`

Modificados:
- `investmentops/data_providers/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `investmentops/config/__init__.py`, `investmentops/__main__.py`, `investmentops/__init__.py`, `tests/test_environment.py`, `tests/test_config.py`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `data_layer`, `analysis_engines`, `ai_providers`, `reports`), que siguen sin implementación.

No se implementó ningún proveedor concreto (eso corresponde a la sección "Fuente de datos fundamentales" de `TASKS.md`, tarea posterior): este trabajo solo define el contrato/interfaz.

## Decisiones técnicas importantes

- **`Protocol` (tipado estructural) en vez de una clase base abstracta (`ABC`)**: un proveedor concreto solo necesita exponer un método `fetch(ticker) -> RawProviderData` con esa firma; no necesita heredar explícitamente de una clase base. Esto es coherente con el principio de `ARCHITECTURE.md` de que "el orquestador conoce interfaces, no implementaciones concretas", sin forzar una jerarquía de herencia sobre proveedores futuros (fundamentales, mercado, noticias, comparables) que pueden tener formas de implementación muy distintas (cliente HTTP, SDK, lectura de caché, etc.).
- **`runtime_checkable`**: permite usar `isinstance(proveedor, DataProvider)` como verificación ligera en pruebas o en el futuro mecanismo de registro del orquestador, sin convertir el contrato en una clase concreta que haya que instanciar o heredar.
- **`payload: Any` en `RawProviderData`**: el contrato deliberadamente no impone una forma fija a los datos crudos, porque cada proveedor (fundamentales, mercado, noticias, comparables) devuelve algo distinto y la normalización a un modelo común es responsabilidad de `investmentops.data_layer`, no de este contrato. Fijar aquí una forma específica habría acoplado el contrato genérico a la fuente de la Fase 1.
- **`ProviderMetadata` con `source`, `queried_at` y `reliability`**: son exactamente los tres campos que `ARCHITECTURE.md` exige para "metadatos de procedencia" (componente 3: *"fuente, fecha de consulta, confiabilidad"*). No se agregó ningún campo adicional (ej. `raw_response_id`, `latency_ms`) para no anticipar necesidades que ninguna tarea actual pide.
- **`reliability` como texto libre, no un enum cerrado**: distintos proveedores (fundamentales vs. noticias vs. comparables) pueden necesitar describir la confiabilidad de forma distinta (ej. "dato oficial" vs. "estimado por consenso de analistas"). Cerrar esto a un enum ahora habría anticipado un diseño que ninguna tarea actual exige; queda documentado en el docstring como una decisión abierta a revisar cuando exista un proveedor concreto.
- **Dataclasses `frozen=True` (inmutables)**: una vez que un proveedor entrega `RawProviderData`, ni el orquestador ni la capa de normalización deberían poder mutarlo por accidente antes de transformarlo al modelo de dominio; esto refuerza la trazabilidad exigida por `ARCHITECTURE.md` ("Reproducibilidad y trazabilidad").
- **`DataProviderError` hereda de `RuntimeError`, no de `Exception` directamente**: mantiene el mismo patrón ya usado en `investmentops.config.ConfigError`, dejando `Exception` para errores realmente inesperados y `RuntimeError` para fallos operacionales esperables (proveedor caído, ticker inexistente) que el orquestador debe poder anticipar y capturar explícitamente.
- **Sin manejo de reintentos, timeouts ni caché en el contrato**: eso es responsabilidad de la implementación concreta de cada proveedor (tarea "Fuente de datos fundamentales") y de `investmentops.data_layer` (caché), no del contrato en sí, conforme a la separación de capas de `ARCHITECTURE.md`.

## Problemas encontrados

Ninguno. Se verificó manualmente que:
- Un proveedor mínimo que implementa `fetch(ticker) -> RawProviderData` satisface `isinstance(proveedor, DataProvider)`.
- `RawProviderData` y `ProviderMetadata` son inmutables (intentar reasignar un atributo lanza `AttributeError`).
- Un proveedor que levanta `DataProviderError` propaga el error correctamente y con su mensaje.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'analysis engine' / agente de IA (entrada: modelo de dominio normalizado + métricas precalculadas cuando aplique; salida: resultado estructurado)."*
