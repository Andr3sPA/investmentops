# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 2, "Modelo de reporte" → "(Opcional) Escribir el archivo de prompt
del agente de reporte y definir su alcance: solo redacción a partir de
los resultados ya existentes, sin nuevos hallazgos ni veredictos"
(TASKS.md).

### Qué se implementó

`prompts/report.md` (nuevo), siguiendo la misma convención ya usada por
`prompts/financial_health.md` y `prompts/valuation.md` (ver
`prompts/README.md`): un archivo de prompt en Markdown, fuera del código
Python, con instrucciones para un futuro agente de reporte cuya única
función es **redactar** (no analizar) a partir del `ResearchResult` ya
ensamblado.

El prompt fija el alcance decidido en `ARCHITECTURE.md` (componente 6,
"agente de reporte... compone el texto final a partir de los resultados
estructurados ya producidos... no introduce hallazgos nuevos ni resume
los resultados en un veredicto de compra/venta"):

- Recibe el `ResearchResult` ya ensamblado (identidad de la empresa,
  `AnalysisResult` por cada análisis completado — hallazgos, métricas de
  soporte, limitaciones, procedencia — y cualquier `ResearchFailure`
  parcial).
- Redacta un texto continuo, integrando hallazgos y limitaciones ya
  declaradas, sin agregar cifras ni interpretaciones nuevas.
- Prohíbe explícitamente fusionar los distintos análisis en una única
  conclusión/puntuación agregada (mismo principio de `GOALS.md`:
  presentar lecturas como opiniones contrastables, no como una única
  verdad) y cualquier recomendación de compra/venta o veredicto de
  inversión.

### Decisión de implementación

Esta tarea es explícitamente opcional y de alcance limitado a "escribir
el archivo de prompt... y definir su alcance": no se implementó ningún
código que invoque este prompt (ni una función `invoke_report_agent`, ni
su parseo a un resultado estructurado, ni su conexión con
`generate_reports`/`render_markdown`/`render_html`). Esa implementación,
si se decide hacer en el futuro, sería una tarea nueva y explícita, no
anticipada aquí (mismo criterio de "no sobre-diseñar antes de tener el
caso de uso real" ya aplicado en el resto del proyecto).

## Archivos creados o modificados

Creados:
- `prompts/report.md`

Modificados:
- `TASKS.md` (una línea: tarea de prompt del agente de reporte marcada
  como completada)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 4, "Motor de análisis: noticias relevantes" → "Ensamblar el
resultado estructurado del motor (hallazgos, lista de noticias
relevantes, advertencias si no hay noticias)".