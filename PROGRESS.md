# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Implementar en el orquestador la función
que ejecuta la investigación de cada empresa involucrada en una
comparación y ensambla sus resultados individuales en un resultado
comparativo, reutilizando el flujo de investigación ya existente."
(TASKS.md).

### Qué se implementó

`investmentops/core/orchestrator.py` (modificado): se agregan dos piezas
nuevas al final del módulo, sin tocar nada existente:

- `ComparisonResult` (dataclass inmutable): contenedor simple
  `{tickers: Sequence[str], results: Sequence[ResearchResult]}`. Definido
  en `investmentops.core.orchestrator` (no en
  `investmentops.core.research_result`, junto a `ResearchResult`/
  `ResearchFailure`), mismo criterio de ubicación ya aplicado a
  `NormalizedCompanyData`/`PeerMetrics`: es una agregación puntual del
  orquestador para el flujo de CLI `compare`, no parte del modelo de
  dominio interno definido en la Fase 1.
- `compare(tickers, *, config=None, provider=None, news_provider=None) ->
  ComparisonResult`: invoca `investigate(ticker, ...)` (sin modificarla)
  una vez por cada ticker de `tickers`, en el mismo orden recibido, y
  agrupa los `ResearchResult` obtenidos. No introduce ningún manejo de
  fallos adicional — un ticker problemático no detiene la comparación de
  los demás, ya que cada `ResearchResult` individual ya refleja su propio
  fallo parcial en `failures` (garantía ya existente de `investigate`).
  No calcula ningún posicionamiento relativo entre las empresas
  comparadas: esa responsabilidad ya vive, por separado, en
  `investmentops.analysis_engines.comparables`
  (`run_comparables_engine`), de la sección "Motor de análisis:
  posicionamiento relativo" de esta misma fase, todavía no conectada con
  este flujo.

`investmentops/tests/test_core_orchestrator_compare.py` (nuevo): cubre
`compare` devolviendo un `ResearchResult` por ticker en el orden
recibido, propagando cada ticker al proveedor inyectado, capturando
fallos de proveedor sin propagar la excepción (tanto "todos fallan" como
"uno falla y los demás no se ven afectados"), y confirmando que
`ComparisonResult.tickers` conserva los tickers tal cual se recibieron
(sin normalizar).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_core_orchestrator_compare.py`

Modificados:
- `investmentops/core/orchestrator.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Orquestador y CLI":
- "Conectar el comando CLI de comparación con esa función del
  orquestador." Extendería `investmentops.cli.dispatch` para reconocer
  `args.command == "compare"` (hoy levanta `ValueError`), invocando
  `investmentops.core.orchestrator.compare(args.tickers, config=config,
  provider=provider, news_provider=news_provider)` y devolviendo el
  `ComparisonResult` obtenido, sin modificar el comportamiento ya
  existente de `dispatch` para `"investigate"`.