# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → Orquestador mínimo → *"Implementar la función que recibe un
ticker y dispara la consulta al proveedor de Fase 1."*

Antes de implementarla, se verificó que no estuviera ya satisfecha:
`investmentops/core/__init__.py` solo re-exporta las estructuras
`ResearchFailure`/`ResearchResult` (definidas para una tarea anterior de
"Contratos e interfaces"), sin ninguna lógica que invoque a
`FMPFundamentalsProvider` ni a ningún otro `DataProvider`. Con esto
comienza la sección "Orquestador mínimo" de TASKS.md (la sección de
"Agente de análisis: valoración" quedó completa en la conversación
anterior).

## Qué se implementó

**`investmentops/core/orchestrator.py`** (nuevo) — `fetch_raw_data(ticker,
*, config=None, provider=None) -> RawProviderData`:

- Recibe un `ticker` y llama a `DataProvider.fetch(ticker)`.
- Por defecto construye un `FMPFundamentalsProvider(config=config)` (el
  proveedor ya elegido para el MVP, ver TASKS.md "Fuente de datos
  fundamentales" y `investmentops/data_providers/fundamentals.py`).
- Acepta un parámetro `provider` opcional para inyectar cualquier objeto
  que cumpla el contrato `DataProvider`
  (investmentops.data_providers.contracts), pensado principalmente para
  pruebas (sin llamadas de red reales) pero dejando la puerta abierta a
  que una tarea futura del orquestador elija entre varios proveedores sin
  tener que modificar esta función.
- No captura ni traduce `DataProviderError`: la propaga tal cual. El
  manejo de fallos "sin detener el resto del flujo" es una tarea
  explícita y posterior de esta misma sección de TASKS.md ("Implementar
  el manejo de fallo del proveedor de datos o del proveedor de IA...").
- No consulta la caché de datos normalizados
  (`investmentops.data_layer.cache`): esa caché guarda modelos ya
  normalizados (`FinancialStatement`/`MarketData`), no `RawProviderData`;
  decidir cuándo evitar la llamada al proveedor por tener ya un dato
  normalizado reciente en caché le corresponde a una tarea posterior que
  también involucre el paso de normalización ("Implementar el paso de
  datos crudos a la capa de normalización"), no a esta tarea aislada de
  "disparar la consulta".

**`investmentops/tests/test_core_orchestrator.py`** (nuevo) — pruebas
para `fetch_raw_data`:

- Que usa un `provider` inyectado y le pasa el `ticker` recibido.
- Que propaga `DataProviderError` sin traducirla cuando el proveedor
  inyectado falla.
- Que, sin `provider` explícito, construye y usa `FMPFundamentalsProvider`
  por defecto (mockeando `requests.get`, nunca una llamada de red real),
  confirmando `metadata.source == "fmp"`.
- Que un ticker inexistente contra el proveedor por defecto sigue
  propagando `DataProviderError` con el mensaje ya validado en
  `test_data_providers_fundamentals.py`.

## Decisiones tomadas

- **Alcance estrictamente limitado a "disparar la consulta".** TASKS.md
  desglosa el orquestador mínimo en 5 tareas pequeñas separadas (disparar
  consulta → normalización → invocar agentes → ensamblar
  `ResearchResult` → manejo de fallos). Esta tarea implementa
  únicamente la primera, sin adelantar ninguna de las siguientes, tal
  como quedó anotado como nota para esta conversación en la actualización
  anterior de este archivo.
- **Parámetro `provider` inyectable en vez de acoplar la función a
  `FMPFundamentalsProvider`.** Aunque hoy solo existe un proveedor de
  datos fundamentales concreto, el contrato `DataProvider` ya es
  estructural (`Protocol`, ver
  `investmentops/data_providers/contracts.py`) y el resto del proyecto ya
  usa ese patrón de inyección para pruebas (ver
  `AnthropicAIProvider`/`build_ai_provider`). Mantiene la función testeable
  sin mockear HTTP en cada prueba, y no le cierra la puerta a que el
  "Orquestador mínimo" decida más adelante construir el proveedor de otra
  forma, sin tener que modificar esta función.
- **No se integra con la caché en esta tarea.** Ver justificación en el
  docstring del módulo: la caché opera sobre modelos normalizados, no
  sobre datos crudos, por lo que mezclar esa decisión aquí adelantaría
  trabajo de la tarea de normalización.

## Validación realizada

Revisión manual del código y las pruebas nuevas contra el patrón ya
usado en otros clientes/pruebas del proyecto (`FMPFundamentalsProvider`,
`test_data_providers_fundamentals.py`,
`test_data_providers_contracts.py`). No se ejecutó la suite completa en
este entorno (Claude Web, sin acceso al repositorio real); se dejan los
archivos para que el usuario los integre y corra `pytest` localmente.

## Archivos creados o modificados

Creados:
- `investmentops/core/orchestrator.py`
- `investmentops/tests/test_core_orchestrator.py`

Modificados:
- `TASKS.md` (primera tarea de "Orquestador mínimo" marcada como
  completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/core/__init__.py`
(no se re-exportó `fetch_raw_data` todavía: `__init__.py` re-exporta hoy
estructuras de datos, no funciones de orquestación; decidir si conviene
re-exportarla puede revisarse cuando el orquestador tenga más de una
pieza), ningún otro módulo de código Python existente.

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Orquestador mínimo" (TASKS.md) es:

2. *"Implementar el paso de datos crudos a la capa de normalización."*

Nota para la próxima conversación:
- Ya existe toda la infraestructura que esta función debe encadenar tras
  `fetch_raw_data`: `investmentops.data_layer.normalization.
  financial_statement_from_raw`/`market_data_from_raw`, que ya reciben un
  `RawProviderData` (el mismo tipo que devuelve `fetch_raw_data`) y
  devuelven `FinancialStatement`/`MarketData` respectivamente, señalando
  `NormalizationError` si faltan campos.
- Esta tarea probablemente deba limitarse a encadenar
  `fetch_raw_data(ticker)` → `financial_statement_from_raw(raw)` +
  `market_data_from_raw(raw)`, dejando fuera todavía la lectura/escritura
  de caché (aunque ambas ya existen en
  `investmentops.data_layer.cache`), la invocación de los agentes de
  análisis, el ensamblado en `ResearchResult` y el manejo de fallos: cada
  uno es su propia tarea siguiente en la misma sección de TASKS.md.
- Los dos agentes de análisis (`analyze_financial_health`,
  `analyze_valuation`) y la caché de datos normalizados
  (`investmentops.data_layer.cache`) ya están completos y listos para ser
  usados por tareas posteriores del orquestador.
