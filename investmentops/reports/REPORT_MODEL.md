# Modelo de reporte — estructura común para los generadores (Fase 2)

Cubre la tarea "Definir la estructura común que consumirán los
generadores (a partir del 'Resultado de investigación')" (TASKS.md, Fase
2, "Modelo de reporte").

Esta tarea es de **diseño/documentación**, no de código: decide qué
estructura de entrada usarán los generadores de reportes (Markdown, HTML,
y JSON en fases posteriores si aplica), antes de implementar las
plantillas concretas (próximas tareas de esta misma sección).

## Decisión: reutilizar `ResearchResult` tal cual, sin una estructura intermedia nueva

Los generadores de reportes (`investmentops.reports`, ver
ARCHITECTURE.md, componente 6) consumirán directamente el
`ResearchResult` ya definido en
`investmentops/core/research_result.py` (Fase 1, "Contratos e
interfaces"), **sin** introducir un tipo intermedio nuevo (ej.
`ReportInput`, `ReportData`) entre el orquestador y los generadores.

Esto no es una omisión: es la decisión explícita de esta tarea. Se
documenta aquí para que ninguna conversación futura reintroduzca una
estructura redundante sin saber que ya se evaluó y se descartó.

## Por qué `ResearchResult` ya es esa estructura

`ARCHITECTURE.md`, "Modelo de datos interno (conceptual)", ya es
explícito al respecto:

> "Resultado de investigación — agregación de todos los resultados de
> análisis para una empresa en un momento dado; **es lo que finalmente
> consumen los generadores de reportes**."

Y el propio docstring de `investmentops/core/research_result.py` (Fase 1)
ya anticipa este uso:

> "Es, a su vez, el tipo que consumirán los generadores de reportes
> (investmentops.reports, aún sin implementar, ver TASKS.md Fase 2)."

`ResearchResult` (y los tipos que agrega) ya expone todo lo que
`ROADMAP.md` (Fase 2) y `TASKS.md` (sección "Modelo de reporte", tarea
siguiente) piden como secciones del reporte:

| Sección del reporte (ver TASKS.md, tarea siguiente)         | De dónde sale en `ResearchResult`                                  |
|--------------------------------------------------------------|----------------------------------------------------------------------|
| Identidad de la empresa                                      | `ResearchResult.company` (`Company`: ticker, name, sector, market)  |
| Salud financiera                                              | El `AnalysisResult` de `analysis_results` con `analysis_id == "financial_health"` |
| Valoración                                                    | El `AnalysisResult` de `analysis_results` con `analysis_id == "valuation"` |
| Fuentes y fecha de cada dato / qué proveedor de IA generó cada interpretación | `AnalysisResult.provenance` (`AnalysisProvenance`: `ai_provider`, `ai_model`, `generated_at`) de cada análisis |
| Fallos/limitaciones explícitas                                 | `AnalysisResult.limitations` (por análisis) y `ResearchResult.failures` (`ResearchFailure`: fuente de datos o agente que no pudo completarse) |

No hay ningún dato que un generador necesite (Markdown u HTML) que
`ResearchResult` no exponga ya. Introducir un tipo intermedio
"aplanado" o "de presentación" sería una capa de indirección sin
beneficio real en este punto: los tres formatos de salida previstos
(Markdown, HTML, JSON) pueden recorrer directamente
`result.company`, `result.analysis_results` y `result.failures`.

## Consistencia con el resto del proyecto

Esta decisión sigue el mismo criterio de "no sobre-diseñar antes de
tener el caso de uso real" ya aplicado repetidamente en el proyecto (ver
por ejemplo `investmentops/data_layer/market_data.py`, que decide no
extender `MarketData` a series históricas hasta que exista una fuente de
datos real que lo justifique). Aquí, introducir una estructura de
reporte separada de `ResearchResult` antes de escribir la primera
plantilla concreta (la tarea siguiente en `TASKS.md`) sería anticipar una
necesidad que no se ha demostrado todavía. Si en el futuro un generador
concreto necesita un dato derivado que `ResearchResult` no expone (por
ejemplo, un resumen agregado calculado a partir de varios
`AnalysisResult`), esa sería una extensión explícita y posterior de esta
decisión, no algo que deba anticiparse aquí.

## Fuera de alcance de esta tarea

- Qué secciones concretas tendrá el reporte y en qué orden se presentan:
  tarea separada y siguiente en la misma sección de `TASKS.md` ("Definir
  qué secciones tendrá el reporte...").
- La implementación de cualquier plantilla concreta (Markdown, HTML):
  tareas separadas y posteriores ("Generador Markdown", "Generador
  HTML").
- El agente de reporte opcional (redacción narrativa a partir de los
  resultados ya existentes): tarea opcional separada, también en
  `TASKS.md`, Fase 2, "Modelo de reporte".
- Cualquier serialización a JSON de `ResearchResult` (relevante para un
  futuro formato de salida JSON): no es parte de esta tarea de diseño;
  se abordará, si aplica, como parte de la implementación de ese
  generador concreto.
