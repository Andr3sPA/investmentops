# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Normalización y almacenamiento → *"Definir el mecanismo de caché local (archivo o base embebida) para persistir datos normalizados."*

Antes de trabajar en ella, se verificó que no estuviera ya satisfecha: se
revisó todo `investmentops/data_layer/` (`domain.py`,
`financial_statements.py`, `market_data.py`, `normalization.py`,
`__init__.py`) y no existe ningún módulo de caché ni lógica de
lectura/escritura a disco más allá de `config.local.toml`.
`CONFIGURATION.md` ya define la *ubicación* de la caché
(`[cache].path`), pero no el *mecanismo* (formato de archivo,
estructura interna). Se confirmó que requería trabajo nuevo.

Esta tarea es, por su propia redacción en `TASKS.md`, una **decisión de
diseño** (igual criterio que "Elegir el proveedor de datos financieros
fundamentales... (decisión, no implementación)"), no una implementación:
las dos tareas siguientes de la misma sección ("Implementar el
guardado..." e "Implementar la lectura...") son las que efectivamente
escriben código a partir de esta decisión.

## Qué se implementó

**`investmentops/data_layer/CACHE.md`** (archivo nuevo) — documento de
decisión que define el mecanismo de caché local, siguiendo el mismo
patrón ya usado en `CONFIGURATION.md` y
`investmentops/ai_providers/EXTENDING.md`:

- **Mecanismo elegido:** un archivo JSON por ticker (no una base de datos
  embebida tipo SQLite), ubicado bajo la ruta de `[cache].path` (ver
  `CONFIGURATION.md`), nombrado `<TICKER>.json`.
- **Estructura:** un objeto JSON con una clave por modelo de dominio
  cacheado (`financial_statement`, `market_data`, y las que se agreguen
  en fases futuras), cada una serializando los campos del dataclass
  correspondiente más un campo `cached_at` (metadato propio de la caché,
  no del modelo de dominio) que registra cuándo se escribió esa sección,
  necesario para que la futura tarea de lectura pueda decidir si un dato
  sigue siendo "reciente".
- El documento deja explícito qué queda fuera de esta tarea: la función
  de guardado, la función de lectura/verificación de frescura, el manejo
  de errores de disco, y el soporte de series históricas (Fase 3).

## Decisiones tomadas

- **JSON por ticker, no SQLite ni otra base embebida.** `json` es
  librería estándar (mismo criterio que llevó a elegir TOML para
  `config.local.toml`, ver `CONFIGURATION.md`), no añade dependencias, y
  es suficiente para el volumen y la concurrencia (un solo usuario, sin
  acceso simultáneo) del MVP. Introducir SQLite habría sido
  sobredimensionar la solución sin un caso de uso que lo justifique hoy
  (ver ARCHITECTURE.md, principio de no sobre-diseñar, ya aplicado
  previamente al dejar `MarketData.multiples` vacío hasta que exista el
  agente de valoración).
- **Un archivo por ticker, no un único archivo global.** Consistente con
  que el resto del sistema ya opera por ticker
  (`DataProvider.fetch(ticker)`, `AnalysisEngine.analyze(company_data)`);
  evita tener que parsear un archivo monolítico para encontrar los datos
  de una sola empresa.
- **Una clave JSON por modelo de dominio dentro del mismo archivo,** en
  vez de un archivo separado por modelo (ej. `AAPL.financial.json` +
  `AAPL.market.json`). Mantiene junta toda la información cacheada de una
  empresa y dentro de un único archivo, sin ganar nada a cambio de
  fragmentar en más archivos.
- **Campo `cached_at` explícito, separado de `period_end`/`as_of`.** Estos
  últimos son la fecha del propio dato financiero (ya parte de los
  dataclasses `FinancialStatement`/`MarketData`); `cached_at` es cuándo se
  escribió en la caché, el dato que necesitará la tarea de lectura para
  decidir frescura. Mezclarlos habría acoplado el mecanismo de caché al
  significado de negocio de esas fechas.
- **No se decide aquí el umbral de "reciente".** La propia redacción de
  la tarea de lectura ("...si el dato ya existe y es reciente") deja ese
  criterio para esa tarea específica; esta decisión de mecanismo solo
  garantiza que el dato (`cached_at`) para tomarlo esté disponible.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/CACHE.md`

Modificados:
- `TASKS.md` (tarea "Definir el mecanismo de caché local..." marcada como
  completada, con referencia inline a `investmentops/data_layer/CACHE.md`)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`.gitignore`, `.python-version`, `pyproject.toml`, y el resto de
`investmentops/` (código y tests).

## Problemas encontrados

Ninguno. La decisión se apoyó directamente en patrones ya establecidos en
el proyecto (TOML por ser stdlib y legible, granularidad por ticker ya
usada en toda la capa de proveedores/análisis), sin necesidad de evaluar
alternativas externas.

## Próxima tarea recomendada

Con esta decisión documentada, la siguiente sin marcar en "Normalización
y almacenamiento" es:

1. *"Implementar el guardado de los datos normalizados en la caché tras
   cada consulta."* — Implementar, en `investmentops/data_layer/`
   (probablemente un nuevo módulo `cache.py`, o junto a
   `normalization.py` si resulta ser poco código), una función que reciba
   un `FinancialStatement` y/o `MarketData` ya normalizado y lo escriba en
   `<cache_path>/<TICKER>.json` siguiendo la estructura definida en
   `investmentops/data_layer/CACHE.md` (fusionando con el contenido
   existente del archivo si ya hay otra sección cacheada para ese
   ticker, en vez de sobrescribirlo por completo).

Nota para la próxima conversación:
- Revisar `investmentops/data_layer/CACHE.md` (recién creado) antes de
  implementar, para no desviarse de la estructura ya decidida (formato
  JSON, una clave por modelo, campo `cached_at`).
- Decidir en esa tarea cómo se resuelve la ruta de caché: lo más
  consistente con el resto del proyecto es leerla de
  `config.local.toml` vía `investmentops.config.load_config()` (mismo
  patrón ya usado en `FMPFundamentalsProvider` y `AnthropicAIProvider`
  para leer sus propias credenciales), aceptando también un parámetro
  explícito para facilitar las pruebas sin depender de un
  `config.local.toml` real en disco.
