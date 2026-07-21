# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Fuente de datos de noticias" → "Implementar manejo de error si
el proveedor de noticias falla o no devuelve resultados" (TASKS.md).

### Qué se implementó

`FMPNewsProvider.fetch` en `investmentops/data_providers/news.py`:

- El manejo de "falla" (fallo de red, API key inválida, errores de
  servidor ≥400, JSON no parseable) ya estaba cubierto desde la tarea
  anterior de esta misma sección — no requirió cambios.
- Se agregó la validación de que el JSON ya parseado (`raw_items`) tenga
  la forma esperada: una lista. Si FMP responde `200` con un cuerpo JSON
  válido pero que no es una lista (ej. un objeto de error como
  `{"Error Message": "Invalid API KEY"}`, patrón real de FMP ante
  credenciales inválidas que no siempre viene acompañado de un código
  HTTP de error), se levanta `DataProviderError` identificando el
  ticker afectado, en vez de dejar escapar una excepción no controlada
  al intentar adjuntar procedencia sobre un valor no iterable como se
  esperaba.
- `None`/`null` sigue tratándose como lista vacía (sin noticias
  recientes), no como error: se preserva explícitamente el criterio ya
  fijado en la tarea anterior de que "no devuelve resultados" (lista
  vacía) es una respuesta válida, distinta de un fallo real.

Nuevo archivo de pruebas
`investmentops/tests/test_data_providers_news_error_handling.py`,
cubriendo: objeto de error de FMP en vez de lista, un string plano en
vez de lista, `null` tratado como lista vacía (no como error), y que el
mensaje de error identifica el ticker afectado.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_data_providers_news_error_handling.py`

Modificados:
- `investmentops/data_providers/news.py` (`fetch`: validación de forma
  de `raw_items`)
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Normalización" → "Definir el modelo de dominio 'Noticias'
(fecha, fuente, resumen)", sobre la base ya disponible en
`investmentops/data_providers/news.py` (`FMPNewsProvider.fetch`).