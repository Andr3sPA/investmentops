# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: salud financiera → *"Implementar la
invocación al proveedor de IA configurado con esas métricas + el
prompt."*

Antes de implementarla, se verificó que no estuviera ya satisfecha por
código existente:

- `investmentops/ai_providers/anthropic_provider.py` ya implementa
  `AIProvider.complete()`, pero nada en el proyecto lo invocaba todavía
  desde un agente concreto.
- `investmentops/ai_providers/selection.py` (`resolve_agent_provider`)
  ya resuelve *qué nombre* de proveedor le corresponde a un agente, pero
  `investmentops/ai_providers/EXTENDING.md` documentaba explícitamente
  que no existía ("Quién decide qué clase concreta instanciar") un
  mecanismo que tradujera ese nombre a una instancia concreta de
  `AIProvider`.
- `investmentops/analysis_engines/financial_health.py` solo tenía el
  cálculo determinístico de métricas (`calculate_financial_health_metrics`);
  no invocaba IA ni cargaba ningún prompt desde código.
- No existía ningún mecanismo para cargar `prompts/<agent_id>.md` desde
  código (los prompts solo se habían usado, hasta ahora, como archivos
  de referencia para quien escribe el código, no como algo que el código
  leyera en tiempo de ejecución).

Se confirmó que la tarea requería trabajo nuevo en tres piezas
complementarias.

## Qué se implementó

**`investmentops/analysis_engines/prompts.py`** (nuevo) — mecanismo
reutilizable de carga de prompts: `load_prompt(agent_id, *,
prompts_dir=None)` traduce un `agent_id` (ej. `"financial_health"`) a
`prompts/<agent_id>.md` (raíz del proyecto, salvo que se indique
`prompts_dir` explícitamente, útil para pruebas) y devuelve su
contenido como texto plano. Señala `PromptError` si el archivo no
existe, si falla la lectura, o si está vacío. Implementa exactamente la
nota dejada en la entrada anterior de este archivo: *"Revisar si
conviene un mecanismo simple de carga de prompts... reutilizable por
futuros agentes"*.

**`investmentops/ai_providers/factory.py`** (nuevo) — `build_ai_provider(
provider_name, *, config=None)` traduce el nombre de proveedor resuelto
por `resolve_agent_provider` (ej. `"anthropic"`) a la instancia concreta
correspondiente de `AIProvider` (hoy solo `AnthropicAIProvider`, vía un
mapeo explícito `_PROVIDER_FACTORIES`). Si el nombre no tiene una
integración concreta implementada, levanta `AIProviderError` con un
mensaje que lista los proveedores soportados actualmente y remite a
`EXTENDING.md` para sumar uno nuevo. `investmentops/ai_providers/__init__.py`
se actualizó para re-exportar `build_ai_provider`, siguiendo el mismo
patrón ya usado para el resto de la interfaz.

**`investmentops/analysis_engines/financial_health.py`** (modificado) —
se agregó `invoke_financial_health_agent(statement, metrics, *,
config=None) -> AIProviderResponse`, que combina las tres piezas
anteriores más lo ya existente:

1. Carga `prompts/financial_health.md` vía `load_prompt`.
2. Resuelve el proveedor/modelo del agente `"financial_health"` vía
   `resolve_agent_provider` (ya existente, sin cambios).
3. Construye la instancia concreta de `AIProvider` vía
   `build_ai_provider`.
4. Invoca `provider.complete(prompt, data=...)`, enviando como `data` el
   `FinancialStatement` normalizado (ingresos, beneficio neto, deuda,
   fuente, fecha de corte) y las `FinancialHealthMetrics` ya calculadas
   (`net_margin`, `debt_to_revenue`, `warnings`) — nunca al revés: la IA
   no calcula ni corrige estas métricas, solo las recibe ya calculadas
   por `calculate_financial_health_metrics` (sin cambios en esa función).

Devuelve el `AIProviderResponse` crudo (texto + metadatos de
procedencia). No se modificó `calculate_financial_health_metrics` ni
`FinancialHealthMetrics`.

**Pruebas nuevas:**
- `investmentops/tests/test_analysis_engines_prompts.py` — carga
  exitosa, archivo ausente, archivo vacío, y una prueba de integración
  que confirma que `prompts/financial_health.md` real se puede cargar y
  contiene el texto esperado.
- `investmentops/tests/test_ai_providers_factory.py` — construcción
  exitosa de `AnthropicAIProvider`, error claro para un proveedor sin
  integración concreta, y propagación de errores de construcción (ej.
  falta de API key) desde la clase concreta.
- `investmentops/tests/test_analysis_engines_financial_health_invoke.py`
  — invocación exitosa (mockeando `requests.post`, igual patrón que
  `test_ai_providers_anthropic.py`), confirma que el prompt y las
  métricas (incluida la advertencia de `revenue == 0`) viajan en la
  llamada real a la API, que se respeta el modelo configurado, y que los
  errores de resolución de proveedor (`AgentProviderSelectionError`), de
  proveedor no soportado (`AIProviderError`) y de prompt faltante
  (`PromptError`) se propagan sin ser silenciados.

No se modificó ningún otro módulo de código Python (`calculate_financial_health_metrics`,
`FinancialHealthMetrics`, `AnthropicAIProvider`, `resolve_agent_provider`,
`load_config`, ningún modelo de dominio) ni ningún prompt existente.

## Decisiones tomadas

- **La fábrica de proveedores (`build_ai_provider`) es un mapeo estático
  explícito**, no un registro dinámico/plugin: hoy solo existe una
  integración concreta (Anthropic), y un mecanismo más elaborado sería
  sobre-diseño antes de tener más de un proveedor real (mismo criterio
  ya aplicado en otras partes del proyecto, ver `MarketData`,
  `CACHE.md`). Sumar un proveedor nuevo (Gemini, OpenAI, Ollama) implica
  agregar una entrada al mapeo, sin tocar `contracts.py` ni
  `selection.py`, consistente con `EXTENDING.md`.
- **El cargador de prompts (`load_prompt`) vive en
  `investmentops.analysis_engines`, no en `investmentops.config` ni en
  un módulo nuevo de nivel superior**, porque quien lo consume hoy (y
  presumiblemente en el futuro: valoración, estrategias) son agentes de
  análisis; no es un dato de configuración del sistema.
- **`invoke_financial_health_agent` no parsea la respuesta del modelo.**
  Devuelve el `AIProviderResponse` crudo tal cual lo entrega el
  proveedor. El parseo a la estructura final del agente
  (`AnalysisResult`: hallazgos, métricas de soporte, limitaciones,
  procedencia) es la tarea siguiente y explícitamente separada en
  `TASKS.md`.
- **`data` enviado al proveedor incluye tanto el `FinancialStatement`
  como las `FinancialHealthMetrics`**, no solo las métricas: el prompt
  (`prompts/financial_health.md`) ya asumía que el modelo recibiría
  "Datos normalizados de la empresa" además de las métricas
  precalculadas, por lo que omitir el `FinancialStatement` habría dejado
  el prompt inconsistente con los datos realmente enviados.
- **No se creó un mecanismo genérico "agente completo" (invocación +
  parseo) en esta tarea.** Se limita estrictamente a la invocación, tal
  como pide el título exacto de la tarea en `TASKS.md`.

## Validación realizada

No fue posible ejecutar la suite de pruebas real vía `pytest` en este
entorno de Claude Web (sin acceso a red para instalar dependencias). En
su lugar, se reconstruyó un árbol mínimo equivalente de las
dependencias ya existentes (`contracts.py`, `selection.py`,
`anthropic_provider.py`, `config/__init__.py`, `FinancialStatement`,
`prompts/financial_health.md` real) y se ejecutaron manualmente, con
`unittest.mock`, los mismos escenarios cubiertos por los archivos de
prueba nuevos (invocación exitosa con prompt+métricas en el payload,
advertencia de `revenue == 0` propagada, proveedor no soportado,
`load_prompt` exitoso/vacío/ausente, `build_ai_provider` exitoso/error).
Todos los escenarios pasaron. Se recomienda correr `pytest` en el
entorno real del proyecto para confirmar la integración completa junto
con el resto de la suite existente.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/prompts.py`
- `investmentops/ai_providers/factory.py`
- `investmentops/tests/test_analysis_engines_prompts.py`
- `investmentops/tests/test_ai_providers_factory.py`
- `investmentops/tests/test_analysis_engines_financial_health_invoke.py`

Modificados:
- `investmentops/analysis_engines/financial_health.py` (se agregó
  `invoke_financial_health_agent` y `AGENT_ID`; sin cambios en
  `calculate_financial_health_metrics` ni `FinancialHealthMetrics`)
- `investmentops/ai_providers/__init__.py` (re-exporta `build_ai_provider`)
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`prompts/financial_health.md`, `investmentops/ai_providers/contracts.py`,
`investmentops/ai_providers/selection.py`,
`investmentops/ai_providers/anthropic_provider.py`,
`investmentops/ai_providers/EXTENDING.md`,
`investmentops/analysis_engines/contracts.py`,
`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`, y el resto
del código existente.

## Problemas encontrados

Ninguno en la implementación. Limitación del entorno: sin acceso a red
para instalar `pytest`/`requests` y correr la suite real (ver
"Validación realizada" arriba); se compensó con una reconstrucción
mínima y validación manual equivalente.

## Próxima tarea recomendada

La siguiente tarea sin empezar en la misma sección de `TASKS.md`
("Agente de análisis: salud financiera") es:

1. *"Implementar el parseo de la respuesta del modelo al resultado
   estructurado del agente (hallazgos, métricas, advertencias si faltan
   datos, proveedor/modelo usado)."*

Nota para la próxima conversación:
- Esta tarea debe tomar el `AIProviderResponse` que ya devuelve
  `invoke_financial_health_agent` (`response.content`,
  `response.provider`, `response.model`, `response.generated_at`) y
  construir un `AnalysisResult` (ver
  `investmentops/analysis_engines/contracts.py`): `analysis_id`
  (`"financial_health"`, ya disponible como `AGENT_ID`), `findings`
  (derivados de `response.content`; decidir si es una lista de una sola
  línea con el texto completo, o si se intenta segmentar por párrafos —
  probablemente lo primero, dado que el prompt no exige un formato
  estructurado), `supporting_metrics` (las mismas `FinancialHealthMetrics`
  ya calculadas, no nada nuevo), `limitations` (al menos la limitación de
  liquidez ya documentada en `FINANCIAL_HEALTH_METRICS.md`, más
  cualquier advertencia de `FinancialHealthMetrics.warnings`), y
  `provenance` (`AnalysisProvenance(ai_provider=response.provider,
  ai_model=response.model, generated_at=response.generated_at)`).
- Esta función probablemente debería combinarse con
  `invoke_financial_health_agent` en una función de nivel superior (ej.
  `analyze_financial_health`) que sea la que finalmente cumpla el
  protocolo `AnalysisEngine` (`analyze(company_data, metrics=None) ->
  AnalysisResult`) de `investmentops.analysis_engines.contracts` —
  aunque decidir esa integración exacta (¿una clase que envuelva estas
  funciones? ¿una función libre que ya cumpla el protocolo estructural
  del `Protocol`?) es trabajo de esa tarea, no de esta.
- No hay indicación en el prompt de que el modelo deba devolver un
  formato estructurado (ej. JSON): la respuesta es texto libre en
  español. El parseo, por tanto, es principalmente "empaquetar" el texto
  como `findings`, no "extraer campos" de una respuesta estructurada.
  Si se decide pedirle al modelo un formato más estructurado en el
  futuro, sería un cambio al prompt (`prompts/financial_health.md`), no
  a esta capa de parseo.
