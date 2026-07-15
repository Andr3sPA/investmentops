# InvestmentOps — TASKS.md

Desglose de tareas por fase, derivado de `ROADMAP.md`, `ARCHITECTURE.md` y `GOALS.md`.

Reglas de este documento:
- Cada tarea es pequeña: implementable en menos de una hora.
- No se describe código, solo el trabajo a realizar.
- Las tareas respetan las capas definidas en `ARCHITECTURE.md` (CLI, orquestador, fuentes de datos, normalización/almacenamiento, motores de análisis, reportes).
- Ninguna tarea de ninguna fase debe introducir un veredicto de compra/venta, autenticación, servidor HTTP, ni gestión de portafolio (fuera de alcance según `GOALS.md`).

Convención de seguimiento: una tarea marcada con `- [x]` está completada. Las marcadas con `- [ ]` (o sin marcar) siguen pendientes. Se van marcando a medida que se implementan, una por conversación, según el flujo de trabajo acordado.

---

## Fase 1 — Analizar una empresa con datos fundamentales básicos

### Setup del proyecto
- [x] Crear la estructura de carpetas/módulos base: CLI, orquestador, proveedores de datos, capa de datos, agentes de análisis, proveedores de IA, reportes.
- [x] Crear la carpeta de prompts, separada del código Python, donde vivirá el prompt de cada agente como archivo independiente.
- [x] Configurar el gestor de dependencias y el entorno del proyecto.
- [x] Definir el formato y la ubicación del archivo de configuración local (API keys de datos, API keys/endpoints de proveedores de IA, qué proveedor usa cada agente, rutas de caché).
- [x] Implementar la carga de ese archivo de configuración al iniciar el sistema.

### Contratos e interfaces
- [x] Definir el contrato de "data provider" (entrada: ticker; salida: datos crudos + metadatos de procedencia).
- [x] Definir el contrato de "analysis engine" / agente de IA (entrada: modelo de dominio normalizado + métricas precalculadas cuando aplique; salida: resultado estructurado).
- [x] Definir el contrato de "AI provider" (entrada: prompt + datos estructurados; salida: respuesta del modelo + metadatos de proveedor/modelo usado), común para Gemini, Claude, OpenAI y Ollama.
- [x] Definir la estructura del modelo de dominio "Empresa" (ticker, nombre, sector, mercado).
- [x] Definir la estructura del modelo de dominio "Estados financieros normalizados" (ingresos, beneficios, deuda, con fuente y fecha).
- [x] Definir la estructura del modelo de dominio "Datos de mercado" (precio, capitalización, múltiplos, fecha de corte).
- [x] Definir la estructura de "Resultado de análisis" (identificador, hallazgos, métricas de soporte, advertencias/limitaciones, procedencia). — Ya satisfecha por `AnalysisResult`/`AnalysisProvenance` en `investmentops/analysis_engines/contracts.py` (ver PROGRESS.md).
- [x] Definir la estructura de "Resultado de investigación" (agregación de resultados de análisis para una empresa). — `ResearchResult`/`ResearchFailure` en `investmentops/core/research_result.py` (ver PROGRESS.md).

### Fuente de datos fundamentales
- [x] Elegir el proveedor de datos financieros fundamentales a usar para el MVP (decisión, no implementación). — Decisión: **Financial Modeling Prep (FMP)** (ver PROGRESS.md).
- [x] Implementar un cliente mínimo que consulte ese proveedor y obtenga datos crudos de una empresa por ticker. — `FMPFundamentalsProvider` en `investmentops/data_providers/fundamentals.py` (ver PROGRESS.md).
- [x] Adjuntar metadatos de procedencia (nombre de la fuente, fecha/hora de consulta) a cada dato crudo obtenido. — Satisfecha por el mismo `FMPFundamentalsProvider.fetch`, que siempre devuelve `RawProviderData` con `ProviderMetadata` (`source="fmp"`, `queried_at`, `reliability="alta"`).
- [x] Implementar manejo de error básico cuando el proveedor no responde o el ticker no existe. — Satisfecha por el mismo cliente: errores de red, de autenticación, de formato de respuesta y tickers inexistentes se traducen a `DataProviderError` (ver PROGRESS.md).

### Interfaz de proveedores de IA
- [x] Implementar la interfaz común de proveedor de IA (envío de prompt + datos, recepción de respuesta + metadatos). — Ya satisfecha por el contrato `AIProvider`/`AIProviderResponse`/`AIProviderError` definido en `investmentops/ai_providers/contracts.py` durante "Contratos e interfaces": ese `Protocol` ya es la interfaz común exigida por esta tarea (ver PROGRESS.md).
- [x] Implementar al menos una integración concreta (por ejemplo, un proveedor) que cumpla la interfaz. — `AnthropicAIProvider` en `investmentops/ai_providers/anthropic_provider.py` (ver PROGRESS.md).
- [x] Definir el mecanismo de selección de proveedor/modelo por agente vía configuración local. — `resolve_agent_provider`/`AgentProviderSelection`/`AgentProviderSelectionError` en `investmentops/ai_providers/selection.py` (ver PROGRESS.md).
- [x] Dejar documentado (sin implementar aún si no es necesario para el MVP) cómo se sumarían las integraciones restantes (Gemini, Claude, OpenAI, Ollama) sin modificar la interfaz ni los agentes. — `investmentops/ai_providers/EXTENDING.md` (ver PROGRESS.md).
- [x] Implementar manejo de error básico cuando el proveedor de IA no responde o devuelve un formato inesperado. — Implementado en el mismo `AnthropicAIProvider`: errores de red, autenticación (401/403), límite de tasa (429), otros errores HTTP, JSON inválido y respuestas sin contenido interpretable se traducen a `AIProviderError` (ver PROGRESS.md).

### Normalización y almacenamiento
- [x] Implementar la transformación de datos crudos del proveedor al modelo "Estados financieros normalizados". — `financial_statement_from_raw` en `investmentops/data_layer/normalization.py` (ver PROGRESS.md). Toma el corte más reciente del `payload` que entrega `FMPFundamentalsProvider` (`income_statement`, `balance_sheet_statement`) y construye un `FinancialStatement`, señalando `NormalizationError` si faltan campos imprescindibles o la fecha no es interpretable.
- [x] Implementar la transformación de datos crudos al modelo "Datos de mercado". — `market_data_from_raw` en `investmentops/data_layer/normalization.py` (ver PROGRESS.md). Toma el corte más reciente del `payload["quote"]` que entrega `FMPFundamentalsProvider` (`price`, `marketCap`, `timestamp`) y construye un `MarketData` con `multiples` vacío (su cálculo es responsabilidad del agente de valoración), señalando `NormalizationError` si faltan campos imprescindibles o el timestamp no es interpretable.
- [x] Definir el mecanismo de caché local (archivo o base embebida) para persistir datos normalizados. — Decisión: **un archivo JSON por ticker** bajo `[cache].path`, con una clave por modelo de dominio cacheado y un campo `cached_at` (metadato propio de la caché, no del modelo de dominio) para soportar la futura verificación de frescura. Documentado en `investmentops/data_layer/CACHE.md` (ver PROGRESS.md).
- [x] Implementar el guardado de los datos normalizados en la caché tras cada consulta. — `save_financial_statement`/`save_market_data` en `investmentops/data_layer/cache.py` (ver PROGRESS.md). Escriben/fusionan la sección correspondiente en `<cache_path>/<TICKER>.json`, siguiendo la estructura de `CACHE.md` (una clave por modelo, campo `cached_at` en UTC/ISO 8601), sin sobrescribir otras secciones ya cacheadas para el mismo ticker. Señala `CacheError` ante ticker vacío o fallos de E/S.
- [x] Implementar la lectura desde caché para evitar una nueva llamada al proveedor si el dato ya existe y es reciente. — `load_financial_statement`/`load_market_data` en `investmentops/data_layer/cache.py` (ver PROGRESS.md). Leen la sección correspondiente de `<cache_path>/<TICKER>.json`, reconstruyen el modelo de dominio y devuelven `None` si no hay nada cacheado o si `cached_at` superó el umbral de frescura (`DEFAULT_MAX_AGE`, 24 horas, ajustable vía el parámetro `max_age`). Señala `CacheError` ante ticker vacío, fallos de E/S, o una sección cacheada corrupta/incompleta (sin confundir esto con "no cacheado" o "vencido", que son casos válidos representados con `None`).

### Agente de análisis: salud financiera
- [x] Definir qué métricas concretas componen "salud financiera básica" (liquidez, endeudamiento, rentabilidad). — `investmentops/analysis_engines/FINANCIAL_HEALTH_METRICS.md` (ver PROGRESS.md). Decisión: `net_margin` (rentabilidad) y `debt_to_revenue` (endeudamiento) son calculables con los campos actuales de `FinancialStatement`; la liquidez queda documentada como limitación explícita, ya que el modelo de dominio no tiene `current_assets`/`current_liabilities` — no se inventa una aproximación.
- [x] Implementar el cálculo determinístico de ratios de liquidez, endeudamiento y rentabilidad a partir del modelo normalizado (entrada del agente, no su resultado final). — `calculate_financial_health_metrics`/`FinancialHealthMetrics` en `investmentops/analysis_engines/financial_health.py` (ver PROGRESS.md). Calcula `net_margin` y `debt_to_revenue` según lo decidido en `FINANCIAL_HEALTH_METRICS.md`; la liquidez queda fuera (limitación ya documentada, no se aproxima). Si `revenue == 0`, ambos ratios se devuelven como `None` junto con una advertencia explícita en `FinancialHealthMetrics.warnings`, en vez de lanzar `ZeroDivisionError` o inventar un valor.
- [x] Escribir el archivo de prompt del agente de salud financiera (fuera del código Python), indicando cómo debe interpretar esas métricas. — `prompts/financial_health.md` (ver PROGRESS.md). Instruye al modelo a interpretar `net_margin` y `debt_to_revenue`, a declarar explícitamente la ausencia de datos de liquidez y las métricas no calculables (`null` + advertencia), y prohíbe explícitamente cualquier recomendación de compra/venta o veredicto de inversión.
- [x] Implementar la invocación al proveedor de IA configurado con esas métricas + el prompt. — `invoke_financial_health_agent` en `investmentops/analysis_engines/financial_health.py` (ver PROGRESS.md). Combina tres piezas de infraestructura reutilizable: `investmentops.analysis_engines.prompts.load_prompt`, `investmentops.ai_providers.factory.build_ai_provider` y `resolve_agent_provider`. Invoca `AIProvider.complete(prompt, data=...)` enviando el `FinancialStatement` y las `FinancialHealthMetrics` ya calculadas como `data`, sin que la IA calcule ni corrija ninguna métrica. Devuelve el `AIProviderResponse` crudo.
- [x] Implementar el parseo de la respuesta del modelo al resultado estructurado del agente (hallazgos, métricas, advertencias si faltan datos, proveedor/modelo usado). — `parse_financial_health_response` en `investmentops/analysis_engines/financial_health.py` (ver PROGRESS.md). Traduce el `AIProviderResponse` crudo (más las `FinancialHealthMetrics` ya calculadas) a un `AnalysisResult`: `analysis_id="financial_health"`, `findings=[response.content]`, `supporting_metrics` con `net_margin`/`debt_to_revenue`, `limitations` con la limitación de liquidez (siempre presente) más cualquier advertencia de `metrics.warnings`, y `provenance` construida desde los metadatos del proveedor de IA. Se agregó también `analyze_financial_health`, una función de conveniencia que encadena calcular métricas → invocar al proveedor → parsear la respuesta.

### Agente de análisis: valoración
- [x] Definir qué múltiplos concretos componen "valoración básica" (ej. P/E, P/B). — `investmentops/analysis_engines/VALUATION_METRICS.md` (ver PROGRESS.md). Decisión: `price_to_earnings` (`market_cap / net_income`) y `price_to_sales` (`market_cap / revenue`) son calculables con los campos actuales de `MarketData`/`FinancialStatement`, sin necesitar `shares_outstanding` (fórmulas agregadas, no por acción). P/B y EV/EBITDA quedan documentados como limitaciones explícitas: el modelo de dominio no expone patrimonio/`equity` (para P/B) ni EBITDA/`cash` (para EV/EBITDA) — no se inventa una aproximación.
- [x] Implementar el cálculo determinístico de esos múltiplos a partir del modelo normalizado. — `calculate_valuation_metrics`/`ValuationMetrics` en `investmentops/analysis_engines/valuation.py` (ver PROGRESS.md). Calcula `price_to_earnings` (`market_cap / net_income`) y `price_to_sales` (`market_cap / revenue`) según lo decidido en `VALUATION_METRICS.md`. Si `net_income <= 0`, `price_to_earnings` se devuelve como `None` con advertencia explícita; si `revenue == 0`, `price_to_sales` se devuelve como `None` con su propia advertencia. Ambos casos pueden coexistir en `ValuationMetrics.warnings`, sin lanzar `ZeroDivisionError` ni inventar un valor.
- [x] Escribir el archivo de prompt del agente de valoración (fuera del código Python). — `prompts/valuation.md` (ver PROGRESS.md). Instruye al modelo a interpretar `price_to_earnings` y `price_to_sales` ya calculados (nunca recalcularlos), a declarar explícitamente cuando vienen como `null`/ausentes (usando la advertencia entregada junto con los datos), a declarar la ausencia de datos para P/B y EV/EBITDA sin aproximarlos, y prohíbe explícitamente cualquier recomendación de compra/venta o veredicto de inversión.
- [ ] Implementar la invocación al proveedor de IA configurado con esos múltiplos + el prompt.
- [ ] Implementar el parseo de la respuesta del modelo al resultado estructurado del agente de valoración.

### Orquestador mínimo
- Implementar la función que recibe un ticker y dispara la consulta al proveedor de Fase 1.
- Implementar el paso de datos crudos a la capa de normalización.
- Implementar la invocación secuencial de los dos agentes de análisis (salud financiera, valoración) sobre el modelo normalizado.
- Implementar el ensamblado de ambos resultados en un "Resultado de investigación" único.
- Implementar el manejo de fallo del proveedor de datos o del proveedor de IA sin detener el resto del flujo, dejándolo explícito en el resultado.

### CLI
- Definir la sintaxis del comando de investigación (ej. investigar una empresa por ticker).
- Implementar el parseo del argumento ticker.
- Implementar la validación básica del ticker (no vacío, formato esperado).
- Conectar el comando con el orquestador.
- Implementar la impresión en consola del resultado (texto simple, sin formato de reporte todavía).
- Implementar mensajes de error legibles en consola ante fallos del flujo.

### Verificación
- Probar manualmente el flujo completo con un ticker real de punta a punta.
- Probar manualmente el flujo con un ticker inválido o inexistente y confirmar que el error es claro.
- Confirmar que las interpretaciones de los agentes provienen del modelo de lenguaje (y no de reglas fijas en código) revisando la respuesta cruda del proveedor de IA.
- Cambiar la configuración del proveedor de IA usado por un agente (sin modificar su código) y confirmar que el flujo sigue funcionando igual.

---

## Fase 2 — Generar un reporte profesional

### Modelo de reporte
- Definir la estructura común que consumirán los generadores (a partir del "Resultado de investigación").
- Definir qué secciones tendrá el reporte (identidad de la empresa, salud financiera, valoración, fuentes y fecha de cada dato, incluyendo qué proveedor de IA generó cada interpretación).
- (Opcional) Escribir el archivo de prompt del agente de reporte y definir su alcance: solo redacción a partir de los resultados ya existentes, sin nuevos hallazgos ni veredictos.

### Generador Markdown
- Implementar la plantilla base de reporte en Markdown (encabezados, secciones vacías).
- Implementar el volcado de los hallazgos de salud financiera en la sección correspondiente.
- Implementar el volcado de los hallazgos de valoración en la sección correspondiente.
- Implementar la sección de fuentes/procedencia (qué proveedor, qué fecha) al final del reporte.
- Implementar el guardado del archivo Markdown generado en una ruta local configurable.

### Generador HTML
- Definir la plantilla base HTML (estructura mínima, sin diseño elaborado).
- Implementar el volcado de las mismas secciones que en Markdown (salud financiera, valoración, fuentes).
- Implementar el guardado del archivo HTML generado en una ruta local configurable.

### Orquestador y CLI
- Extender el orquestador para invocar los generadores de reporte tras ensamblar el resultado de investigación.
- Añadir al comando CLI la opción de formato de salida (markdown, html, o ambos).
- Implementar el mensaje final en consola indicando dónde quedaron guardados los reportes generados.

### Verificación
- Generar un reporte Markdown de una empresa real y revisar que la información coincide con la Fase 1.
- Generar un reporte HTML de la misma empresa y revisar que abre correctamente en un navegador.

---

## Fase 3 — Analizar ingresos y beneficios en el tiempo

### Fuente de datos histórica
- Investigar si el proveedor actual soporta series históricas (varios años/trimestres) o si se necesita otro endpoint/proveedor.
- Implementar la consulta de series históricas de ingresos y beneficios para un ticker.
- Adjuntar metadatos de procedencia a cada punto de la serie histórica.

### Normalización
- Extender el modelo "Estados financieros normalizados" para incluir series temporales (no solo el dato más reciente).
- Implementar la transformación de la respuesta cruda histórica al modelo de series temporales.
- Extender la caché local para persistir series históricas sin romper los datos ya guardados de Fase 1.

### Motor de análisis: evolución de ingresos y beneficios
- Definir qué se considera "tendencia" (ej. crecimiento interanual, aceleración/desaceleración) a nivel básico.
- Implementar el cálculo de variación periodo a periodo de ingresos.
- Implementar el cálculo de variación periodo a periodo de beneficios.
- Implementar la detección simple de tendencia (creciente, decreciente, estable) para cada serie.
- Ensamblar el resultado estructurado del motor (hallazgos, métricas de soporte, advertencias si hay huecos en la serie).

### Orquestador
- Registrar el nuevo motor de análisis en el flujo del orquestador sin modificar los motores existentes.
- Incluir el nuevo resultado en el "Resultado de investigación" ensamblado.

### Reportes
- Añadir la sección "Evolución de ingresos y beneficios" a la plantilla Markdown.
- Añadir la misma sección a la plantilla HTML.
- Decidir el formato de presentación de la serie (tabla simple vs. descripción textual) para esta fase.

### Verificación
- Probar el flujo completo con una empresa que tenga histórico disponible y revisar que la tendencia calculada es coherente.

---

## Fase 4 — Analizar noticias recientes

### Fuente de datos de noticias
- Elegir el proveedor de noticias a usar para el MVP.
- Implementar el contrato de "data provider" para noticias (ticker/nombre de empresa in, lista de eventos crudos out).
- Adjuntar metadatos de procedencia (fuente, fecha de publicación, fecha de consulta) a cada noticia cruda.
- Implementar manejo de error si el proveedor de noticias falla o no devuelve resultados.

### Normalización
- Definir el modelo de dominio "Noticias" (fecha, fuente, resumen).
- Implementar la transformación de noticias crudas al modelo normalizado.
- Persistir las noticias normalizadas en la caché local.

### Motor de análisis: noticias relevantes
- Definir el criterio básico de relevancia/filtrado de noticias para el MVP (ej. ventana de tiempo reciente).
- Implementar el filtrado de noticias según ese criterio.
- Implementar un resumen breve por noticia relevante (o selección del resumen ya provisto por la fuente).
- Ensamblar el resultado estructurado del motor (hallazgos, lista de noticias relevantes, advertencias si no hay noticias).

### Orquestador
- Registrar el nuevo proveedor de noticias sin modificar los proveedores existentes.
- Registrar el nuevo motor de análisis sin modificar los motores existentes.
- Incluir el nuevo resultado en el "Resultado de investigación".

### Reportes
- Añadir la sección "Noticias recientes relevantes" a la plantilla Markdown.
- Añadir la misma sección a la plantilla HTML.

### Verificación
- Probar el flujo con una empresa que tenga noticias recientes y revisar que aparecen en el reporte con su fuente y fecha.
- Probar el flujo con una empresa sin noticias recientes y revisar que el reporte lo indica explícitamente en vez de omitirlo en silencio.

---

## Fase 5 — Comparar con empresas similares

### Fuente de datos de comparables
- Elegir el proveedor o método para obtener empresas pares/sector de una empresa dada.
- Implementar la consulta de comparables (lista de empresas pares) para un ticker.
- Implementar la consulta de métricas clave (las ya normalizadas en fases previas) para cada empresa par.
- Adjuntar metadatos de procedencia a los datos de comparables.

### Normalización
- Definir el modelo de dominio "Comparables" (conjunto de empresas pares y sus métricas equivalentes).
- Implementar la transformación de los datos crudos de comparables al modelo normalizado.
- Persistir los comparables normalizados en la caché local.

### Motor de análisis: posicionamiento relativo
- Definir qué métricas clave se comparan lado a lado (ej. valoración, márgenes, crecimiento).
- Implementar el cálculo de la posición relativa de la empresa frente a sus pares en cada métrica.
- Ensamblar el resultado estructurado del motor (hallazgos, tabla comparativa, advertencias si faltan datos de algún par).

### Orquestador y CLI
- Registrar el nuevo proveedor y el nuevo motor sin modificar los existentes.
- Diseñar la sintaxis del nuevo comando CLI para comparar dos o más empresas directamente.
- Implementar el parseo de argumentos del comando de comparación (lista de tickers).
- Conectar el comando de comparación con el orquestador, reutilizando el flujo existente para cada empresa involucrada.

### Reportes
- Añadir la sección "Comparables del sector" a la plantilla Markdown.
- Añadir la misma sección a la plantilla HTML.
- Adaptar los generadores para soportar un reporte de comparación (varias empresas) además del reporte individual.

### Verificación
- Probar el comando de investigación individual y confirmar que ahora incluye la sección de comparables.
- Probar el nuevo comando de comparación con dos empresas reales del mismo sector.

---

## Fase 6 — Lecturas por estrategia de inversión

### Diseño de estrategias
- Listar las estrategias/escuelas de inversión a cubrir en el MVP (ej. value, growth, calidad).
- Para cada estrategia, definir de forma breve qué datos del modelo de dominio utiliza y qué pregunta responde.

### Motores de análisis por estrategia
- Implementar el motor de análisis para la estrategia "value" (interpreta datos ya existentes, sin nuevas fuentes).
- Implementar el motor de análisis para la estrategia "growth".
- Implementar el motor de análisis para la estrategia "calidad".
- Ensamblar el resultado estructurado de cada motor, dejando explícito que es una lectura desde un marco particular, no un veredicto.

### Orquestador
- Registrar los nuevos motores de estrategia sin modificar los motores existentes.
- Incluir los resultados de cada estrategia en el "Resultado de investigación" como entradas independientes y contrastables.

### Reportes
- Añadir la sección "Lecturas por estrategia de inversión" a la plantilla Markdown, presentando cada estrategia por separado.
- Añadir la misma sección a la plantilla HTML.
- Revisar que ninguna sección fusiona las lecturas en una única recomendación o veredicto.

### Verificación
- Probar el flujo completo con una empresa real y revisar que las distintas lecturas de estrategia aparecen una junto a otra, sin mezclarse.
- Revisar manualmente que el lenguaje usado en las lecturas es descriptivo/interpretativo y no prescriptivo ("compra"/"vende").

---

## Fase 7 — Registro personal de investigaciones

### Modelo de histórico
- Definir qué campos del histórico ya guardado (desde la capa de normalización/caché) se expondrán al usuario (empresa, fecha, análisis ejecutados).
- Confirmar que el histórico no incluye datos de portafolio (posiciones, montos, rendimientos), conforme a `GOALS.md`.

### Capa de datos
- Implementar una función de consulta que liste las investigaciones previas guardadas en caché/histórico.
- Implementar una función que recupere el detalle de una investigación previa específica sin volver a ejecutarlas.

### CLI
- Definir la sintaxis del nuevo comando para listar investigaciones anteriores.
- Implementar el comando de listado (empresa, fecha de la última investigación).
- Definir la sintaxis del nuevo comando para ver el detalle de una investigación anterior específica.
- Implementar el comando de detalle, reutilizando los generadores de reporte existentes si aplica.

### Verificación
- Investigar dos empresas distintas, luego listar el histórico y confirmar que ambas aparecen con su fecha correcta.
- Consultar el detalle de una investigación anterior y confirmar que no se realizan nuevas llamadas a proveedores externos.

---

## Fase 8 — Watchlist

### Modelo de watchlist
- Definir la estructura de almacenamiento local de la watchlist (lista de tickers, sin datos de portafolio).

### Capa de datos
- Implementar la función para agregar un ticker a la watchlist local.
- Implementar la función para quitar un ticker de la watchlist local.
- Implementar la función para listar los tickers actuales en la watchlist.

### CLI
- Definir la sintaxis de los comandos de watchlist (agregar, quitar, listar).
- Implementar el comando para agregar una empresa a la watchlist.
- Implementar el comando para quitar una empresa de la watchlist.
- Implementar el comando para listar la watchlist actual.
- Definir la sintaxis del comando para re-investigar todas las empresas de la watchlist de una sola vez.
- Implementar ese comando, reutilizando el orquestador existente para cada ticker de la lista.

### Verificación
- Agregar, listar y quitar empresas de la watchlist y confirmar que los cambios persisten entre ejecuciones.
- Ejecutar la re-investigación completa de la watchlist con al menos dos empresas y confirmar que se generan los reportes de cada una.

---

## Fase 9 — Automatización diaria

### Diseño de la ejecución programada
- Definir el mecanismo local a usar para programar la ejecución (scheduler del sistema operativo), sin introducir un servidor.
- Documentar los pasos para que el usuario configure la ejecución periódica en su propio entorno.

### Detección de cambios
- Definir qué se considera "cambio relevante" desde la última ejecución (ej. nuevas noticias, variación de valoración por encima de un umbral).
- Implementar la comparación entre el resultado de investigación actual y el guardado en el histórico de la ejecución anterior para el mismo ticker.
- Implementar el marcado de qué elementos cambiaron respecto a la ejecución previa.

### Orquestador y CLI
- Definir la sintaxis del comando que ejecuta la investigación completa de la watchlist en modo "automatizado" (sin intervención manual).
- Implementar ese comando reutilizando el flujo de la Fase 8, incorporando la detección de cambios.

### Reportes
- Añadir a la plantilla de reporte (Markdown y HTML) una sección opcional de "cambios desde la última ejecución".
- Confirmar que esta sección solo contextualiza cambios, sin emitir ninguna sugerencia de acción.

### Verificación
- Ejecutar el comando automatizado dos veces seguidas (simulando dos días distintos) y confirmar que la segunda ejecución muestra correctamente qué cambió.
- Confirmar que, tras configurar el scheduler del sistema operativo, la ejecución ocurre sin intervención manual.

---

## Principio transversal (todas las fases)

- En cada fase, al revisar las tareas completadas, verificar que ningún texto generado por el sistema (consola, Markdown, HTML) emite una recomendación de compra/venta o un veredicto final, conforme al principio rector de `GOALS.md` y a la restricción arquitectónica de `ARCHITECTURE.md`.
- En cada fase que agregue o modifique un agente de análisis, verificar que su prompt vive en un archivo independiente (no embebido en el código) y que el agente invoca al proveedor de IA únicamente a través de la interfaz común, sin acoplarse a un SDK específico.
