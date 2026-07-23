# investmentops/analysis_engines/STRATEGIES.md
# Lecturas por estrategia de inversión — estrategias a cubrir en el MVP (Fase 6)

Cubre la tarea "Listar las estrategias/escuelas de inversión a cubrir en
el MVP (ej. value, growth, calidad)" (TASKS.md, Fase 6, "Diseño de
estrategias").

Esta tarea es de **decisión/documentación**, no de código: fija cuántas
y cuáles estrategias/escuelas de inversión implementará el MVP de esta
fase, antes de la tarea siguiente ("Para cada estrategia, definir de
forma breve qué datos del modelo de dominio utiliza y qué pregunta
responde") y de las tareas de implementación de cada motor (prompt →
invocación → parseo, ver TASKS.md, "Motores de análisis por
estrategia").

## Contexto: qué ya pide `ROADMAP.md`/`GOALS.md`

`ROADMAP.md`, Fase 6: *"Se agregan agentes de análisis adicionales, uno
por estrategia/escuela de inversión, cada uno con su propio prompt
(archivo independiente) que encapsula el marco de esa estrategia, todos
consumiendo el mismo modelo de dominio ya existente."* Y `GOALS.md`,
pregunta 8 del MVP: *"¿Qué dirían distintas estrategias o escuelas de
inversión sobre esta empresa?"*, con el objetivo de *"presentadas como
opiniones contrastables entre sí, no como una única verdad"*.

`TASKS.md` ya anticipa, en el desglose original de "Motores de análisis
por estrategia", tres ejemplos concretos de estrategia: **value**,
**growth** y **calidad** — cada una con sus propias tres tareas ya
desglosadas (prompt → invocación al proveedor de IA → parseo de la
respuesta), siguiendo exactamente el mismo patrón ya usado en la Fase 1
para los agentes de salud financiera y valoración.

## Decisión: tres estrategias para el MVP — value, growth, calidad

Se confirman, sin agregar ni quitar ninguna, las **tres** estrategias ya
anticipadas en `TASKS.md`:

1. **Value investing** (`value`) — lectura centrada en si la empresa
   cotiza "barata" en relación con sus propios fundamentales (múltiplos
   de valoración ya calculados, margen y endeudamiento), en la tradición
   de análisis de valor.
2. **Growth investing** (`growth`) — lectura centrada en la evolución y
   el ritmo de crecimiento de ingresos/beneficios en el tiempo, más que
   en cuán "barata" esté la empresa hoy.
3. **Calidad** (`quality`) — lectura centrada en la solidez financiera
   subyacente (rentabilidad, nivel de endeudamiento) como proxy de
   "calidad" del negocio, independientemente de su valoración o su
   ritmo de crecimiento actual.

No se agrega una cuarta estrategia (ej. "momentum", "dividendos",
"contrarian") para el MVP: `TASKS.md` no las anticipa, y agregarlas
ahora sería introducir alcance nuevo no pedido por esta tarea ni por
`ROADMAP.md`/`GOALS.md` (que solo piden "distintas estrategias o
escuelas", sin fijar una lista cerrada más allá de los tres ejemplos ya
usados en `TASKS.md`).

## Por qué estas tres y no otras

- **Cobertura sin fuentes de datos nuevas.** Las tres se pueden
  implementar reutilizando exclusivamente modelos de dominio ya
  normalizados desde fases anteriores (`FinancialStatement`,
  `MarketData`, `FinancialStatementSeries`) y, cuando aplica, métricas
  ya calculadas de forma determinística por agentes/motores ya
  existentes (`calculate_financial_health_metrics`,
  `calculate_valuation_metrics`, `assemble_trend_analysis`). Consistente
  con `ROADMAP.md`, Fase 6: *"cada uno... consumiendo el mismo modelo de
  dominio ya existente"* — ninguna estrategia requiere una fuente de
  datos nueva.
- **Cubren ángulos claramente distintos y no redundantes entre sí**: value
  (¿está cara o barata hoy?), growth (¿cómo evoluciona en el tiempo?) y
  calidad (¿qué tan sólida es, independientemente del precio o del
  crecimiento?). Esto es justamente lo que pide `GOALS.md`: opiniones
  contrastables, no la misma lectura repetida con otro nombre.
- **Ya estaban anticipadas y desglosadas en `TASKS.md`** con el mismo
  patrón de tres tareas por estrategia (prompt, invocación, parseo) ya
  usado en la Fase 1: no hay que rediseñar el desglose de tareas, solo
  confirmar la decisión antes de ejecutarlas.

## Qué NO se decide en esta tarea

- Qué datos concretos del modelo de dominio usa cada estrategia y qué
  pregunta responde: tarea siguiente y separada de esta misma sección
  ("Para cada estrategia, definir de forma breve qué datos del modelo de
  dominio utiliza y qué pregunta responde").
- El contenido de los prompts de cada estrategia: tareas separadas y
  posteriores en "Motores de análisis por estrategia".
- Cómo se registran estos motores en el orquestador o se presentan en
  los reportes: tareas separadas y posteriores de esta misma fase.

## Fuera de alcance de esta tarea

- Cualquier cálculo determinístico nuevo: `ROADMAP.md` ya aclara que
  estos motores "interpretan datos ya existentes, sin nuevas fuentes",
  por lo que no se anticipa aquí ningún módulo de métricas nuevo (a
  diferencia de `FINANCIAL_HEALTH_METRICS.md`/`VALUATION_METRICS.md`,
  que sí definían métricas nuevas a calcular).
- La implementación de cualquier agente concreto (prompt, invocación,
  parseo): tareas separadas y posteriores.