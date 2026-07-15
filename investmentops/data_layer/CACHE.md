# Caché local de datos normalizados (Data Layer)

Cubre la tarea "Definir el mecanismo de caché local (archivo o base
embebida) para persistir datos normalizados" (TASKS.md, Fase 1,
"Normalización y almacenamiento").

Esta tarea **solo decide y documenta el mecanismo**: formato, ubicación y
estructura de la caché. La implementación del guardado y la lectura son
tareas separadas, ya completadas y desglosadas en `TASKS.md`:

- "Implementar el guardado de los datos normalizados en la caché tras
  cada consulta." — `save_financial_statement`/`save_market_data` en
  `investmentops/data_layer/cache.py`.
- "Implementar la lectura desde caché para evitar una nueva llamada al
  proveedor si el dato ya existe y es reciente." —
  `load_financial_statement`/`load_market_data` en el mismo módulo.

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
  los dataclasses de dominio: es metadato propio de la caché, usado por
  la lectura para decidir si un dato cacheado sigue siendo válido o debe
  refrescarse. No debe confundirse con `period_end`/`as_of` (fecha del
  propio dato financiero) ni con `ProviderMetadata.queried_at` (fecha en
  que se consultó al proveedor por primera vez): `cached_at` es
  específicamente la fecha de la última escritura en caché.
- Si una empresa aún no tiene un tipo de dato cacheado (ej. se cacheó su
  `financial_statement` pero todavía no su `market_data`), la clave
  correspondiente simplemente está ausente del objeto JSON, no se
  representa con `null` ni con un objeto vacío.

## Qué determina "reciente"

Umbral elegido: **24 horas** desde `cached_at`
(`investmentops.data_layer.cache.DEFAULT_MAX_AGE`). Si al invocar
`load_financial_statement`/`load_market_data` la sección cacheada tiene
menos de 24 horas de antigüedad, se devuelve el modelo reconstruido sin
consultar al proveedor de nuevo; si tiene más, se devuelve `None` para
que quien invoque la lectura dispare una nueva consulta.

Es un valor fijo y explícito en código (no una clave nueva de
`config.local.toml`): no hay hoy un caso de uso que requiera que el
usuario lo configure, y agregarlo a la configuración antes de necesitarlo
concretamente iría contra el mismo criterio de no sobre-diseñar ya
aplicado en otros módulos de esta capa. `max_age` es, de todas formas, un
parámetro explícito de `load_financial_statement`/`load_market_data` por
si una llamada puntual necesita un umbral distinto al de 24 horas.

## Fuera de alcance de esta tarea (aún)

- Cachear series históricas (varios periodos): la estructura anterior
  asume un único corte por modelo, igual que `FinancialStatement` y
  `MarketData` hoy. Extenderla a series es tarea explícita de la Fase 3
  (ver TASKS.md, Fase 3, "Normalización"), y podrá representarse como una
  lista dentro de la misma clave (ej. `"financial_statement": [...]`) sin
  romper este formato de archivo por ticker.
- Decidir qué hace el orquestador cuando la lectura devuelve `None`
  (disparar la consulta real al proveedor de datos y luego guardar el
  resultado): responsabilidad de "Orquestador mínimo" (ver TASKS.md), no
  de esta capa de caché.
