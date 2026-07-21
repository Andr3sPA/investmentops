# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Normalización" → "Implementar la transformación de noticias
crudas al modelo normalizado" (TASKS.md).

### Qué se implementó

`news_from_raw` en `investmentops/data_layer/normalization.py` (mismo
módulo que ya aloja `financial_statement_from_raw`, `market_data_from_raw`
y `financial_statement_series_from_raw`, siguiendo el mismo criterio ya
documentado de no fragmentar transformaciones de este tipo en módulos
separados).

Traduce el `RawProviderData` que entrega `FMPNewsProvider.fetch`
(`investmentops/data_providers/news.py`) — una lista cruda de noticias,
cada una ya con `"source"`/`"queried_at"` adjuntados por
`_attach_news_provenance` — a `list[News]` (`investmentops.data_layer.News`),
una `News` por cada elemento del payload, en el mismo orden en que las
entrega FMP (a diferencia de `financial_statement_from_raw`/
`market_data_from_raw`, que solo toman el corte más reciente: aquí no
hay un único "dato más reciente" relevante, el futuro motor de noticias
necesita ver el conjunto completo).

Mapeo de campos: `"title"` -> `title`, `"text"` -> `summary`, `"site"`
-> `source` (el medio que publicó la noticia, distinto del proveedor de
datos que la entregó — misma distinción ya documentada en
`investmentops/data_layer/news.py`), `"publishedDate"` -> `published_at`
(parseado con `datetime.fromisoformat`, que en Python 3.11 ya interpreta
el formato `"YYYY-MM-DD HH:MM:SS"` que entrega FMP), `"url"` -> `url`.

Un `raw.payload` vacío o `None` produce una lista vacía sin levantar
ninguna excepción, consistente con que `FMPNewsProvider.fetch` ya trata
"sin noticias" como una respuesta válida, no un error. `NormalizationError`
se levanta únicamente si a una noticia individual le falta alguno de los
cinco campos imprescindibles, o si su fecha de publicación no es
interpretable; el mensaje identifica la posición (índice, comenzando en
1) de la noticia afectada dentro del payload, mismo criterio ya usado por
`financial_statement_series_from_raw` para identificar el periodo que
falla en una serie.

Nuevo archivo de pruebas
`investmentops/tests/test_data_layer_normalization_news.py`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_layer_normalization_news.py`

Modificados:
- `investmentops/data_layer/normalization.py` (nueva función `news_from_raw`
  y ampliación del docstring del módulo; sin cambios en las funciones ya
  existentes)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Normalización" → "Implementar el guardado de noticias
normalizadas en la caché local tras cada consulta", sobre la base ya
disponible en `investmentops/data_layer/cache.py` (mismo patrón ya usado
por `save_financial_statement_series` para persistir una lista de
elementos por ticker) y el modelo `News`/`news_from_raw` recién
completados.