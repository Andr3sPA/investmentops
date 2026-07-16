# Secciones del reporte (Fase 2)

Cubre la tarea "Definir qué secciones tendrá el reporte (identidad de la
empresa, salud financiera, valoración, fuentes y fecha de cada dato,
incluyendo qué proveedor de IA generó cada interpretación)" (TASKS.md,
Fase 2, "Modelo de reporte").

Esta tarea es de **diseño/documentación**, no de código: fija el orden y
el contenido exacto de cada sección del reporte, sobre la base ya
decidida en `investmentops/reports/REPORT_MODEL.md` (los generadores
consumen `ResearchResult` directamente, sin un tipo intermedio nuevo).
La implementación de la primera plantilla concreta (Generador Markdown)
es la tarea siguiente en esta misma sección de `TASKS.md`.

## Orden y contenido de las secciones

Los tres formatos previstos (Markdown, HTML, y JSON si aplica en el
futuro) presentan el mismo contenido, en el mismo orden. El orden ya lo
sigue, de hecho, `investmentops.cli.format_research_result` (Fase 1,
texto plano de consola); esta tarea simplemente lo fija como la
estructura oficial que reutilizarán los generadores de reporte de la
Fase 2, sin que cada generador tenga que redecidir el orden por su
cuenta.

### 1. Encabezado — Identidad de la empresa

- **Fuente:** `ResearchResult.company` (`Company`: `ticker`, `name`,
  `sector`, `market`) y `ResearchResult.generated_at`.
- **Contenido:** ticker de la empresa investigada (siempre presente) y
  la fecha/hora en que se ensambló la investigación. `name`, `sector` y
  `market` se muestran si no están vacíos; en la Fase 1 estos tres
  campos están siempre vacíos (`assemble_research_result` construye una
  `Company` mínima, ver `investmentops/core/orchestrator.py`), por lo que
  en la práctica el encabezado de Fase 2 mostrará solo el ticker y la
  fecha hasta que una fuente de datos futura complete esos campos (fuera
  de alcance de esta tarea).

### 2. Salud financiera

- **Fuente:** el `AnalysisResult` de `ResearchResult.analysis_results`
  con `analysis_id == "financial_health"`, si está presente.
- **Contenido, en este orden:**
  1. Hallazgos (`findings`): el texto de interpretación del agente.
  2. Métricas de soporte (`supporting_metrics`): `net_margin`,
     `debt_to_revenue`, mostradas como par clave-valor.
  3. Limitaciones (`limitations`): siempre incluye la limitación de
     liquidez (ver `LIQUIDITY_LIMITATION`); se omite la sub-sección
     completa solo si la lista está vacía (no ocurre en la práctica para
     este agente).
  4. Procedencia de la interpretación de IA (`provenance`): proveedor y
     modelo (`ai_provider`, `ai_model`).
- **Si el agente no completó su análisis:** la sección se omite (no se
  imprime un encabezado vacío); el fallo correspondiente aparece en la
  sección 4 ("Fallos parciales").

### 3. Valoración

- **Fuente:** el `AnalysisResult` con `analysis_id == "valuation"`.
- **Contenido:** mismo orden y estructura que "Salud financiera"
  (hallazgos → métricas de soporte `price_to_earnings`/`price_to_sales`
  → limitaciones, incluyendo siempre P/B y EV/EBITDA → procedencia de
  IA).
- **Si el agente no completó su análisis:** igual criterio que la
  sección anterior.

### 4. Fallos parciales (solo si existen)

- **Fuente:** `ResearchResult.failures` (`ResearchFailure`: `stage`,
  `identifier`, `reason`).
- **Contenido:** una entrada por fallo, indicando en qué etapa ocurrió
  (`"data_provider"` o `"analysis_engine"`), qué falló concretamente
  (identificador del proveedor o del agente) y el motivo. Esta sección
  se omite por completo si `failures` está vacío, nunca se muestra un
  encabezado sin contenido.

## Limitación documentada: no hay fuente/fecha del dato normalizado subyacente

`TASKS.md` pide que el reporte muestre "fuentes y fecha de cada dato,
incluyendo qué proveedor de IA generó cada interpretación". Lo segundo
(procedencia de la interpretación de IA) ya está cubierto en cada sección
de análisis vía `AnalysisResult.provenance` (`AnalysisProvenance`).

Lo primero (fuente y fecha del **dato financiero/de mercado en sí**, ej.
`FinancialStatement.source`/`period_end`, `MarketData.source`/`as_of`)
**no** está disponible hoy en `ResearchResult`: esos modelos normalizados
(`NormalizedCompanyData`, ver `investmentops/core/orchestrator.py`) se
consumen internamente por los agentes de análisis para calcular sus
métricas, pero no se propagan hacia el `ResearchResult` final. Esto no es
un descuido de esta tarea: ya estaba así desde la Fase 1 (`ResearchResult`
solo agrega `AnalysisResult`, no los modelos normalizados de entrada).

Para el MVP de Fase 2, esta ausencia se documenta como una limitación
explícita en vez de inventar un dato o rediseñar `ResearchResult` sin un
caso de uso concreto que lo justifique (mismo criterio de "no
sobre-diseñar antes de tener el caso de uso real" ya aplicado en
`investmentops/data_layer/market_data.py` y otros módulos del proyecto):
en la Fase 1, todos los datos financieros y de mercado de una
investigación provienen de un único proveedor fijo (FMP, ver
`investmentops/data_providers/fundamentals.py`), por lo que la "fuente"
es implícitamente uniforme y conocida para todo el reporte, aunque no se
muestre explícitamente dato por dato.

Si en una fase futura se agregan múltiples proveedores de datos
fundamentales (no previsto en `ROADMAP.md` antes de Fase 5,
"comparables"), esta limitación debería resolverse extendiendo
`ResearchResult` (o `AnalysisResult`) para propagar la fuente/fecha del
dato normalizado subyacente — una tarea explícita y separada, no
anticipada aquí.

## Fuera de alcance de esta tarea

- La implementación de cualquier plantilla concreta (Markdown, HTML):
  tareas separadas y posteriores ("Generador Markdown", "Generador
  HTML").
- Resolver la limitación de fuente/fecha del dato normalizado subyacente
  (ver sección anterior): documentada explícitamente, no resuelta aquí.
- El agente de reporte opcional: tarea separada en la misma sección de
  `TASKS.md`.
- Completar `Company.name`/`sector`/`market` con datos reales: fuera de
  alcance de esta tarea (ver `investmentops/core/orchestrator.py`).
