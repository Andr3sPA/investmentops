# PROGRESS.md

**Última actualización:** 2026-07-22

## Última tarea completada

Fase 5, "Orquestador y CLI" → "Conectar el comando CLI de comparación
con esa función del orquestador." (TASKS.md).

### Qué se implementó

`investmentops/cli/__init__.py` (modificado): `dispatch` ahora reconoce
`args.command == "compare"`, invocando
`investmentops.core.orchestrator.compare(args.tickers, config=config,
provider=provider)` (ya implementada en la tarea anterior de esta misma
sección) y devolviendo el `ComparisonResult` obtenido tal cual, sin
transformarlo. Se importan `compare`/`ComparisonResult` desde
`investmentops.core.orchestrator`. Se amplió la anotación de tipo de
retorno de `dispatch` a `ResearchResult | tuple[ResearchResult,
list[Path]] | ComparisonResult`. No se propaga ningún `news_provider`
desde `dispatch` (mismo criterio que la rama ya existente de
`"investigate"`, que tampoco lo hace); `compare` ya usa
`news_provider=None` por defecto internamente para cada
`investigate(...)` que ejecuta. No se modificó el comportamiento
existente de `dispatch` para `"investigate"`, ni `format_research_result`
(formatear un `ComparisonResult` en consola es una tarea separada,
todavía pendiente en la sección "Reportes" de esta misma fase).

`investmentops/tests/test_cli_dispatch_compare.py` (nuevo): cubre que
`dispatch` devuelve un `ComparisonResult` para el subcomando `compare`,
que propaga cada ticker al proveedor inyectado en el mismo orden y sin
normalizar, y que un fallo de proveedor para un ticker no impide
completar la investigación de los demás (tanto "uno falla" como "todos
fallan").

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_cli_dispatch_compare.py`

Modificados:
- `investmentops/cli/__init__.py`
- `TASKS.md` (una línea: tarea marcada como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Reportes":
- "Añadir la sección 'Comparables del sector' a la plantilla Markdown."