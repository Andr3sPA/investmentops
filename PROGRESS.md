# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Fuente de datos fundamentales → *"Implementar un cliente mínimo que consulte ese proveedor y obtenga datos crudos de una empresa por ticker."*, junto con las dos tareas siguientes de la misma sección: *"Adjuntar metadatos de procedencia..."* e *"Implementar manejo de error básico..."*.

Las tres tareas se implementaron en conjunto porque son inseparables para producir un `DataProvider` funcional: el contrato `RawProviderData` (`investmentops.data_providers.contracts`) exige `metadata` en su propia definición, por lo que ningún cliente "mínimo" puede devolver datos sin adjuntar procedencia; y sin manejo de error básico, cualquier fallo de red dejaría escapar una excepción de `requests` en vez de `DataProviderError`, incumpliendo el contrato ya definido en Fase 1 ("Contratos e interfaces").

## Qué se implementó

**`investmentops/data_providers/fundamentals.py`** — nuevo módulo con la clase `FMPFundamentalsProvider`, que:

- Cumple el contrato `DataProvider` (método `fetch(ticker) -> RawProviderData`).
- Consulta tres endpoints de Financial Modeling Prep (FMP) por ticker: estado de resultados (`/income-statement/{ticker}`), balance general (`/balance-sheet-statement/{ticker}`) y cotización (`/quote/{ticker}`), y combina sus respuestas crudas (sin transformar) en un único `payload` con esas tres claves. Esto da suficiente información cruda para las transformaciones futuras a `FinancialStatement` (ingresos, beneficios, deuda) y `MarketData` (precio, capitalización, múltiplos), sin que este cliente decida qué campos usar — esa decisión es de `investmentops.data_layer` (tarea posterior).
- Adjunta `ProviderMetadata(source="fmp", queried_at=<ahora, UTC>, reliability="alta")` a cada `RawProviderData` devuelto.
- Lee la API key y (opcionalmente) la URL base desde `config.local.toml`, sección `[data_providers.fundamentals]`, usando `investmentops.config.load_config`; también acepta un diccionario de configuración inyectado (parámetro `config`) para pruebas, y `api_key`/`base_url` explícitos para uso directo.
- Traduce a `DataProviderError` los siguientes casos de fallo: ticker vacío, error de red/tiempo de espera al llamar a FMP, API key inválida o sin permisos (401/403), cualquier otro error HTTP ≥ 400, respuesta que no se puede interpretar como JSON, y ticker inexistente (cuando FMP no devuelve datos ni en el estado de resultados ni en la cotización). En ningún caso se propaga una excepción cruda de `requests` ni se devuelven datos parciales/inventados como si fueran válidos.

**`investmentops/tests/test_data_providers_fundamentals.py`** — pruebas que mockean `requests.get` (sin llamadas de red reales ni API key válida), cubriendo: cumplimiento del protocolo `DataProvider`, resultado exitoso con los tres endpoints combinados y metadatos correctos, envío de la API key como query param, ticker inexistente, fallo de red, error de autenticación, error de servidor, respuesta JSON inválida, ticker vacío, y la resolución de credenciales (falta de API key, lectura desde config, uso de la URL base por defecto).

## Decisiones tomadas

- **Dependencia HTTP: `requests`.** Se eligió sobre `httpx` por ser la opción más simple y estándar para un cliente síncrono de tres llamadas GET; no se necesita soporte async en esta fase. Se agregó `requests>=2.31` a `dependencies` en `pyproject.toml` (antes vacío).
- **Combinar tres endpoints en un único `payload`, en vez de tres llamadas `fetch()` separadas.** El contrato `DataProvider.fetch(ticker)` devuelve un único `RawProviderData` por ticker; separar en tres llamadas habría obligado a introducir tres "proveedores" distintos (uno por endpoint) o a cambiar el contrato, ninguno de los cuales es necesario para lo que exige esta tarea ("obtener datos crudos de una empresa por ticker", en singular).
- **Criterio de "ticker no existe":** se interpreta como que FMP no devolvió datos ni en el estado de resultados ni en la cotización (ambas listas vacías). Es una heurística simple, consistente con el alcance de "manejo de error básico" de esta tarea; un refinamiento posterior (ej. distinguir explícitamente "ticker no encontrado" de "empresa sin datos financieros recientes") no está en el alcance de la Fase 1.
- **No se implementó caché ni reintentos.** Ambos son responsabilidad de tareas posteriores explícitas en `TASKS.md` ("Normalización y almacenamiento") y no forman parte de un cliente "mínimo".

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/fundamentals.py`
- `investmentops/tests/test_data_providers_fundamentals.py`

Modificados:
- `pyproject.toml` (se agregó `requests>=2.31` a `dependencies`)
- `TASKS.md` (las tres tareas de "Fuente de datos fundamentales" restantes marcadas como completadas, con referencia inline a esta implementación)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `.python-version`, y el resto de `investmentops/` (código y tests) no mencionado arriba.

## Problemas encontrados

Ninguno. La estructura de `RawProviderData`/`ProviderMetadata`/`DataProviderError` ya definida en Fase 1 ("Contratos e interfaces") encajó sin fricción con el cliente concreto.

## Próxima tarea recomendada

Con toda la sección "Fuente de datos fundamentales" completa, la siguiente sección pendiente en `TASKS.md` es **"Interfaz de proveedores de IA"**, empezando por:

*"Implementar la interfaz común de proveedor de IA (envío de prompt + datos, recepción de respuesta + metadatos)."*

Nota para la próxima conversación:
- El contrato ya existe (`investmentops.ai_providers.contracts.AIProvider`, definido en la sección "Contratos e interfaces" de esta misma fase), así que esta tarea probablemente consiste en confirmar/documentar que ese contrato es la "interfaz común" exigida, o bien en preparar el mecanismo de registro/selección de proveedor concreto (sin implementar todavía una integración real, que es la tarea siguiente: "Implementar al menos una integración concreta").
- La tarea inmediatamente siguiente, "Implementar al menos una integración concreta (por ejemplo, un proveedor) que cumpla la interfaz", es la que requerirá elegir un proveedor de IA concreto (Anthropic, Gemini, OpenAI u Ollama) para el MVP y su respectiva API key en `config.local.toml`, sección `[ai_providers.<nombre>]` (ya prevista en `config.example.toml`).
- Como con el cliente de FMP, cualquier prueba de una integración de IA concreta deberá mockear la llamada HTTP/SDK en vez de depender de una API key real o de una llamada de red.
