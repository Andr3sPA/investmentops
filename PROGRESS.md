# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 4, "Orquestador" → "Incluir el nuevo resultado en el 'Resultado de
investigación'" (TASKS.md).

### Qué se implementó

`investigate` (`investmentops/core/orchestrator.py`) ahora también invoca
`run_news_relevance_engine(ticker, config=config, provider=news_provider)`,
en un `try/except` independiente de los ya existentes para salud
financiera, valoración y tendencia, capturando
`DataProviderError`/`NormalizationError` y traduciéndolas a
`ResearchFailure(stage="data_provider", identifier="news_relevance",
reason=<mensaje>)`, sin detener el resto del flujo.

A diferencia del motor de tendencia (que reutiliza el mismo `provider`
de datos fundamentales ya recibido por `investigate`, comprobando
`hasattr(provider, "fetch_historical")`), el motor de noticias
relevantes necesita un proveedor de un tipo distinto (`FMPNewsProvider`,
no `FMPFundamentalsProvider`). Por eso `investigate` gana un parámetro
nuevo y separado, `news_provider: FMPNewsProvider | None = None`,
independiente de `provider`. El motor se intenta si:

- `news_provider` se inyecta explícitamente (típicamente en pruebas), o
- `provider` (datos fundamentales) tampoco se inyectó — uso real, sin
  proveedores de prueba, en cuyo caso `run_news_relevance_engine`
  construye su propio `FMPNewsProvider` real por defecto.

En cualquier otro caso (un `provider` de prueba inyectado sin
`news_provider`), el motor de noticias no se intenta, sin registrarse
como fallo — mismo criterio ya usado para el motor de tendencia. Esto
preserva sin cambios el comportamiento de todas las pruebas de
`investigate` ya existentes en `test_core_orchestrator.py`.

`investigate_and_generate_reports` también gana y propaga el mismo
parámetro `news_provider`.

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_news_integration.py`

Modificados:
- `investmentops/core/orchestrator.py` (`investigate` gana el parámetro
  `news_provider` e invoca `run_news_relevance_engine`;
  `investigate_and_generate_reports` gana y propaga el mismo parámetro;
  docstrings actualizados; ninguna función existente cambió su firma de
  forma incompatible — `news_provider` es un nuevo parámetro opcional
  con valor por defecto `None`)
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Reportes" → "Añadir la sección 'Noticias recientes relevantes'
a la plantilla Markdown."