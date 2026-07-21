# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Normalización" → "Definir el modelo de dominio 'Noticias'
(fecha, fuente, resumen)" (TASKS.md).

### Qué se implementó

`News` en `investmentops/data_layer/news.py` (nuevo): dataclass
inmutable que representa un evento noticioso normalizado, siguiendo
exactamente el mismo patrón ya usado por `Company`, `FinancialStatement`
y `MarketData` (Fase 1/Fase 3).

Campos elegidos:

- `title`: titular de la noticia.
- `summary`: resumen/cuerpo de la noticia (el "resumen" que pide
  `ARCHITECTURE.md`).
- `source`: el medio/sitio que publicó la noticia (ej. "Reuters"),
  distinto de `ProviderMetadata.source` (el proveedor de datos, ej.
  "fmp") — mismo criterio de distinción ya aplicado por
  `FinancialStatement.source`/`MarketData.source`.
- `published_at`: fecha y hora de publicación (la "fecha" que pide
  `ARCHITECTURE.md`). Se usa `datetime`, no `date`, porque el
  `publishedDate` que entrega FMP (`FMPNewsProvider.fetch`) tiene
  granularidad de minutos, a diferencia de `period_end`/`as_of`.
- `url`: enlace a la noticia completa, para trazabilidad.

Se dejó fuera deliberadamente `queried_at` (metadato de la consulta, ya
disponible en `ProviderMetadata`/el payload crudo, no del dato de
dominio en sí) y cualquier lógica de relevancia/filtrado (responsabilidad
del futuro motor de análisis de noticias).

Re-exportado desde `investmentops/data_layer/__init__.py`. Nuevo archivo
de pruebas `investmentops/tests/test_data_layer_news.py`.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/news.py`
- `investmentops/tests/test_data_layer_news.py`

Modificados:
- `investmentops/data_layer/__init__.py` (re-exporta `News`)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Normalización" → "Implementar la transformación de noticias
crudas al modelo normalizado", sobre la base ya disponible en
`investmentops/data_providers/news.py` (`FMPNewsProvider.fetch`) y el
modelo `News` recién definido.