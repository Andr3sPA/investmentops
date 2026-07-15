# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: salud financiera → *"Definir qué métricas
concretas componen 'salud financiera básica' (liquidez, endeudamiento,
rentabilidad)."*

Antes de trabajar en ella, se revisó si esta decisión ya estaba tomada en
algún lugar del proyecto (`ARCHITECTURE.md`, `GOALS.md`,
`investmentops/data_layer/financial_statements.py`) y se confirmó que no
existía ningún documento ni implementación que definiera estos ratios
todavía: la tarea requería trabajo nuevo.

## Qué se implementó

**`investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`** (nuevo)
— documento de diseño que define, a partir de los campos que expone hoy
`FinancialStatement` (`revenue`, `net_income`, `debt`, `source`,
`period_end`), qué métricas concretas calculará de forma determinística
el futuro agente de salud financiera:

- **Rentabilidad:** `net_margin = net_income / revenue`.
- **Endeudamiento:** `debt_to_revenue = debt / revenue` (se eligió esta
  razón, y no deuda/patrimonio, porque `FinancialStatement` no tiene un
  campo de patrimonio/equity).
- **Liquidez:** documentada explícitamente como **no calculable** con el
  modelo de dominio actual, ya que `FinancialStatement` no tiene
  `current_assets` ni `current_liabilities`. Se decidió no inventar una
  aproximación (ej. usar `debt` como proxy de pasivos corrientes), sino
  dejarlo como una limitación explícita que el propio `AnalysisResult`
  del agente deberá declarar (`limitations`), conforme al principio de
  `ARCHITECTURE.md` de no inventar datos que no se tienen.

El documento también deja fuera de alcance (para tareas futuras y
separadas): el cálculo determinístico en sí (próxima tarea pendiente), el
manejo de división por cero (`revenue == 0`), una eventual extensión del
modelo de dominio para soportar liquidez, y el prompt/invocación del
agente.

## Decisiones tomadas

- **Solo dos de las tres categorías previstas (rentabilidad y
  endeudamiento) se calculan en el MVP de Fase 1; la liquidez queda
  como limitación explícita.** Se prefirió declarar honestamente el gap
  de datos (no hay campos de activos/pasivos corrientes en el modelo de
  dominio) en vez de forzar un ratio aproximado con los campos
  existentes, que sería impreciso y podría inducir a una lectura
  equivocada de la salud financiera de la empresa — inconsistente con
  `ARCHITECTURE.md`, "Manejo de errores y limitaciones".
- **`debt_to_revenue` en vez de `debt_to_equity` para endeudamiento.**
  El ratio de endeudamiento más común (deuda/patrimonio) no es calculable
  hoy porque el modelo de dominio no tiene un campo de patrimonio; se
  eligió una razón que sí es calculable con los campos existentes
  (`debt`, `revenue`), dejando explícito por qué no se usó la razón más
  estándar.
- **No se extiende el modelo de dominio `FinancialStatement` en esta
  tarea.** Agregar `current_assets`/`current_liabilities` para resolver
  el gap de liquidez sería una decisión de diseño separada y explícita
  (requeriría, además, que el proveedor de datos y la capa de
  normalización lo soporten), no algo a anticipar dentro de una tarea que
  solo debía *definir* las métricas.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, y todo el
código Python existente en `investmentops/` (esta tarea es puramente de
diseño/documentación, no toca ninguna implementación).

## Problemas encontrados

Ninguno. Se detectó un gap de datos (falta de `current_assets`/
`current_liabilities` en `FinancialStatement` para calcular liquidez),
pero se documentó como una limitación explícita en vez de bloquear la
tarea o inventar una solución fuera de su alcance.

## Próxima tarea recomendada

La siguiente tarea sin empezar en la misma sección de `TASKS.md`
("Agente de análisis: salud financiera") es:

1. *"Implementar el cálculo determinístico de ratios de liquidez,
   endeudamiento y rentabilidad a partir del modelo normalizado (entrada
   del agente, no su resultado final)."*

Nota para la próxima conversación:
- Según lo definido en `investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md`,
  esta tarea implementará el cálculo determinístico de `net_margin` y
  `debt_to_revenue` a partir de un `FinancialStatement`, en Python puro
  (nunca vía el modelo de lenguaje, conforme a `ARCHITECTURE.md`).
- La tarea deberá decidir explícitamente qué hacer si `revenue == 0`
  (división por cero) para ambos ratios: probablemente señalar la
  imposibilidad de calcular esa métrica en vez de lanzar una excepción
  no controlada o devolver un valor inventado (ej. `None`/`inf` con una
  advertencia asociada), siguiendo el mismo criterio de honestidad ante
  datos faltantes o degenerados ya aplicado en el resto del proyecto.
- La liquidez debe quedar fuera de este cálculo (no implementarla ni
  aproximarla): la función/resultado de esta tarea debe reflejar
  únicamente `net_margin` y `debt_to_revenue`, dejando la ausencia de un
  ratio de liquidez para que la capa de resultado del agente (tarea
  posterior, "Implementar el parseo de la respuesta del modelo al
  resultado estructurado del agente") la declare como limitación.
- No confundir esta tarea con la invocación al proveedor de IA (tarea
  posterior en la misma sección): aquí solo se calculan números en
  código, sin tocar `investmentops.ai_providers` todavía.
