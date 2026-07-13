# InvestmentOps — Arquitectura

Este documento describe la arquitectura técnica de InvestmentOps para el MVP, en línea con lo definido en `GOALS.md`. No contiene código; describe componentes, responsabilidades, límites entre módulos y flujos de datos.

## Principios de diseño

- **CLI-first.** Todo el sistema se opera desde una interfaz de línea de comandos. No hay servidor, no hay proceso persistente escuchando peticiones.
- **Un solo usuario, sin autenticación.** No existe concepto de sesión, cuenta, ni permisos. La configuración (API keys, preferencias) vive en archivos locales.
- **Monolito modular, no microservicios.** Un único proyecto desplegable, pero internamente dividido en módulos con responsabilidades claras y bajo acoplamiento, comunicados mediante interfaces internas (no HTTP).
- **Extensibilidad sin reescritura.** Agregar una nueva fuente de datos (por ejemplo, otro proveedor financiero) o un nuevo tipo de análisis (por ejemplo, una nueva estrategia de inversión) debe implicar *añadir* un módulo que cumple un contrato conocido, no modificar el núcleo del sistema.
- **La IA es un mecanismo central, no un accesorio.** Los motores de análisis no son simplemente scripts que calculan ratios: son agentes especializados que interpretan datos normalizados con apoyo de un modelo de lenguaje. El cálculo determinístico de métricas (cuando aplica) es una entrada para el agente, no un sustituto de su interpretación.
- **Independencia del proveedor de IA.** El sistema no debe acoplarse a un único proveedor (Gemini, Claude, OpenAI, Ollama). Todo acceso a un modelo de lenguaje pasa por una interfaz común, de modo que cambiar de proveedor no requiera modificar los agentes ni el resto del sistema.
- **Prompts como artefactos, no como código.** El texto de los prompts de cada agente vive en archivos independientes (fuera del código Python), de forma que puedan revisarse, versionarse y ajustarse sin tocar la lógica de orquestación ni de parsing.
- **Reproducibilidad y trazabilidad.** Cada reporte generado debe poder explicar de qué fuentes salió cada dato y cuándo se obtuvo, para poder confiar (o desconfiar) en él.
- **El sistema informa, no decide.** Esto es una restricción arquitectónica, no solo de producto: ningún módulo de análisis debe emitir un veredicto binario tipo "comprar/vender". La capa de análisis produce lecturas e interpretaciones; la capa de presentación las muestra sin resumirlas en una decisión.

## Vista general de capas

El sistema se organiza en seis capas, cada una con una responsabilidad única:

1. **CLI (punto de entrada)** — interpreta comandos y argumentos del usuario, orquesta la ejecución, no contiene lógica de negocio.
2. **Orquestación (core / pipeline)** — coordina qué fuentes de datos consultar, qué análisis correr y qué reportes generar para una solicitud dada.
3. **Fuentes de datos (data providers)** — módulos independientes que obtienen datos crudos de proveedores externos (financieros, noticias, mercado) o de caché local.
4. **Normalización y almacenamiento (data layer)** — transforma los datos crudos de cada proveedor a un modelo interno común y los persiste localmente (caché/histórico).
5. **Análisis (agentes de IA / analysis engines)** — módulos que consumen el modelo interno normalizado y producen interpretaciones: salud financiera, valoración, riesgos, comparables, lecturas por estrategia. Cada uno se implementa como un agente especializado que usa un modelo de lenguaje (vía la interfaz de proveedores de IA) para producir su interpretación, apoyado en prompts externos y, cuando aplica, en métricas calculadas de forma determinística como entrada.
6. **Reportes (report generators)** — toman los resultados del análisis y los renderizan en Markdown, HTML y JSON. La redacción narrativa final puede delegarse a un agente de reporte (también basado en IA) que compone el texto a partir de los resultados estructurados, sin agregar análisis nuevo ni veredictos.

Como soporte transversal a las capas 5 y 6 existe una **interfaz de proveedores de IA**, descrita en la sección de componentes, que abstrae la llamada a cualquier modelo de lenguaje (Gemini, Claude, OpenAI, Ollama) detrás de un contrato común.

La regla de dependencia es de arriba hacia abajo: la CLI depende del core, el core depende de las interfaces de fuentes de datos y de análisis, pero las fuentes de datos y los motores de análisis no conocen a la CLI ni entre sí directamente. Esto es lo que permite añadir nuevas fuentes, nuevos análisis o nuevos proveedores de IA sin tocar las demás capas.

## Componentes

### 1. CLI

Responsable de:
- Parsear comandos (por ejemplo: investigar una empresa, listar análisis disponibles, regenerar un reporte, comparar dos empresas).
- Validar argumentos básicos (ticker, formato de salida, rango de fechas).
- Invocar al orquestador y mostrar progreso/errores al usuario.
- No contiene lógica financiera ni de formateo de reportes; delega todo.

### 2. Orquestador (Core)

Es el corazón del sistema. Responsable de:
- Recibir una solicitud de investigación (ej. "investiga la empresa X").
- Determinar qué fuentes de datos deben consultarse según el análisis solicitado.
- Ejecutar las fuentes de datos (con manejo de fallos: si una fuente falla, el sistema debe poder continuar con las demás y dejarlo explícito en el reporte).
- Pasar los datos normalizados a los motores de análisis correspondientes.
- Ensamblar los resultados de todos los análisis en un modelo de "resultado de investigación" único.
- Entregar ese resultado a la capa de reportes.

El orquestador conoce **interfaces**, no implementaciones concretas. Esto es lo que hace posible el registro dinámico de nuevas fuentes y análisis (ver sección "Extensibilidad").

### 3. Fuentes de datos (Data Providers)

Cada proveedor es un módulo independiente responsable de obtener un tipo de dato desde una fuente externa. Ejemplos de categorías (no de proveedores específicos, que se definirán más adelante):
- Datos financieros fundamentales (estados financieros, ratios).
- Datos de mercado (precio, volumen, capitalización).
- Noticias y eventos recientes.
- Datos de comparables/sector.

Todos los proveedores implementan el mismo contrato: reciben un identificador de empresa (ticker) y devuelven datos crudos junto con metadatos de procedencia (fuente, fecha de consulta, confiabilidad). El orquestador no sabe *cómo* cada proveedor obtiene el dato, solo que cumple el contrato.

Esto permite, por ejemplo, agregar un proveedor nuevo para el mercado colombiano (relevante para Tyba/Trii) sin alterar los proveedores existentes ni el core.

### 4. Normalización y almacenamiento (Data Layer)

Responsable de:
- Convertir los datos crudos y heterogéneos de cada proveedor a un **modelo de dominio interno común** (por ejemplo, una representación estándar de "estado de resultados" sin importar de qué proveedor vino).
- Cachear localmente los datos obtenidos, para evitar llamadas repetidas a APIs externas y para permitir trabajar offline con datos previamente descargados.
- Mantener un histórico simple de consultas (qué se consultó, cuándo, con qué resultado) para trazabilidad.
- El almacenamiento es local (archivos o una base de datos embebida), coherente con el requisito de "un solo usuario, todo local".

Esta capa es la que aísla al resto del sistema de los formatos particulares de cada API externa: si una fuente cambia su formato de respuesta, el impacto se limita a su adaptador de normalización.

### 5. Motores de análisis (Agentes de IA / Analysis Engines)

Cada motor de análisis es un **agente especializado** que responde a **una** de las preguntas de investigación definidas en `GOALS.md`. Ejemplos de agentes:
- Salud financiera (liquidez, endeudamiento, rentabilidad).
- Valoración (múltiplos, comparación histórica de valoración).
- Evolución de ingresos y beneficios (series de tiempo, tendencias).
- Riesgos (señales cualitativas y cuantitativas de riesgo).
- Noticias relevantes (filtrado y resumen de eventos recientes).
- Comparables (posicionamiento frente a pares del sector).
- Lecturas por estrategia de inversión (value, growth, calidad, etc.) — cada estrategia puede implementarse como un agente propio que interpreta los mismos datos normalizados desde su propio marco de análisis.

Todos los agentes comparten un contrato común: reciben el modelo de dominio normalizado de una empresa (y, cuando aplica, métricas ya calculadas de forma determinística a partir de ese modelo) y devuelven un resultado estructurado (hallazgos, métricas relevantes, contexto), nunca una recomendación de acción. Un agente no depende de otro agente ni de una fuente de datos específica; depende del modelo de dominio interno y de la interfaz de proveedores de IA (componente 5bis).

Internamente, cada agente sigue el mismo patrón:
1. Prepara los datos de entrada (modelo normalizado y, si corresponde, métricas precalculadas).
2. Carga su prompt desde un archivo independiente (no embebido en el código).
3. Invoca al proveedor de IA configurado a través de la interfaz común, enviando datos + prompt.
4. Parsea la respuesta del modelo a la estructura de "Resultado de análisis", registrando además qué proveedor/modelo de IA se usó (como parte de la procedencia).

El cálculo determinístico de métricas (cuando existe) se mantiene separado de la interpretación: garantiza que los números sean reproducibles, mientras que la lectura/interpretación de esos números es responsabilidad del agente de IA. Esto es lo que distingue a los motores de un simple script de cálculo de ratios.

Esto permite agregar una nueva estrategia de inversión o un nuevo tipo de análisis registrando un agente adicional (con su propio prompt), sin modificar los existentes.

### 5bis. Interfaz de proveedores de IA (AI Provider Interface)

Componente transversal, usado por los agentes de análisis (capa 5) y, opcionalmente, por el agente de reporte (capa 6). Responsable de:
- Definir un contrato común para invocar un modelo de lenguaje: entrada (prompt + datos estructurados + parámetros básicos) y salida (texto/estructura de respuesta + metadatos: proveedor, modelo, fecha de la llamada).
- Proveer una implementación concreta por proveedor soportado: Gemini, Claude (Anthropic), OpenAI y Ollama (modelos locales).
- Permitir seleccionar el proveedor (y el modelo) a usar mediante configuración local, sin que el agente que lo invoca conozca los detalles de la API específica de cada proveedor.

Ningún agente de análisis llama directamente al SDK o API de un proveedor de IA; siempre pasa por esta interfaz. Esto es lo que permite cambiar de proveedor, o incluso usar proveedores distintos para agentes distintos, sin modificar los agentes ni el orquestador. Añadir un nuevo proveedor de IA implica implementar el contrato de esta interfaz y registrarlo, igual que ocurre con un nuevo proveedor de datos.

### 6. Generadores de reportes (Report Generators)

Responsables de tomar el resultado ensamblado de la investigación (salida del orquestador, ya con todos los análisis resueltos) y renderizarlo en distintos formatos:
- **Markdown** — formato principal, legible y versionable, pensado para guardarse en el propio repo o notas personales.
- **HTML** — versión navegable, útil para lectura más cómoda o para compartir.
- **JSON** — formato estructurado, pensado para consumo programático futuro (por ejemplo, si más adelante se quiere alimentar otra herramienta, sin necesidad de una API).

Los tres generadores consumen el mismo modelo de resultado. La lógica de análisis no vive en esta capa; sin embargo, la redacción narrativa del reporte puede delegarse a un **agente de reporte** (también apoyado en un prompt externo y en la interfaz de proveedores de IA) cuya única función es componer texto legible a partir de los resultados estructurados ya producidos por los demás agentes — no introduce hallazgos nuevos ni resume los resultados en un veredicto de compra/venta. Agregar un nuevo formato de salida (por ejemplo PDF a futuro) implica añadir un generador nuevo, no tocar los existentes.

## Modelo de datos interno (conceptual)

Para que las capas de análisis y reportes sean independientes de las fuentes, el sistema se apoya en un modelo de dominio común, entre otros:

- **Empresa** — identidad básica (ticker, nombre, sector, mercado).
- **Estados financieros normalizados** — series históricas de ingresos, beneficios, deuda, flujo de caja, etc., con la fuente y fecha de cada dato.
- **Datos de mercado** — precio, capitalización, múltiplos, con fecha de corte.
- **Noticias** — eventos con fecha, fuente y resumen.
- **Comparables** — conjunto de empresas pares y sus métricas equivalentes.
- **Resultado de análisis** — estructura común que produce cada agente: identificador del análisis, hallazgos, métricas de soporte, advertencias/limitaciones, y metadatos de procedencia (incluyendo, cuando aplica, qué proveedor y modelo de IA generó la interpretación).
- **Resultado de investigación** — agregación de todos los resultados de análisis para una empresa en un momento dado; es lo que finalmente consumen los generadores de reportes.

Este modelo es el "contrato" que conecta todas las capas y es, junto con las interfaces de proveedor/motor, el principal mecanismo de extensibilidad del sistema.

## Extensibilidad

Dos ejes de extensión están contemplados desde el diseño:

**Nuevas fuentes de datos:** un nuevo proveedor se agrega implementando el contrato de "data provider" (recibir ticker, devolver datos crudos + metadatos) y registrándose ante el orquestador. No requiere cambios en los motores de análisis ni en los reportes.

**Nuevos tipos de análisis:** un nuevo agente se agrega implementando el contrato de "analysis engine" (recibir modelo de dominio normalizado, devolver resultado estructurado), añadiendo su propio archivo de prompt, y registrándose ante el orquestador. No requiere cambios en las fuentes de datos ni en los reportes, siempre que use datos ya presentes en el modelo de dominio (si necesita un dato nuevo, ese dato se agrega al modelo de dominio y a la fuente correspondiente, sin afectar a los demás agentes).

**Nuevos proveedores de IA:** un nuevo proveedor (por ejemplo, otro modelo de Gemini, OpenAI, Claude u Ollama, o uno adicional a futuro) se agrega implementando el contrato de la interfaz de proveedores de IA y registrándose en la configuración. No requiere cambios en los agentes de análisis ni en el orquestador: los agentes siguen invocando la misma interfaz común, independientemente de qué proveedor esté configurado detrás.

El mecanismo de registro (cómo el orquestador "descubre" proveedores de datos, agentes de análisis y proveedores de IA disponibles) debe resolverse en el diseño detallado, pero el punto arquitectónico clave es que **agregar** un módulo no debe requerir **modificar** el código de los módulos existentes.

## Manejo de configuración y credenciales

- La configuración (API keys de proveedores de datos, API keys/endpoints de proveedores de IA, qué proveedor de IA usa cada agente, preferencias de formato de salida, rutas de caché) se gestiona mediante archivos de configuración locales, no mediante un sistema de gestión de usuarios.
- Los prompts de cada agente se almacenan como archivos independientes (no como cadenas dentro del código Python), en una ubicación configurable o convencional dentro del proyecto, de forma que puedan editarse sin tocar la lógica de los agentes.
- No existe concepto de sesión ni de login: la configuración es global al entorno local del usuario.

## Manejo de errores y limitaciones

- Si una fuente de datos falla o no tiene información, el orquestador debe permitir continuar con las fuentes y análisis restantes, y el reporte final debe reflejar explícitamente qué información no pudo obtenerse, en vez de fallar silenciosamente o inventar datos.
- Cada resultado de análisis debe poder expresar sus propias limitaciones (por ejemplo: "cálculo basado en datos parciales", "sin datos de los últimos dos trimestres").
- Esto es una decisión arquitectónica deliberada: la confiabilidad y transparencia del dato es más importante que la completitud del reporte.

## Fuera de alcance de esta arquitectura (consistente con GOALS.md)

- No se define ninguna capa de autenticación ni gestión de usuarios.
- No se define ninguna capa de API REST ni servidor HTTP.
- No se define ningún frontend web o gráfico.
- No se define infraestructura de despliegue multi-servicio ni orquestación de microservicios.
- No se define ningún módulo de ejecución de órdenes ni integración transaccional con Tyba, Trii u otros brókers.
- No se define ningún módulo de toma de decisión automática; la capa de análisis produce lecturas, no veredictos.
- El uso de IA no introduce un servicio alojado propio: los proveedores de IA se consumen como APIs externas (o un runtime local en el caso de Ollama), de la misma forma en que se consumen los proveedores de datos, sin agregar un servidor ni multi-tenancy al proyecto.

## Resumen del flujo de una investigación

1. El usuario ejecuta un comando en la CLI indicando la empresa a investigar (y opcionalmente qué análisis y formatos quiere).
2. La CLI delega la solicitud al orquestador.
3. El orquestador identifica qué fuentes de datos y qué motores de análisis son necesarios, y los ejecuta.
4. Los proveedores obtienen datos crudos; la capa de normalización los convierte al modelo de dominio interno y los cachea.
5. Los agentes de análisis consumen el modelo de dominio (y métricas precalculadas cuando aplica) y, mediante la interfaz de proveedores de IA, producen resultados de análisis interpretados.
6. El orquestador ensambla todos los resultados en un resultado de investigación único.
7. Los generadores de reportes traducen ese resultado a Markdown, HTML y/o JSON, según lo solicitado, apoyándose opcionalmente en un agente de reporte para la redacción narrativa.
8. La CLI informa al usuario dónde quedaron guardados los reportes generados.
