# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Interfaz de proveedores de IA → *"Dejar documentado (sin implementar aún si no es necesario para el MVP) cómo se sumarían las integraciones restantes (Gemini, Claude, OpenAI, Ollama) sin modificar la interfaz ni los agentes."*

Antes de implementar, se verificó que esta tarea no estuviera ya satisfecha por trabajo previo: `ARCHITECTURE.md` (sección "Extensibilidad") ya menciona en términos generales que un nuevo proveedor de IA "se agrega implementando el contrato de la interfaz... y registrándose en la configuración", pero eso es una afirmación de principio arquitectónico, no un procedimiento concreto tomando como referencia la única integración real ya existente (`AnthropicAIProvider`). Ningún documento explicaba, paso a paso, qué archivo crear, qué patrón seguir (resolución de credenciales, manejo de error) ni qué módulos NO se deben tocar (`contracts.py`, `selection.py`, los agentes). Se confirmó que requería trabajo nuevo — puramente de documentación, sin código — y se implementó.

## Qué se implementó

**`investmentops/ai_providers/EXTENDING.md`** — nuevo documento, ubicado junto al módulo (mismo patrón que `prompts/README.md`), que cubre:

- Por qué agregar un proveedor nuevo no requiere tocar `AIProvider` (contrato estructural, `Protocol`) ni ningún agente de análisis.
- Un procedimiento paso a paso para sumar Gemini, OpenAI u Ollama, usando `anthropic_provider.py` como plantilla: crear un módulo nuevo, implementar `complete(prompt, data=None) -> AIProviderResponse`, resolver credenciales desde `config.local.toml` (con los defaults ya definidos en `config.example.toml`, ej. `http://localhost:11434` para Ollama), traducir cualquier fallo a `AIProviderError`, no modificar `selection.py` ni los agentes, y escribir pruebas mockeando la llamada HTTP/SDK (nunca red real), siguiendo el patrón de `test_ai_providers_anthropic.py`.
- Una aclaración explícita: el mapeo de "nombre de proveedor resuelto" (string que devuelve `resolve_agent_provider`) a "clase concreta a instanciar" (`AnthropicAIProvider`, `GeminiAIProvider`, etc.) todavía no existe como mecanismo genérico; es responsabilidad de quien construya cada agente (tareas pendientes "Agente de análisis: salud financiera" / "valoración"), no de este documento ni de `selection.py`.
- Qué queda explícitamente fuera de alcance: implementar cualquiera de las integraciones, y un registro/factory central de proveedores (no hay evidencia de que se necesite con una sola integración concreta).

No se modificó ningún archivo de código: esta tarea es puramente documental, tal como la describe TASKS.md ("sin implementar aún si no es necesario para el MVP").

## Decisiones tomadas

- **Ubicación del documento: `investmentops/ai_providers/EXTENDING.md`, no `ARCHITECTURE.md`.** `ARCHITECTURE.md` ya cubre el principio arquitectónico general ("Extensibilidad" > "Nuevos proveedores de IA") y explícitamente "no contiene código" ni detalles de implementación. El procedimiento concreto (qué archivo crear, cómo resolver credenciales, qué pruebas escribir) es información operativa ligada al módulo `investmentops/ai_providers`, coherente con el mismo criterio ya usado para `prompts/README.md` (documentación de convención viviendo junto a la carpeta que describe).
- **No se implementó ningún proveedor nuevo.** La propia redacción de la tarea en TASKS.md permite dejarlo "sin implementar aún si no es necesario para el MVP"; no hay ninguna señal de que Gemini, OpenAI u Ollama sean necesarios ahora mismo (el MVP de Fase 1, según ROADMAP.md, solo exige "al menos una implementación funcional").
- **No se creó un mecanismo de registro/factory de proveedores.** Se documentó explícitamente que ese mapeo no existe todavía y que crearlo antes de tener una segunda integración concreta sería anticipar una abstracción sin caso de uso real, siguiendo el mismo criterio ya aplicado en otras decisiones del proyecto (ver por ejemplo `market_data.py`, que evita adelantar series históricas sin necesidad concreta).

## Archivos creados o modificados

Creados:
- `investmentops/ai_providers/EXTENDING.md`

Modificados:
- `TASKS.md` (tarea "Dejar documentado... cómo se sumarían las integraciones restantes" marcada como completada, con referencia inline a este documento)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `.python-version`, `pyproject.toml`, y todo `investmentops/` (código y tests) salvo el nuevo `EXTENDING.md`.

## Problemas encontrados

Ninguno. La implementación existente de `AnthropicAIProvider` ya era suficientemente representativa del patrón a seguir; no hubo ambigüedad que resolver de forma nueva.

## Próxima tarea recomendada

Con esta tarea completa, la sección "Interfaz de proveedores de IA" de la Fase 1 queda **cerrada por completo** en `TASKS.md`. La siguiente sección sin marcar es "Normalización y almacenamiento", cuya primera tarea es:

1. *"Implementar la transformación de datos crudos del proveedor al modelo 'Estados financieros normalizados'."* — requiere convertir el `payload` crudo que ya devuelve `FMPFundamentalsProvider.fetch` (claves `income_statement`, `balance_sheet_statement`, `quote`, ver `investmentops/data_providers/fundamentals.py`) a una instancia de `FinancialStatement` (ver `investmentops/data_layer/financial_statements.py`).

Nota para la próxima conversación:
- Antes de implementar, revisar la forma real del JSON que devuelve FMP en `income-statement` y `balance-sheet-statement` (campos `revenue`, `netIncome`, `totalDebt`, ya referenciados en `test_data_providers_fundamentals.py`) para mapearlos correctamente a `FinancialStatement.revenue`, `.net_income`, `.debt`, `.source` y `.period_end`.
