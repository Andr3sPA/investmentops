# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Normalización" → "Implementar el guardado de noticias
normalizadas en la caché local tras cada consulta" (TASKS.md).

### Qué se implementó

`save_news`/`load_news` en `investmentops/data_layer/cache.py` (mismo
módulo que ya aloja el guardado/lectura de `financial_statement`,
`market_data` y `financial_statement_series`).

Siguen exactamente el mismo patrón ya usado por
`save_financial_statement_series`/`load_financial_statement_series`
(Fase 3), aplicado a `News` en vez de a la serie de estados financieros:

- **Sección nueva:** `"news"`, en el mismo archivo `<TICKER>.json`, junto
  a las tres secciones ya existentes. Guardar/leer noticias no toca
  ninguna otra sección (misma fusión ya usada en el resto del módulo).
- **Forma de la sección:** `{"items": [...], "cached_at": ...}`, donde
  cada elemento de `"items"` serializa los cinco campos de `News`
  (`title`, `summary`, `source`, `published_at` en ISO 8601, `url`).
  No se reutiliza `_save_section`/`dataclasses.asdict` directamente por
  la misma razón que la serie histórica: `News.published_at` es un
  `datetime`, y `News` se guarda como una lista, no como un único
  dataclass plano.
- **Lista vacía como valor válido:** una empresa sin noticias recientes
  (`payload == []`, ver `investmentops.data_providers.news`, "'No
  devuelve resultados' NO es un error") se guarda y se lee tal cual
  (`[]`), distinguiéndose explícitamente de `None` (nada cacheado, o
  cacheado pero vencido) — quien invoque `load_news` no debe confundir
  "ya sé que no hay noticias" con "todavía no sé si hay noticias".
- **Manejo de fallos:** mismo criterio que las demás secciones
  (`CacheError` ante ticker vacío, fallos de E/S, sección corrupta o
  incompleta — un elemento de `"items"` sin algún campo imprescindible,
  o con `published_at` no interpretable).

Reutiliza sin duplicar `_resolve_cache_dir`, `_ticker_file`,
`_read_existing` y `_load_section`, ya existentes en el módulo.

Nuevo archivo de pruebas
`investmentops/tests/test_data_layer_cache_news.py`, siguiendo el mismo
patrón de `test_data_layer_cache_series.py`, incluyendo pruebas de
no-ruptura del roundtrip ya existente de `financial_statement`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_layer_cache_news.py`

Modificados:
- `investmentops/data_layer/cache.py` (nuevas funciones `save_news`/
  `load_news`, nueva constante `_NEWS_SECTION`, import de `News`,
  ampliación del docstring del módulo; sin cambios en las funciones ya
  existentes)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Normalización" → "Implementar la lectura de noticias
normalizadas desde caché para evitar una nueva llamada al proveedor si
el dato ya existe y es reciente" — nota: `load_news` ya quedó
implementada en esta misma tarea (junto con `save_news`, siguiendo el
mismo criterio ya aplicado en Fase 3 a
`save_financial_statement_series`/`load_financial_statement_series`, que
también se implementaron en conjunto). La próxima conversación debería
verificar esto primero y, si se confirma que ya está satisfecha, marcarla
como completada sin duplicar código, dejando como siguiente tarea real
"Definir el criterio básico de relevancia/filtrado de noticias para el
MVP" (Fase 4, "Motor de análisis: noticias relevantes").