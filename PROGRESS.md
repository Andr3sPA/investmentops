# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Setup del proyecto → *"Crear la carpeta de prompts, separada del código Python, donde vivirá el prompt de cada agente como archivo independiente."*

## Cambios realizados

- Se creó la carpeta `prompts/` en la raíz del proyecto, **fuera** del paquete Python `investmentops/`, conforme al principio de `ARCHITECTURE.md` de que "los prompts son artefactos, no código".
- Se agregó `prompts/README.md` documentando:
  - Por qué la carpeta está separada del código (cita textual del principio de `ARCHITECTURE.md`).
  - La convención de nombres: un archivo Markdown (`.md`) por agente, nombrado con el identificador del agente en `snake_case` (ej. `financial_health.md`, `valuation.md`).
  - Qué debe (y no debe) contener cada archivo de prompt: solo instrucciones de interpretación para el modelo de lenguaje, nunca código Python ni peticiones de veredicto de compra/venta.
  - El estado actual: la carpeta está vacía de prompts reales porque los agentes de análisis todavía no están implementados; cada agente añadirá su propio archivo cuando se implemente (tareas ya previstas en `TASKS.md`).
- No se creó ningún archivo de prompt real todavía (ej. `financial_health.md`), porque escribir el contenido del prompt de cada agente es una tarea explícita y separada dentro de las secciones "Agente de análisis: salud financiera" y "Agente de análisis: valoración" de `TASKS.md`, y la regla de trabajo indica una tarea por conversación.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `prompts/README.md`

Modificados:
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, y ningún archivo dentro de `investmentops/` (esta tarea no toca código Python).

## Decisiones técnicas importantes

- **Ubicación de `prompts/`**: se colocó como carpeta hermana de `investmentops/` en la raíz del proyecto, no dentro del paquete Python, para que quede inequívocamente "fuera del código" (tal como pide `ARCHITECTURE.md`) y sea trivial de encontrar, versionar y editar sin tocar el paquete.
- **Formato Markdown para los prompts**: se eligió `.md` en vez de `.txt` porque los prompts probablemente incluirán estructura (secciones, listas) que se lee mejor en Markdown, y es consistente con el resto de la documentación del proyecto. No hay lógica de renderizado involucrada; sigue siendo texto plano para el agente.
- **Convención de nombres = identificador del agente**: se decidió que el nombre de archivo sea exactamente el identificador que usará el agente en código (ej. `financial_health`), para que la carga del prompt sea una simple resolución de ruta por nombre, sin necesidad de un mapeo adicional. Esta convención queda documentada para cuando se implementen los agentes.
- **No se crearon subcarpetas por fase ni por tipo de agente**: con cero prompts reales todavía, cualquier subdivisión sería especulativa; se prefirió una carpeta plana y agregar estructura solo si el número de prompts lo justifica más adelante (consistente con la decisión ya tomada en la tarea anterior de no crear subestructuras prematuras).
- **No se escribió el contenido de ningún prompt real**: esa es una tarea separada y explícita en `TASKS.md` (dentro de "Agente de análisis: salud financiera" y "Agente de análisis: valoración"), y requiere primero tener definidas las métricas de entrada de cada agente (tareas previas en la sección "Contratos e interfaces" / la propia sección de cada agente), que tampoco están hechas todavía.

## Problemas encontrados

- Ninguno. La tarea era puramente de estructura documental y no interactuó con ninguna decisión ya tomada en `ARCHITECTURE.md` o `TASKS.md`.

## Próxima tarea recomendada

Fase 1 → Setup del proyecto → *"Configurar el gestor de dependencias y el entorno del proyecto."*