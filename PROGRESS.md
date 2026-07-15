# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: valoración → *"Escribir el archivo de
prompt del agente de valoración (fuera del código Python)."*

Antes de implementarla, se verificó que no estuviera ya satisfecha: no
existía ningún archivo `prompts/valuation.md` (solo `prompts/
financial_health.md`, del otro agente). La tarea anterior ("Implementar
el cálculo determinístico de esos múltiplos a partir del modelo
normalizado") ya estaba completa (`ValuationMetrics`/
`calculate_valuation_metrics` en `investmentops/analysis_engines/
valuation.py`), pero esta tarea de prompt sí requería trabajo nuevo: es
contenido/documentación, no código Python.

## Qué se implementó

**`prompts/valuation.md`** (nuevo) — prompt del agente de análisis de
valoración, siguiendo el mismo patrón ya usado en `prompts/
financial_health.md`:

- Describe los datos que recibirá el agente: `MarketData`
  (`price`, `market_cap`, `source`, `as_of`), `FinancialStatement`
  (`revenue`, `net_income`, `debt`, `source`, `period_end`), y los
  múltiplos ya calculados de forma determinística (`price_to_earnings`,
  `price_to_sales`), incluyendo que pueden venir como `null`/ausentes
  junto con una advertencia.
- Instruye al modelo a **interpretar, nunca recalcular ni corregir**
  `price_to_earnings` y `price_to_sales`.
- Instruye a relacionar ambos múltiplos cuando tenga sentido (ej. cuando
  P/E no está disponible por pérdidas pero P/S sí lo está), sin forzar
  conclusiones no respaldadas por los datos.
- Instruye a declarar explícitamente cuando `price_to_earnings` venga
  como `null`/ausente (beneficio neto nulo o negativo), usando la
  advertencia entregada junto con los datos.
- Prohíbe explícitamente:
  - Cualquier recomendación de compra/venta o veredicto de inversión
    (mismo principio que `prompts/financial_health.md`, conforme a
    `GOALS.md` y `ARCHITECTURE.md`, "El sistema informa, no decide").
  - Inventar o aproximar P/B y EV/EBITDA: el modelo de dominio no expone
    patrimonio (`equity`), EBITDA ni efectivo (`cash`), limitaciones ya
    documentadas en `VALUATION_METRICS.md`. El prompt instruye a declarar
    explícitamente esta ausencia en vez de omitirla en silencio.
  - Inventar cifras cuando un múltiplo viene como `null`/ausente.
  - Comparar con otras empresas o el sector (no hay datos de comparables
    en esta fase, ver `ROADMAP.md`, Fase 5).
  - Agregar análisis de salud financiera, noticias, riesgos o
    estrategias de inversión (fuera del alcance de este agente).
- Define el formato de salida esperado: texto breve en español, sin
  jerga innecesaria, dirigido a un inversionista individual sin
  formación financiera avanzada (mismo criterio que `prompts/
  financial_health.md`).

No se modificó ningún archivo Python: esta tarea es puramente de
contenido/prompt, conforme a `ARCHITECTURE.md` ("Prompts como
artefactos, no como código") y `prompts/README.md`.

## Decisiones tomadas

- **Mismo patrón que `prompts/financial_health.md`**: estructura de
  secciones (datos que recibirá, qué debe hacer, qué NO debe hacer,
  formato de salida), mismo tono, mismas prohibiciones estructurales
  (sin veredicto de compra/venta, sin inventar datos ausentes).
- **No se compara contra promedios de mercado/sector**: se instruye
  explícitamente al modelo a no hacerlo, ya que esos datos no existen
  todavía en el modelo de dominio (llegan en la Fase 5, "Comparar con
  empresas similares", ver `ROADMAP.md`).
- **Las limitaciones de P/B y EV/EBITDA se declaran en el prompt** (para
  que el propio texto de interpretación las mencione si el contexto lo
  amerita), pero la declaración *estructurada* de esas limitaciones en
  `AnalysisResult.limitations` es responsabilidad de la tarea de parseo
  (`investmentops.analysis_engines.valuation`, tarea pendiente), no de
  este prompt — mismo criterio ya aplicado con `LIQUIDITY_LIMITATION` en
  `financial_health.py`.
- **No se implementó todavía el resto del agente de valoración**
  (invocación al proveedor de IA, parseo de la respuesta): siguiendo la
  instrucción de implementar solo una tarea por conversación, y dado que
  cada una de esas piezas es una tarea separada y explícita en
  `TASKS.md`.

## Validación realizada

Revisión manual del contenido del prompt contra `VALUATION_METRICS.md`
(múltiplos y limitaciones ya decididos) y contra el patrón ya validado de
`prompts/financial_health.md`. No aplica ejecución de pruebas
automatizadas: esta tarea no introduce código Python. No se ejecutó la
suite completa en este entorno (Claude Web, sin acceso al repositorio
real).

## Archivos creados o modificados

Creados:
- `prompts/valuation.md`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`,
`VALUATION_METRICS.md`, ningún módulo de código Python existente
(`investmentops/analysis_engines/valuation.py`,
`investmentops/analysis_engines/financial_health.py`,
`investmentops/data_layer/*`, `investmentops/ai_providers/*`, etc.).

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en "Agente de análisis: valoración" es:

1. *"Implementar la invocación al proveedor de IA configurado con esos
   múltiplos + el prompt."*

Nota para la próxima conversación:
- Seguir el mismo patrón de `invoke_financial_health_agent` en
  `investmentops/analysis_engines/financial_health.py`: cargar el prompt
  con `investmentops.analysis_engines.prompts.load_prompt("valuation")`,
  resolver el proveedor con `resolve_agent_provider("valuation", cfg)`,
  construir la instancia con `build_ai_provider(...)`, e invocar
  `AIProvider.complete(prompt, data=...)` enviando el `MarketData`, el
  `FinancialStatement` y las `ValuationMetrics` ya calculadas como
  `data` (nunca dejar que la IA calcule o corrija `price_to_earnings`/
  `price_to_sales`).
- El identificador de agente (`AGENT_ID`) debe ser `"valuation"`,
  consistente con el nombre del prompt (`prompts/valuation.md`) y con
  `[agents]` en `config.example.toml` (que ya trae
  `# valuation = "default"` como ejemplo comentado).
- Reutilizar la infraestructura ya existente
  (`investmentops.ai_providers.selection.resolve_agent_provider`,
  `investmentops.ai_providers.factory.build_ai_provider`,
  `investmentops.analysis_engines.prompts.load_prompt`) sin modificarla.
