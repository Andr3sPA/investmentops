# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Fuente de datos de noticias" → "Implementar el contrato de
'data provider' para noticias (ticker/nombre de empresa in, lista de
eventos crudos out)" (TASKS.md).

### Qué se implementó

Nuevo módulo `investmentops/data_providers/news.py`, con la clase
`FMPNewsProvider`, que cumple el contrato `DataProvider`
(investmentops.data_providers.contracts) sobre la decisión ya tomada en
`investmentops/data_providers/NEWS_PROVIDER.md`:

- `fetch(ticker)` consulta el endpoint `/stock_news` de FMP (filtrado
  por `tickers=<TICKER>`, con `limit` configurable), y devuelve un
  `RawProviderData` cuyo `payload` es la lista cruda de noticias tal
  como la entrega FMP (sin seleccionar ni transformar campos) — la
  transformación al modelo de dominio "Noticias" es una tarea separada
  y posterior de esta misma sección ("Normalización").
- Lee sus credenciales desde una sección **nueva y separada**,
  `[data_providers.news]`, en vez de reutilizar
  `[data_providers.fundamentals]`, tal como ya lo dejó documentado
  `NEWS_PROVIDER.md`. Se actualizaron `config.example.toml` y
  `CONFIGURATION.md` con esta nueva sección.
- `ProviderMetadata.source` se identifica como `"fmp"` (mismo
  identificador de proveedor externo ya usado por
  `FMPFundamentalsProvider`): lo que cambia entre ambos clientes es la
  sección de configuración que cada uno lee, no el nombre de la fuente.
- Traduce a `DataProviderError` los fallos mínimos exigidos por el
  contrato `DataProvider` (ticker vacío, fallo de red, autenticación
  inválida, error HTTP, respuesta no interpretable como JSON), sin dejar
  escapar excepciones de `requests` sin traducir.
- **Deliberadamente fuera de alcance de esta tarea** (quedan como las
  dos tareas siguientes de la misma sección de `TASKS.md`): adjuntar
  procedencia (fuente, fecha de publicación, fecha de consulta) a cada
  noticia individual, y decidir/implementar el tratamiento de "sin
  resultados" como caso de error explícito — hoy una lista vacía es una
  respuesta válida y exitosa (una empresa puede legítimamente no tener
  noticias recientes).

Nuevo archivo de pruebas `investmentops/tests/test_data_providers_news.py`,
mockeando `requests.get` (sin llamadas de red reales), cubriendo:
cumplimiento del protocolo `DataProvider`, payload de lista cruda,
parámros de consulta (`tickers`, `limit`, `apikey`), normalización de
ticker a mayúsculas, tratamiento de lista vacía como válida, ticker
vacío, fallos de red/autenticación/servidor/JSON inválido, resolución de
credenciales desde `config` (incluyendo que NO lea accidentalmente
`[data_providers.fundamentals]`), y valor por defecto de `base_url`.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/news.py`
- `investmentops/tests/test_data_providers_news.py`

Modificados:
- `config.example.toml` (nueva sección `[data_providers.news]`)
- `CONFIGURATION.md` (mención de la nueva sección en "Estructura del
  archivo")
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Fuente de datos de noticias" → "Adjuntar metadatos de
procedencia (fuente, fecha de publicación, fecha de consulta) a cada
noticia cruda", sobre `FMPNewsProvider.fetch` ya implementado en
`investmentops/data_providers/news.py`.