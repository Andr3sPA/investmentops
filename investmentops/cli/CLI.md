# Sintaxis de la CLI (Fase 1)

Cubre la tarea "Definir la sintaxis del comando de investigación (ej.
investigar una empresa por ticker)" (TASKS.md, Fase 1, "CLI").

Esta tarea es de **diseño/documentación**, no de código: decide la
sintaxis del comando antes de implementar su parseo real (próxima tarea,
"Implementar el parseo del argumento ticker"). No se toca
`investmentops/cli/__init__.py` ni `investmentops/__main__.py` en esta
tarea.

## Punto de entrada

El proyecto ya se ejecuta como módulo (`python -m investmentops`, ver
`investmentops/__main__.py`, que hoy solo carga la configuración local
como prueba de humo). La CLI real se invoca de la misma forma:

```bash
python -m investmentops <subcomando> [argumentos]
```

## Decisión: subcomandos (`argparse` con subparsers), no un único comando plano

Se elige una estructura de **subcomandos** (`investmentops <subcomando>
...`) en vez de un único comando con flags, aunque en la Fase 1 solo
existe un subcomando (`investigate`). Motivos:

- `ARCHITECTURE.md`, componente 1 ("CLI"), ya anticipa varios comandos a
  futuro: *"Parsear comandos (por ejemplo: investigar una empresa,
  listar análisis disponibles, regenerar un reporte, comparar dos
  empresas)."*
- `ROADMAP.md` confirma que se sumarán comandos nuevos y explícitamente
  distintos en fases posteriores: comparar empresas (Fase 5, "Nuevo
  comando de CLI para comparar dos o más empresas directamente"),
  listar/ver investigaciones anteriores (Fase 7), watchlist
  (agregar/quitar/listar/re-investigar, Fase 8).
- Definir la sintaxis como subcomandos desde la Fase 1 evita tener que
  rediseñar el parseo de argumentos cuando se agreguen esos comandos
  (cada uno se añade como un subparser nuevo, sin tocar los existentes,
  mismo criterio de extensibilidad ya aplicado en el resto del proyecto
  — ver ARCHITECTURE.md, "Extensibilidad sin reescritura").
- Es el patrón estándar de `argparse` (`add_subparsers`) para herramientas
  CLI con múltiples acciones, sin sumar una dependencia nueva.

Introducir ya los subparsers de comandos futuros (comparar, watchlist,
etc.) sería sobre-diseño antes de que existan esas tareas: esta decisión
solo fija la **forma general** (subcomandos) y define en detalle el único
subcomando que corresponde a la Fase 1.

## El subcomando de la Fase 1: `investigate`

```bash
python -m investmentops investigate TICKER
```

- **Nombre del subcomando:** `investigate` (en inglés, consistente con
  el resto del código del proyecto — módulos, funciones y excepciones ya
  están en inglés, ej. `investigate()` en
  `investmentops.core.orchestrator`, mientras que los mensajes al
  usuario y los prompts sí están en español).
- **Argumento posicional obligatorio:** `TICKER` (ej. `AAPL`,
  `ECOPETROL.CL`). Un único ticker por invocación en esta fase — invocar
  el comando para varios tickers a la vez (comparación) es
  explícitamente una capacidad de la Fase 5 (`ROADMAP.md`), no de esta.
- **Sin flags adicionales en la Fase 1.** En particular:
  - **Sin flag de formato de salida.** `ROADMAP.md`, Fase 1: *"La salida
    es texto simple en consola (aún sin reportes formales)."* La opción
    de formato (`--format markdown|html`) es explícitamente una
    capacidad de la Fase 2 (`TASKS.md`, Fase 2, "Añadir al comando CLI
    la opción de formato de salida"), no de esta.
  - **Sin flag de ruta de configuración** (ej. `--config`). El sistema
    ya resuelve `config.local.toml` en la raíz del proyecto por
    convención (ver `investmentops.config._default_config_path` y
    CONFIGURATION.md); `investigate(ticker, config=None, provider=None)`
    ya acepta `config=None` para que se cargue automáticamente. No hay
    hoy un caso de uso real que requiera apuntar a una ubicación
    distinta desde la línea de comandos, y agregarlo antes de
    necesitarlo iría contra el criterio de no sobre-diseñar ya aplicado
    en otros módulos del proyecto (ver por ejemplo
    `investmentops/data_layer/market_data.py`,
    `investmentops/data_layer/CACHE.md`).

### Ejemplos de invocación

```bash
python -m investmentops investigate AAPL
python -m investmentops investigate ECOPETROL.CL
```

## Validación del ticker (alcance de la próxima tarea)

Esta tarea solo fija la sintaxis (`investigate TICKER`); la validación
concreta (ticker no vacío, formato esperado) es la tarea siguiente en
`TASKS.md` ("Implementar la validación básica del ticker"). Queda
anotado aquí únicamente que el argumento es **posicional y obligatorio**
(`argparse` ya rechaza su ausencia con un error estándar), sin normalizar
ni validar su contenido en el parseo de argumentos: la normalización a
mayúsculas ya ocurre más abajo en el pipeline (ver
`FMPFundamentalsProvider.fetch` y
`investmentops.core.orchestrator.assemble_research_result`), no es
responsabilidad de la capa CLI (ver ARCHITECTURE.md, componente 1: "No
contiene lógica financiera ni de formateo de reportes; delega todo").

## Salida y manejo de errores (alcance de tareas posteriores)

Fuera de alcance de esta tarea, ya identificadas como tareas separadas en
`TASKS.md`, sección "CLI":

- Qué y cómo se imprime en consola el `ResearchResult` devuelto por
  `investigate(...)` ("Implementar la impresión en consola del
  resultado").
- Qué mensajes se muestran ante fallos del flujo ("Implementar mensajes
  de error legibles en consola ante fallos del flujo") — nótese que
  `investigate(...)` ya no deja escapar `DataProviderError`,
  `NormalizationError`, `PromptError`, `AgentProviderSelectionError` ni
  `AIProviderError` (los traduce a `ResearchFailure` dentro del propio
  `ResearchResult`, ver `investmentops/core/orchestrator.py`); lo que
  falta es decidir cómo se le presentan al usuario esos
  `ResearchFailure` en la salida de consola, y cómo se manejan errores
  que sí pueden escapar (ej. `ConfigError` si falta
  `config.local.toml`).

## Fuera de alcance de esta tarea

- Implementar el parseo real con `argparse` (próxima tarea).
- La validación del ticker (tarea separada, ver arriba).
- Conectar el comando con `investigate(...)` (tarea separada,
  "Conectar el comando con el orquestador").
- La impresión del resultado y el manejo de errores en consola (tareas
  separadas, ver arriba).
- La sintaxis de comandos de fases posteriores (comparar, listar
  investigaciones, watchlist): se definirán como tareas explícitas en
  sus propias fases (`ROADMAP.md`, Fases 5, 7 y 8), reutilizando la
  misma estructura de subcomandos ya fijada aquí.
