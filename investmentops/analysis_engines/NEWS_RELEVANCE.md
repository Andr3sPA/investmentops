# investmentops/analysis_engines/NEWS_RELEVANCE.md
# Noticias relevantes — criterio básico de relevancia/filtrado (Fase 4)

Cubre la tarea "Definir el criterio básico de relevancia/filtrado de
noticias para el MVP (ej. ventana de tiempo reciente)" (TASKS.md, Fase
4, "Motor de análisis: noticias relevantes").

Esta tarea es de **diseño/documentación**, no de código: decide qué
hace que una noticia se considere "relevante" para el MVP, antes de
implementar el filtrado real (tarea siguiente de esta misma sección,
"Implementar el filtrado de noticias según ese criterio"), a partir de
los campos que **hoy** expone el modelo de dominio normalizado `News`
(`investmentops/data_layer/news.py`): `title`, `summary`, `source`,
`published_at`, `url`.

## Qué hay disponible para decidir relevancia

`FMPNewsProvider.fetch` (ver `investmentops/data_providers/news.py` y
`NEWS_PROVIDER.md`) ya devuelve, para el ticker consultado, hasta
`DEFAULT_LIMIT` (50) noticias, ordenadas tal como las entrega FMP (no
garantizado por fecha descendente ni por ningún criterio de relevancia
propio: FMP no calcula relevancia ni sentimiento — decisión deliberada
de `NEWS_PROVIDER.md`, "Sin análisis de sentimiento de terceros"). Cada
noticia normalizada (`News`) trae:

- `title`, `summary`: contenido textual de la noticia.
- `source`: el medio que la publicó (ej. `"Reuters"`).
- `published_at`: fecha y hora de publicación (con granularidad de
  minutos).
- `url`: enlace a la noticia completa.

No hay, en el modelo actual, ninguna señal de:
- Relevancia temática (¿la noticia trata sobre resultados financieros,
  litigios, cambios de gerencia, o es irrelevante para la empresa —ej.
  una mención de paso—?).
- Impacto o sentimiento (positivo/negativo/neutral).
- Popularidad o alcance de la fuente.

## Restricción de partida: no inventar una señal de relevancia que no existe

Igual que `FINANCIAL_HEALTH_METRICS.md` (liquidez, no calculable) y
`VALUATION_METRICS.md` (P/B, EV/EBITDA, no calculables), este módulo no
puede fabricar una señal de relevancia temática o de sentimiento que no
está presente en los datos: aproximarla con heurísticas de palabras
clave sin validar, o con un score inventado, sería impreciso y
engañoso, y contradice el principio ya aplicado en todo el proyecto de
declarar honestamente lo que no se puede calcular en vez de inventarlo.

La única señal objetiva y verificable que **sí** está disponible sin
inventar nada es `published_at`: cuán reciente es la noticia respecto al
momento de la investigación. Por eso el criterio de relevancia del MVP
se basa exclusivamente en esa señal.

## Decisión: ventana de tiempo reciente, sin filtrado temático

Para el MVP de esta fase, una noticia se considera **relevante** si su
`published_at` cae dentro de una **ventana de los últimos N días**
respecto al momento en que se ejecuta el análisis (no respecto a
`queried_at`, ya adjuntado por punto en el payload crudo, sino respecto
al momento del filtrado, ver "Cálculo del límite de la ventana" abajo).

- **N por defecto: 7 días.** Una semana es un horizonte razonable para
  "noticias recientes" en el contexto de investigación previa a una
  decisión de inversión (`GOALS.md`, pregunta 6: "¿Qué noticias
  recientes podrían afectarla?"), sin exigir al usuario que revise
  meses de historial cada vez que investiga una empresa. No hay hoy
  evidencia ni caso de uso que justifique un valor distinto; si en el
  futuro se determina que 7 días es muy corto o muy largo, ajustar ese
  valor es una extensión explícita y posterior, no algo que deba
  resolverse aquí con una heurística adicional.
- **Parámetro configurable, no fijo en código.** El motor que implemente
  este filtrado (tarea siguiente) debe aceptar `days` (o nombre
  equivalente) como parámetro con ese valor por defecto, siguiendo el
  mismo criterio ya usado por `period`/`limit` en
  `fetch_historical`/`fetch_and_normalize_historical` (Fase 3): un valor
  razonable por defecto, ajustable por quien invoque la función, sin
  necesidad de una clave nueva en `config.local.toml` mientras no exista
  un caso de uso real que lo requiera (mismo criterio de no
  sobre-diseñar ya aplicado en `investmentops/data_layer/CACHE.md` para
  `DEFAULT_MAX_AGE`).
- **Sin filtrado temático ni de sentimiento.** Todas las noticias dentro
  de la ventana se consideran relevantes por igual; ninguna se descarta
  ni se prioriza por su contenido, título, o fuente. Esto es
  consistente con `NEWS_PROVIDER.md` ("Sin análisis de sentimiento de
  terceros... dejando la interpretación/filtrado a los motores de
  análisis del propio sistema") y con el principio de `GOALS.md` de que
  el sistema informa y contextualiza, no decide por el usuario qué
  noticia es "más importante" sin una base objetiva para hacerlo.
- **Sin deduplicación ni agrupamiento de noticias similares.** Fuera de
  alcance del MVP: no hay hoy evidencia de que FMP devuelva duplicados
  con la frecuencia suficiente para justificar esa lógica adicional.

## Cálculo del límite de la ventana

El límite se calcula como `now - timedelta(days=N)`, donde `now` es el
momento en que se ejecuta el filtrado (no el momento en que se consultó
originalmente al proveedor, `queried_at`): esto asegura que, si una
noticia se cachea y se reutiliza varios días después (ver
`investmentops.data_layer.cache.load_news`, `DEFAULT_MAX_AGE` = 24
horas), la ventana de relevancia siempre se evalúa contra el momento
real del análisis, no contra un instante pasado. Una noticia con
`published_at` anterior al límite calculado se considera **no
relevante** para el análisis actual (queda fuera del filtrado, no se
descarta del modelo de dominio ni de la caché).

## Manejo de casos degenerados

- **Ninguna noticia dentro de la ventana** (la empresa no tuvo noticias
  recientes, o todas las disponibles son más antiguas que N días): no es
  un error. El motor de análisis (tarea de ensamblado, más adelante en
  esta misma sección) debe declararlo explícitamente como una
  limitación/advertencia, en vez de omitir la sección en silencio — mismo
  criterio ya aplicado en salud financiera (liquidez no disponible) y en
  el motor de tendencias (serie de un solo periodo).
- **Lista de noticias vacía de entrada** (ver
  `investmentops.data_providers.news`, "'No devuelve resultados' NO es
  un error"): sigue sin ser un error en esta etapa; el filtrado sobre una
  lista vacía simplemente produce una lista vacía de noticias relevantes,
  mismo resultado que "ninguna dentro de la ventana".

## Fuera de alcance de esta tarea

- La implementación real del filtrado por ventana de tiempo (tarea
  siguiente, "Implementar el filtrado de noticias según ese criterio").
- El resumen breve por noticia relevante (tarea separada y posterior de
  la misma sección: "Implementar un resumen breve por noticia relevante
  (o selección del resumen ya provisto por la fuente)").
- El ensamblado del resultado estructurado del motor (hallazgos, lista de
  noticias relevantes, advertencias si no hay noticias): tarea separada y
  posterior en la misma sección de `TASKS.md`.
- Cualquier filtrado temático, de sentimiento, de relevancia por fuente,
  o deduplicación: descartados explícitamente para el MVP (ver arriba),
  no anticipados aquí.
- El prompt del motor de análisis de noticias (si este motor delega
  interpretación a un modelo de lenguaje, siguiendo el patrón de salud
  financiera/valoración) y su invocación al proveedor de IA: no están
  desglosados todavía como tareas explícitas en `TASKS.md` para esta
  sección; se definirán si el diseño de este motor concreto lo requiere,
  mismo criterio ya aplicado por el motor de tendencias (Fase 3), que no
  invoca IA.