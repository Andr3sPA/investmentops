# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Normalización y almacenamiento → *"Implementar el guardado de los datos normalizados en la caché tras cada consulta."*

Antes de trabajar en ella, se verificó que no estuviera ya satisfecha: se
revisó todo `investmentops/data_layer/` (`domain.py`,
`financial_statements.py`, `market_data.py`, `normalization.py`,
`CACHE.md`, `__init__.py`) y no existía ningún módulo `cache.py` ni
función que escribiera datos normalizados a disco. `CACHE.md` (tarea
anterior) solo documentaba la decisión de mecanismo, sin implementarla.
Se confirmó que requería trabajo nuevo.

## Qué se implementó

**`investmentops/data_layer/cache.py`** (módulo nuevo) — implementa el
mecanismo ya decidido en `CACHE.md`:

- `save_financial_statement(ticker, statement, *, cache_path=None, config=None)`
  y `save_market_data(ticker, market_data, *, cache_path=None, config=None)`:
  cada una escribe/actualiza la sección correspondiente
  (`"financial_statement"` o `"market_data"`) del archivo
  `<cache_path>/<TICKER>.json`, agregando un campo `cached_at` (UTC, ISO
  8601) a esa sección.
- La escritura **fusiona** con el contenido existente del archivo: guardar
  `market_data` para un ticker que ya tiene `financial_statement` cacheado
  no borra esta última sección, y viceversa (ver `CACHE.md`, "Estructura
  del archivo").
- El ticker se normaliza a mayúsculas para el nombre de archivo, mismo
  criterio que `FMPFundamentalsProvider.fetch`.
- La ruta de caché se resuelve, en orden: `cache_path` explícito (para
  pruebas) → `config["cache"]["path"]` si se pasa `config` → 
  `investmentops.config.load_config()["cache"]["path"]` → 
  `DEFAULT_CACHE_PATH` (`.investmentops_cache/`) si la configuración no
  define una ruta.
- El directorio de caché se crea automáticamente si no existe
  (`Path.mkdir(parents=True, exist_ok=True)`).
- `CacheError` (subclase de `RuntimeError`) señala: ticker vacío, fallo al
  crear el directorio, fallo al leer un archivo de caché existente (JSON
  corrupto o error de E/S), o fallo al escribir el archivo.

**`investmentops/tests/test_data_layer_cache.py`** (archivo nuevo) —
pruebas que mockean el sistema de archivos con `tmp_path` (sin depender
de `config.local.toml` real ni de una caché real en disco): guardado de
cada modelo, normalización de ticker a mayúsculas, fusión de secciones,
sobrescritura de solo la sección actualizada, creación automática del
directorio, resolución de la ruta desde `config`, ticker vacío rechazado,
y jerarquía de excepción.

## Decisiones tomadas

- **Dos funciones específicas (`save_financial_statement`,
  `save_market_data`) en vez de una función genérica que reciba
  cualquier modelo.** Mismo criterio que `normalization.py`
  (`financial_statement_from_raw`/`market_data_from_raw`): cada función
  sabe explícitamente a qué clave JSON corresponde su modelo, sin
  necesidad de inferirlo por tipo ni de que quien llama indique el
  nombre de la sección como string suelto (evita errores de tipeo en la
  clave).
- **`cache_path`/`config` como parámetros opcionales, con el mismo patrón
  ya usado en `FMPFundamentalsProvider.__init__` y
  `AnthropicAIProvider.__init__`.** Permite pasar `config` (dict) en
  pruebas sin tocar disco para `config.local.toml`, y `cache_path`
  directamente cuando ya se conoce la ruta (ej. para no volver a leer la
  configuración en cada llamada dentro de un mismo flujo).
- **Serialización manual de `date` a ISO 8601 (`_serialize`), en vez de
  un `json.JSONEncoder` personalizado.** Los dataclasses de dominio solo
  tienen un campo de tipo `date` cada uno (`period_end`, `as_of`); una
  función simple que recorre `asdict(model).items()` es suficiente y más
  legible que registrar un encoder para un caso tan acotado.
- **Fusión leyendo el archivo completo antes de escribir**, en vez de
  algún mecanismo de escritura parcial. Consistente con "un solo
  usuario, sin concurrencia" (ver `ARCHITECTURE.md`, "Un solo usuario,
  sin autenticación"): no hay riesgo de condición de carrera entre
  lectura y escritura que justifique algo más elaborado.
- **No se valida frescura ni se lee el `cached_at` existente.** Esta
  tarea es solo de guardado; decidir si un dato cacheado sigue siendo
  válido es, por diseño (ver `CACHE.md`), responsabilidad exclusiva de la
  tarea de lectura, todavía pendiente.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/cache.py`
- `investmentops/tests/test_data_layer_cache.py`

Modificados:
- `TASKS.md` (tarea "Implementar el guardado de los datos normalizados en
  la caché tras cada consulta" marcada como completada, con referencia
  inline a `investmentops/data_layer/cache.py`)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`investmentops/data_layer/CACHE.md`, `investmentops/data_layer/__init__.py`
(no se re-exportan las funciones de caché, mismo criterio ya aplicado a
`normalization.py`, que tampoco se re-exporta), `.gitignore`,
`.python-version`, `pyproject.toml`, y el resto de `investmentops/`
(código y tests).

## Problemas encontrados

Ninguno. La implementación siguió directamente la estructura ya decidida
y documentada en `CACHE.md`, sin necesidad de tomar decisiones de diseño
adicionales.

## Próxima tarea recomendada

La siguiente sin marcar en "Normalización y almacenamiento" es:

1. *"Implementar la lectura desde caché para evitar una nueva llamada al
   proveedor si el dato ya existe y es reciente."* — Implementar,
   probablemente en el mismo `investmentops/data_layer/cache.py`, una
   función que lea `<cache_path>/<TICKER>.json`, reconstruya el
   `FinancialStatement`/`MarketData` correspondiente a partir de la
   sección guardada (inversa de la serialización ya implementada:
   `date.fromisoformat` sobre `period_end`/`as_of`), y decida si el dato
   sigue siendo "reciente" a partir de `cached_at` (definir aquí el
   umbral, ya que `CACHE.md` lo dejó explícitamente para esta tarea).

Nota para la próxima conversación:
- Revisar `investmentops/data_layer/cache.py` (recién creado) antes de
  implementar la lectura, para reutilizar `_ticker_file`,
  `_resolve_cache_dir` y el formato ya escrito por `_save_section`, en
  vez de duplicar esa lógica.
- Decidir el umbral de frescura (ej. horas o días desde `cached_at`) como
  parte explícita de esa tarea; no se adelantó aquí ninguna decisión al
  respecto.
