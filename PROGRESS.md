# InvestmentOps — Progreso

**Última actualización:** 2026-07-19

## Última tarea completada (mantenimiento de proceso, no de código)

Regranulación de `TASKS.md`: se revisaron todas las tareas **pendientes**
(`- [ ]`) del roadmap y se dividieron las que resultaban demasiado
grandes para completarse de principio a fin en una única conversación de
Claude Web, sin cambiar el alcance del proyecto ni el contenido de
`ROADMAP.md`/`GOALS.md`. Ninguna tarea ya completada (`- [x]`) se
modificó: su registro histórico se conserva intacto.

Esta tarea **no modificó ningún archivo Python** ni introdujo código
nuevo: es puramente de reorganización de `TASKS.md`.

## Qué se dividió

- **Fase 3, "Orquestador"** (2 tareas → 4 tareas): se separó explícitamente
  la decisión de diseño pendiente ya señalada en una actualización
  anterior de este archivo (cómo integrar `TrendAnalysisResult`, que no
  tiene `AnalysisProvenance`, dentro de `ResearchResult.analysis_results`)
  como su propia tarea previa a cualquier código. Luego se separó la
  obtención/normalización de la serie histórica (pieza reutilizable del
  orquestador) del registro de la invocación del motor, y de su inclusión
  final en el `ResearchResult` con manejo de fallos parciales.
- **Fase 3, "Reportes"** (reordenada, sin cambiar cantidad): se movió la
  tarea de diseño ("decidir el formato de presentación de la serie")
  antes de las tareas de implementación en Markdown y HTML, siguiendo el
  mismo orden ya usado en el resto del documento.
- **Fase 4, "Normalización"** (3 tareas → 4 tareas): "Persistir las
  noticias normalizadas en la caché local" se dividió en guardado y
  lectura por separado, igual que ya está hecho para `financial_statement`/
  `market_data` (Fase 1) y `financial_statement_series` (Fase 3).
- **Fase 5, "Normalización"** (3 tareas → 4 tareas): mismo criterio que
  Fase 4, aplicado a la caché de comparables.
- **Fase 5, "Orquestador y CLI"** (4 tareas → 6 tareas): "Registrar el
  nuevo proveedor y el nuevo motor" se separó en dos tareas (una por
  componente). "Conectar el comando de comparación con el orquestador"
  se separó en la función de orquestación que ejecuta y ensambla la
  comparación, y la conexión de esa función con la CLI.
- **Fase 5, "Reportes"** (3 tareas → 4 tareas): "Adaptar los generadores
  para soportar un reporte de comparación" se dividió por formato
  (Markdown y HTML), ya que cada adaptación toca un módulo distinto.
- **Fase 6, "Motores de análisis por estrategia"** (4 tareas → 9 tareas):
  era la división más significativa. "Implementar el motor de análisis
  para la estrategia X" (value/growth/calidad) combinaba en una sola
  tarea la escritura del prompt, la invocación al proveedor de IA y el
  parseo de la respuesta — exactamente las responsabilidades que en la
  Fase 1 (salud financiera, valoración) sí estaban separadas. Se aplicó
  ese mismo patrón (prompt → invocación → parseo) a cada una de las tres
  estrategias, y se eliminó la tarea separada de "ensamblar el resultado
  de cada motor" al quedar cubierta por el paso de parseo de cada
  estrategia.

## Qué NO se tocó

- Ninguna tarea marcada `- [x]` (todo el trabajo ya completado de las
  Fases 1 a 3 permanece exactamente igual, con sus referencias a
  archivos concretos).
- Tareas pendientes que ya tenían una sola responsabilidad clara y un
  alcance verificable (ej. Fases 7, 8 y 9 casi en su totalidad, y varias
  tareas de las Fases 4-6 que ya estaban bien acotadas).
- `ROADMAP.md`, `GOALS.md` y `ARCHITECTURE.md`: no se modificó ningún
  otro documento del proyecto.
- Ningún archivo `.py`: esta tarea no tocó código.

## Archivos creados o modificados

Modificados:
- `TASKS.md` (regranulación de tareas pendientes; se agregó un anexo al
  final documentando los criterios de división usados)
- `PROGRESS.md` (este archivo)

No modificados: todo el código Python del proyecto, `ROADMAP.md`,
`GOALS.md`, `ARCHITECTURE.md`, `CONFIGURATION.md`, `config.example.toml`,
ni ningún archivo de prompt.

## Próxima tarea recomendada

Con el roadmap ya regranulado, la siguiente tarea pendiente en orden es
la primera subtarea nueva de Fase 3 → "Orquestador":

> "Decidir cómo se integra `TrendAnalysisResult` (sin `AnalysisProvenance`)
> en `ResearchResult.analysis_results`... y documentar la decisión, sin
> modificar código todavía."

Es una tarea de diseño/documentación (no de código), pensada para
desbloquear las tres subtareas de implementación que le siguen en la
misma sección.
