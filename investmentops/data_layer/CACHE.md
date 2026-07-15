# Caché local de datos normalizados (Data Layer)

Cubre la tarea "Definir el mecanismo de caché local (archivo o base
embebida) para persistir datos normalizados" (TASKS.md, Fase 1,
"Normalización y almacenamiento").

Esta tarea **solo decide y documenta el mecanismo**: formato, ubicación y
estructura de la caché. La implementación del guardado y la lectura son
tareas separadas y posteriores, ya desglosadas en `TASKS.md`:

- "Implementar el guardado de los datos normalizados en la caché tras
  cada consulta."
- "Implementar la lectura desde caché para evitar una nueva llamada al
  proveedor si el dato ya existe y es reciente."

## Decisión: archivos JSON, uno por empresa (ticker)

Se elige **un archivo JSON por ticker** (no una base de datos embebida
tipo SQLite), por los siguientes motivos:

- **Sin dependencias nuevas.** `json` es parte de la librería estándar de
  Python, igual criterio que llevó a elegir TOML para la configuración
  (ver `CONFIGURATION.md`, "Formato elegido: TOML"): mantener el número
  de dependencias del proyecto al mínimo.
- **Coherente con "un solo usuario, todo local".** No hay necesidad de
  transacciones concurrentes, índices ni consultas relacionales: cada
  archivo se lee/escribe completo para su ticker. Un motor de base de
  datos embebida (SQLite) sería una solución sobredimensionada para el
  volumen de datos del MVP (ver ARCHITECTURE.md, principio de no
  sobre-diseñar antes de tener el caso de uso real, ya aplicado en
  `investmentops/data_layer/market_data.py`).
- **Legible y depurable.** Un archivo JSON por empresa puede inspeccionarse
  directamente (`cat`, editor de texto) sin herramientas adicionales, útil
  para depurar durante el desarrollo del MVP.
- **Granularidad natural.** El resto del sistema ya opera por ticker
  (`DataProvider.fetch(ticker)`, `AnalysisEngine.analyze(company_data)`):
  un archivo por ticker evita tener que parsear/filtrar un archivo único
  y monolítico para encontrar los datos de una empresa.

## Ubicación

- Los archivos viven bajo la ruta configurada en `config.local.toml`,
  sección `[cache]` (ver `CONFIGURATION.md`; valor por defecto en
  `config.example.toml`: `.investmentops_cache/`).
- Un archivo por ticker, nombrado `<TICKER>.json` (ej.
  `.investmentops_cache/AAPL.json`), usando el ticker ya normalizado en
  mayúsculas (mismo criterio que `FMPFundamentalsProvider.fetch`, que
  normaliza el ticker con `.strip().upper()`).

## Estructura del archivo

Cada archivo `<TICKER>.json` contiene un único objeto JSON con una clave
por modelo de dominio cacheado, de forma que agregar un nuevo tipo de
dato cacheado (ej. noticias, comparables, en fases futuras) no requiera
tocar los datos ya guardados de otros tipos:

```json
{
  "financial_statement": {
    "revenue": 1000000.0,
    "net_income": 150000.0,
    "debt": 400000.0,
    "source": "fmp",
    "period_end": "2025-12-31",
    "cached_at": "2026-07-14T12:00:00+00:00"
  },
  "market_data": {
    "price": 185.5,
    "market_cap": 2900000000000.0,
    "multiples": {},
    "source": "fmp",
    "as_of": "2025-12-31",
    "cached_at": "2026-07-14T12:00:00+00:00"
  }
}
```

- Cada sección (`financial_statement`, `market_data`, y las que se agreguen
  en fases futuras) serializa directamente los campos del dataclass
  correspondiente (`FinancialStatement`, `MarketData`), con las fechas
  (`period_end`, `as_of`) en formato ISO 8601 (`YYYY-MM-DD`), consistente
  con el formato que ya devuelve FMP y que ya interpreta
  `investmentops.data_layer.normalization`.
- Se agrega un campo `cached_at` (fecha/hora en que se escribió esa
  sección de la caché, en UTC, formato ISO 8601) que **no** forma parte de
  los dataclasses de dominio: es metadato propio de la caché, necesario
  para que la tarea de lectura ("...si el dato ya existe y es reciente")
  pueda decidir si un dato cacheado sigue siendo válido o debe
  refrescarse. No debe confundirse con `period_end`/`as_of` (fecha del
  propio dato financiero) ni con `ProviderMetadata.queried_at` (fecha en
  que se consultó al proveedor por primera vez): `cached_at` es
  específicamente la fecha de la última escritura en caché.
- Si una empresa aún no tiene un tipo de dato cacheado (ej. se cacheó su
  `financial_statement` pero todavía no su `market_data`), la clave
  correspondiente simplemente está ausente del objeto JSON, no se
  representa con `null` ni con un objeto vacío.

## Qué determina "reciente" (fuera de alcance de esta tarea)

El criterio concreto para decidir si un dato cacheado es lo bastante
reciente como para evitar una nueva llamada al proveedor (ej. un umbral
de horas/días desde `cached_at`) es responsabilidad de la tarea de
lectura ("Implementar la lectura desde caché..."), no de esta decisión de
mecanismo. Este documento solo garantiza que el dato necesario para esa
decisión (`cached_at`) ya queda registrado en la estructura del archivo.

## Fuera de alcance de esta tarea

- La función que efectivamente escribe un archivo `<TICKER>.json` (tarea
  "Implementar el guardado...").
- La función que efectivamente lee y valida la frescura de un archivo
  cacheado (tarea "Implementar la lectura...").
- El manejo de errores de lectura/escritura en disco (permisos, disco
  lleno, JSON corrupto): se resuelve como parte de las dos tareas
  anteriores, no aquí.
- Cachear series históricas (varios periodos): la estructura anterior
  asume un único corte por modelo, igual que `FinancialStatement` y
  `MarketData` hoy. Extenderla a series es tarea explícita de la Fase 3
  (ver TASKS.md, Fase 3, "Normalización"), y podrá representarse como una
  lista dentro de la misma clave (ej. `"financial_statement": [...]`) sin
  romper este formato de archivo por ticker.
