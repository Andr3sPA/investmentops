# Revisión: ninguna sección fusiona las lecturas en un veredicto único (Fase 6)

Cubre la tarea "Revisar que ninguna sección fusiona las lecturas en una
única recomendación o veredicto" (TASKS.md, Fase 6, "Reportes").

Esta tarea es de **revisión/documentación**, no de código: audita el
estado actual del sistema (prompts, generadores de reporte, pruebas ya
existentes) para confirmar que se cumple el principio rector de
`GOALS.md` ("nunca emite una recomendación de compra o venta ni una
decisión final") y el de `ARCHITECTURE.md` ("El sistema informa, no
decide"), específicamente en el punto donde más riesgo hay de violarlo:
la Fase 6 introduce **múltiples lecturas contrastables** (salud
financiera, valoración, value, growth, calidad) sobre la misma empresa,
y `GOALS.md` exige explícitamente que se presenten "como opiniones
contrastables entre sí, no como una única verdad" — es decir, que nunca
se fusionen en una sola conclusión.

## Qué se revisó

### 1. Prompts de los agentes que producen texto de análisis

Se revisaron los seis prompts que hoy generan o compondrían texto de
interpretación (`prompts/`):

| Prompt | Prohibición de veredicto | Restringe su alcance al propio marco |
|---|---|---|
| `financial_health.md` | Sí, explícita | N/A (no es una "estrategia", es diagnóstico general) |
| `valuation.md` | Sí, explícita | N/A |
| `value.md` | Sí, explícita | Sí: "no presentes esta lectura como la única perspectiva válida" |
| `growth.md` | Sí, explícita | Sí: mismo texto |
| `quality.md` | Sí, explícita | Sí: mismo texto, y distingue explícitamente su lectura del diagnóstico general de salud financiera (Fase 1) |
| `report.md` (agente de reporte, prompt ya escrito, agente aún no invocado) | Sí, explícita | Sí: "no resumas los distintos análisis en una única conclusión o puntuación agregada (ej. 'en general, la empresa obtiene una calificación de 7/10')... cada análisis debe seguir siendo reconocible como una lectura independiente" |

Los tres prompts de estrategia (`value`/`growth`/`quality`) comparten,
palabra por palabra, la misma instrucción de no presentarse como la
única perspectiva válida ni como un resumen general de la empresa —
exactamente lo que exige `GOALS.md` sobre "opiniones contrastables, no
una única verdad".

### 2. Generadores de reporte (`investmentops/reports/markdown.py`, `investmentops/reports/html.py`)

- Cada una de las ocho secciones del reporte individual (salud
  financiera, valoración, evolución de ingresos y beneficios, noticias
  recientes relevantes, comparables del sector, y las tres subsecciones
  de estrategia) se renderiza de forma **independiente**, con su propio
  encabezado (`## `/`<h2>` para las cinco primeras, `### `/`<h3>` para
  cada estrategia dentro de "Lecturas por estrategia de inversión").
- No existe, en ninguno de los dos generadores, ningún paso posterior
  que combine el contenido de varias secciones en una sola cifra, texto
  o etiqueta (ej. una puntuación agregada, un semáforo, o una frase de
  cierre tipo "en conclusión..."). `render_markdown`/`render_html`
  simplemente concatenan las secciones en orden fijo; no hay ninguna
  función de "síntesis final" en ninguno de los dos módulos.
- `_render_analysis_body`/`_render_analysis_body_html` (reutilizada,
  sin modificación, tanto por "Salud financiera"/"Valoración" como por
  las tres subsecciones de estrategia) procesa **un único**
  `AnalysisResult` a la vez: no tiene forma de mezclar el contenido de
  dos análisis distintos, ya que ni siquiera recibe más de uno como
  argumento.
- El reporte de comparación (`render_markdown_comparison`/
  `render_html_comparison`, Fase 5) tampoco introduce ninguna síntesis:
  anida el reporte individual completo de cada empresa (con sus ocho
  secciones intactas) bajo un documento superior, sin ningún cálculo
  comparativo adicional propio (esa comparación ya vive, por separado,
  en el motor de comparables, `investmentops.analysis_engines.comparables`,
  que tampoco resume en un veredicto: ver `assemble_comparables_analysis`,
  que reporta posición relativa por métrica, `"por_encima"`/`"por_debajo"`/
  `"igual"`, nunca una recomendación).

### 3. Pruebas ya existentes que verifican esto explícitamente

- `test_render_does_not_merge_strategies_into_a_single_reading`
  (`investmentops/tests/test_reports_markdown_strategies.py` y su
  equivalente en `test_reports_html_strategies.py`): confirma que un
  hallazgo exclusivo de una estrategia (`value`) no aparece dentro del
  rango de texto de otra estrategia (`growth`).
- `test_render_keeps_empty_strategy_subsections_when_agents_absent`:
  confirma que cada estrategia mantiene su propio encabezado vacío si no
  se completó, en vez de omitirse o fusionarse con las demás.
- `test_render_includes_real_ai_provenance_for_each_strategy`: confirma
  que cada estrategia expone su propia procedencia de IA
  (`ai_provider`/`ai_model`/`generated_at`), reforzando que son
  interpretaciones separadas y trazables por separado, no un texto único
  de origen mixto.

## Conclusión

No se encontró ningún punto del sistema —ni en los prompts, ni en el
cálculo determinístico de métricas, ni en los generadores de reporte,
ni en el orquestador— que combine las distintas lecturas (salud
financiera, valoración, evolución, noticias, comparables, value,
growth, calidad) en una única recomendación, puntuación agregada o
veredicto de inversión. El diseño ya vigente (una sección/subsección
por lectura, cada una con su propio encabezado, sus propios hallazgos y
su propia procedencia, sin ningún paso de síntesis posterior) satisface
por construcción el requisito de esta tarea, reforzado por las pruebas
ya existentes citadas arriba.

No se requirió ningún cambio de código para esta tarea: es una
auditoría que confirma un comportamiento ya correcto, documentada aquí
para que quede como registro explícito (mismo criterio ya aplicado en
otras tareas de revisión/decisión del proyecto, ej. `STRATEGIES.md`,
`TREND_INTEGRATION.md`).

## Fuera de alcance de esta tarea

- Cualquier cambio de código: no se detectó ningún problema que lo
  requiriera.
- La verificación manual con una empresa real de que las lecturas
  aparecen "una junto a otra, sin mezclarse" (tarea separada, ver
  TASKS.md, Fase 6, "Verificación").