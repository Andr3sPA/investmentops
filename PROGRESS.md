# InvestmentOps — Progreso

**Última actualización:** 2026-07-14

## Última tarea completada

Fase 1 → Agente de análisis: salud financiera → *"Escribir el archivo de
prompt del agente de salud financiera (fuera del código Python),
indicando cómo debe interpretar esas métricas."*

Antes de implementarla, se revisó si ya existía algún archivo de prompt
en `prompts/` (`prompts/README.md` documenta la convención pero
confirmaba explícitamente que "todavía no hay archivos de prompt") y si
algún módulo de código ya cargaba/hacía referencia a un prompt de salud
financiera (`investmentops/analysis_engines/financial_health.py` solo
implementa el cálculo determinístico, sin invocar IA ni cargar ningún
archivo de prompt). Se confirmó que la tarea requería trabajo nuevo.

## Qué se implementó

**`prompts/financial_health.md`** (nuevo) — instrucciones en lenguaje
natural (Markdown), fuera del código Python, para el modelo de lenguaje
que interpretará las métricas ya calculadas por
`calculate_financial_health_metrics` (`net_margin`, `debt_to_revenue`).
El prompt:

- Describe qué datos y métricas recibirá el modelo (el
  `FinancialStatement` normalizado y las métricas precalculadas, sin que
  el modelo deba recalcularlas).
- Indica cómo interpretar `net_margin` (rentabilidad, incluyendo el caso
  de margen negativo) y `debt_to_revenue` (endeudamiento relativo a
  ingresos), y cómo relacionarlas quirúrgicamente sin forzar
  conclusiones no respaldadas por los datos.
- Prohíbe explícitamente inventar o aproximar datos de liquidez (el
  modelo de dominio no los tiene) y exige declarar esa ausencia cuando
  sea relevante, en vez de omitirla en silencio.
- Prohíbe explícitamente inventar valores cuando una métrica venga como
  `null`/ausente (ej. por `revenue == 0`); exige usar la advertencia ya
  calculada en `FinancialHealthMetrics.warnings`.
- Prohíbe explícitamente cualquier recomendación de compra/venta o
  veredicto de inversión, conforme al principio rector de `GOALS.md` y a
  la restricción arquitectónica de `ARCHITECTURE.md` ("El sistema
  informa, no decide").
- Define el formato de salida esperado: texto breve en español, dirigido
  a un inversionista individual sin formación financiera avanzada.

No se modificó ningún módulo de código Python: esta tarea es
exclusivamente de contenido/documentación, tal como exige
`ARCHITECTURE.md` ("Prompts como artefactos, no como código").

## Decisiones tomadas

- **El prompt no calcula ni corrige métricas.** Se instruye explícitamente
  al modelo a usar `net_margin` y `debt_to_revenue` tal como se le
  entregan, sin recalcularlos ni ajustarlos, preservando la separación
  ya establecida en `ARCHITECTURE.md` entre cálculo determinístico
  (código) e interpretación (IA).
- **La ausencia de datos de liquidez se declara de forma explícita en el
  prompt**, no solo en la documentación de diseño
  (`FINANCIAL_HEALTH_METRICS.md`): de lo contrario, el modelo de lenguaje
  podría inferir o insinuar una lectura de liquidez a partir de `debt` u
  otros campos disponibles, lo cual sería impreciso.
- **El prompt maneja explícitamente el caso `null`/ausente** de cada
  métrica (resultado de `revenue == 0` en el cálculo determinístico),
  indicando que se declare la limitación en vez de inventar un valor.
- **No se implementa todavía la invocación al proveedor de IA ni el
  parseo de su respuesta.** Esas son las dos tareas siguientes en la
  misma sección de `TASKS.md`, explícitamente fuera de alcance de esta
  tarea.

## Archivos creados o modificados

Creados:
- `prompts/financial_health.md`

Modificados:
- `TASKS.md` (tarea marcada como completada, con referencia inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `prompts/README.md` (su
contenido ya anticipaba correctamente esta convención, no requiere
cambios), `investmentops/analysis_engines/financial_health.py`, y el
resto del código existente.

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

La siguiente tarea sin empezar en la misma sección de `TASKS.md`
("Agente de análisis: salud financiera") es:

1. *"Implementar la invocación al proveedor de IA configurado con esas
   métricas + el prompt."*

Nota para la próxima conversación:
- Esta tarea debe combinar: (a) `resolve_agent_provider` (ver
  `investmentops/ai_providers/selection.py`) para resolver qué
  proveedor/modelo le corresponde al agente `"financial_health"`, (b) la
  construcción de la instancia concreta de `AIProvider` correspondiente
  (hoy solo existe `AnthropicAIProvider`, ver
  `investmentops/ai_providers/anthropic_provider.py`), (c) la carga del
  contenido de `prompts/financial_health.md` desde disco, y (d) la
  invocación de `AIProvider.complete(prompt, data=...)` con las métricas
  de `FinancialHealthMetrics` como `data`.
- No confundir esta tarea con el parseo de la respuesta del modelo al
  `AnalysisResult` final del agente (tarea siguiente, separada): aquí
  solo se implementa la invocación y se obtiene el `AIProviderResponse`
  crudo.
- Revisar si conviene un mecanismo simple de carga de prompts desde
  `prompts/<agent_id>.md` reutilizable por futuros agentes (ej.
  valoración, Fase 6), en vez de hardcodear la ruta solo para
  `financial_health`, siempre que no adelante trabajo de tareas futuras
  no relacionadas.
