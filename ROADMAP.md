# InvestmentOps — Roadmap

Este roadmap está organizado por **valor entregado**, no por capas técnicas. Cada fase añade una capacidad de investigación completa y deja el proyecto en un estado usable de principio a fin desde la CLI, conforme a `GOALS.md` y `ARCHITECTURE.md`.

> Nota sobre alcance: `GOALS.md` excluye explícitamente la gestión de portafolio (posiciones, rendimientos, rebalanceo). Por eso, en este roadmap no hay una fase de "portafolio"; en su lugar existe una fase de **registro de investigaciones**, que guarda un historial de qué se investigó y qué se encontró — no de qué se compró ni cuánto se ganó o perdió.

---

## Fase 1 — Analizar una empresa con datos fundamentales básicos

**Estado:** 🚧 En progreso (estructura base del proyecto creada; aún no es usable de punta a punta).

**Valor:** Por primera vez, el usuario puede pedirle a la herramienta que investigue una empresa y recibir una respuesta real a "¿está financieramente sana?" y "¿está cara o barata?", en vez de buscarlo manualmente. Desde esta primera fase, la interpretación no es un cálculo fijo de umbrales en código: es producida por agentes de IA, sobre una interfaz que no ata el proyecto a un único proveedor.

- Un comando de CLI recibe un ticker y devuelve datos fundamentales básicos (ingresos, beneficios, deuda, múltiplos de valoración) desde una única fuente de datos.
- Se introduce la interfaz común de proveedores de IA, con al menos una implementación funcional (por ejemplo, un proveedor) y el diseño ya preparado para sumar Gemini, Claude, OpenAI y Ollama sin cambios en los agentes.
- Dos agentes de análisis mínimos (salud financiera y valoración) calculan sus métricas de forma determinística y delegan la interpretación a un modelo de lenguaje, usando prompts almacenados en archivos independientes.
- La salida es texto simple en consola (aún sin reportes formales).
- Ya es utilizable: responde 2 de las 8 preguntas de `GOALS.md` de punta a punta, con IA como parte central del análisis desde el primer momento, no como una capa añadida después.

## Fase 2 — Generar un reporte profesional

**Valor:** Lo que antes era texto suelto en consola ahora es un documento que el usuario puede guardar, releer y archivar como parte de su proceso de decisión.

- Se activa la capa de generación de reportes: Markdown y HTML (JSON puede sumarse aquí o dejarse para una fase posterior si no aporta valor inmediato al usuario).
- El reporte organiza de forma clara los hallazgos de la Fase 1: salud financiera, valoración, con contexto y fuente de cada dato (incluyendo qué proveedor de IA generó cada interpretación).
- Opcionalmente, la redacción del reporte se apoya en un agente de reporte que compone el texto final a partir de los resultados ya producidos por los agentes de análisis, sin agregar hallazgos nuevos.
- El usuario ya tiene un artefacto persistente y presentable, no solo una consulta efímera.

## Fase 3 — Analizar ingresos y beneficios en el tiempo

**Valor:** El usuario deja de ver una foto estática de la empresa y empieza a ver su evolución, que es clave para juzgar si una empresa mejora, se estanca o se deteriora.

- Se amplía la fuente de datos para traer series históricas (varios años/trimestres) de ingresos y beneficios.
- Nuevo motor de análisis: evolución y tendencia de ingresos/beneficios.
- El reporte incluye esta evolución de forma legible (tablas o series descritas).
- Responde directamente las preguntas 3 y 4 de `GOALS.md`.

## Fase 4 — Analizar noticias recientes

**Valor:** El usuario deja de depender de revisar noticias por su cuenta; la herramienta le trae el contexto reciente que podría afectar su decisión.

- Se añade una nueva fuente de datos (noticias), sin alterar las fuentes existentes, gracias al contrato de proveedores definido en `ARCHITECTURE.md`.
- Nuevo motor de análisis: filtrado y resumen de noticias relevantes para la empresa.
- El reporte incorpora una sección de "noticias recientes relevantes".
- Responde la pregunta 6 de `GOALS.md`.

## Fase 5 — Comparar con empresas similares

**Valor:** El usuario puede contextualizar los números de una empresa frente a su competencia, en vez de juzgarla de forma aislada.

- Se añade una fuente de datos de comparables/sector.
- Nuevo motor de análisis: posicionamiento relativo frente a pares (métricas clave lado a lado).
- Nuevo comando de CLI para comparar dos o más empresas directamente.
- El reporte puede generarse tanto para una empresa individual como para una comparación.
- Responde la pregunta 7 de `GOALS.md`.

## Fase 6 — Lecturas por estrategia de inversión

**Valor:** El usuario obtiene distintas perspectivas sobre la misma empresa (value, growth, calidad, etc.), en vez de una sola lectura genérica, ayudándolo a formar su propio juicio en vez de recibir una única narrativa.

- Se agregan agentes de análisis adicionales, uno por estrategia/escuela de inversión, cada uno con su propio prompt (archivo independiente) que encapsula el marco de esa estrategia, todos consumiendo el mismo modelo de dominio ya existente.
- El reporte presenta estas lecturas de forma explícitamente contrastable (una junto a otra), sin fusionarlas en un veredicto único.
- Responde la pregunta 8 de `GOALS.md` y cierra completamente el conjunto de preguntas original del MVP.

## Fase 7 — Registro personal de investigaciones

**Valor:** El usuario puede llevar un historial de qué empresas ha investigado, cuándo, y qué conclusiones sacó — útil para no repetir trabajo y para revisar su propio criterio en el tiempo. Esto **no** es gestión de portafolio: no registra posiciones, montos ni rendimientos, solo el histórico de investigación y análisis ya construido en la capa de datos.

- Se expone el histórico de consultas (ya guardado internamente desde la Fase 1 por la capa de normalización/caché) como algo consultable por el usuario: qué empresas se investigaron y cuándo.
- Nuevo comando de CLI para listar o revisar investigaciones anteriores sin tener que volver a ejecutarlas.
- El usuario gana continuidad entre sesiones de investigación.

## Fase 8 — Watchlist

**Valor:** El usuario puede marcar empresas de interés para hacerles seguimiento recurrente, sin tener que recordar manualmente cuáles está considerando.

- Nuevo comando de CLI para agregar/quitar/listar empresas en una watchlist local.
- Un nuevo comando permite re-investigar de una sola vez todas las empresas de la watchlist y generar sus reportes.
- El usuario tiene ahora un flujo de investigación recurrente centrado en sus empresas de interés, no solo consultas puntuales.

## Fase 9 — Automatización diaria

**Valor:** El usuario deja de tener que acordarse de correr la herramienta; el sistema le mantiene la información de su watchlist actualizada por sí solo.

- Se agrega la posibilidad de ejecutar la investigación de la watchlist de forma programada (por ejemplo, vía un scheduler del sistema operativo local, sin necesidad de un servidor).
- Los reportes generados automáticamente pueden resaltar qué cambió desde la última ejecución (por ejemplo: nuevas noticias, cambios relevantes en valoración).
- El usuario obtiene un flujo de "investigación continua" de bajo esfuerzo, manteniendo siempre el rol informativo (nunca decide ni ejecuta nada por sí mismo).

---

## Principio transversal a todas las fases

En cada fase, sin excepción, el sistema **informa y contextualiza**, nunca recomienda comprar o vender ni toma decisiones por el usuario. Esto se mantiene constante desde la Fase 1 hasta la Fase 9, tal como establece el principio rector de `GOALS.md`.
