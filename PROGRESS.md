# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Fuente de datos de noticias" → "Adjuntar metadatos de
procedencia (fuente, fecha de publicación, fecha de consulta) a cada
noticia cruda" (TASKS.md).

### Qué se implementó

`_attach_news_provenance` en `investmentops/data_providers/news.py`
(ver PROGRESS.md anterior para el contexto de `FMPNewsProvider`):

- `FMPNewsProvider.fetch` ahora adjunta, a cada elemento de la lista
  cruda que devuelve el endpoint `/stock_news` de FMP, las claves
  `"source"` (mismo valor que `RawProviderData.metadata.source`,
  `"fmp"`) y `"queried_at"` (mismo valor que
  `RawProviderData.metadata.queried_at`, serializado a ISO 8601).
- La fecha de publicación de cada noticia (`"publishedDate"`) no
  requirió ningún cambio: ya venía incluida en cada elemento crudo desde
  la tarea anterior, tal como la entrega FMP.
- `_attach_news_provenance` construye una lista nueva de dicts (no muta
  las respuestas originales de `response.json()`), mismo criterio ya
  aplicado por `_attach_point_provenance` en
  `investmentops/data_providers/fundamentals.py` para la serie
  histórica de estados financieros.
- El caso de lista vacía (empresa sin noticias recientes) sigue
  comportándose igual: `_attach_news_provenance` sobre una lista vacía
  devuelve una lista vacía, sin error.

Nuevo archivo de pruebas
`investmentops/tests/test_data_providers_news_provenance.py`, cubriendo:
procedencia por noticia (`source`/`queried_at`), coincidencia con el
`ProviderMetadata` de nivel superior, preservación de los campos
originales de FMP (incluyendo `publishedDate`), no mutación de los
dicts originales, mismo `queried_at` compartido por todas las noticias
de una misma consulta, y manejo correcto de una respuesta vacía.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_providers_news_provenance.py`

Modificados:
- `investmentops/data_providers/news.py` (`_attach_news_provenance`,
  `fetch` actualizado para usarla)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Fuente de datos de noticias" → "Implementar manejo de error si
el proveedor de noticias falla o no devuelve resultados", sobre
`FMPNewsProvider.fetch` ya implementado en
`investmentops/data_providers/news.py`.