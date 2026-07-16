# InvestmentOps — Progreso

**Última actualización:** 2026-07-15

## Última tarea completada

Fase 1 → CLI → *"Definir la sintaxis del comando de investigación (ej.
investigar una empresa por ticker)."*

Se verificó antes de implementar que no estuviera ya satisfecha: no
existía ningún documento de diseño de CLI, `investmentops/cli/__init__.py`
seguía siendo solo el docstring de responsabilidad de la capa (sin
ninguna decisión de sintaxis tomada), y `investmentops/__main__.py` solo
prueba la carga de configuración, sin invocar ningún comando real. Con
"Orquestador mínimo" recién completado en la conversación anterior,
"CLI" es la primera sección de `TASKS.md` sin ninguna tarea marcada.

## Qué se implementó

Es una tarea de **diseño/documentación** (mismo patrón que `CACHE.md`,
`FINANCIAL_HEALTH_METRICS.md`, `VALUATION_METRICS.md`): no se esperaba
código todavía, solo fijar la sintaxis del comando antes de implementar
su parseo real (próxima tarea).

**`investmentops/cli/CLI.md`** (nuevo) — documenta:

- **Punto de entrada:** `python -m investmentops <subcomando> [argumentos]`,
  reutilizando el mecanismo ya existente (`investmentops/__main__.py`).
- **Decisión: estructura de subcomandos** (`argparse` con
  `add_subparsers`), no un único comando plano con flags. Justificada
  por `ARCHITECTURE.md` (el componente CLI ya anticipa varios comandos:
  investigar, listar análisis, regenerar reporte, comparar empresas) y
  por `ROADMAP.md` (comandos futuros ya previstos: comparar en Fase 5,
  listar/ver investigaciones en Fase 7, watchlist en Fase 8). Fijar esto
  ahora evita rediseñar el parseo de argumentos cuando se agreguen esos
  comandos; no se implementan esos subcomandos futuros todavía (sería
  sobre-diseño), solo se deja la forma general.
- **El subcomando de la Fase 1:** `investigate TICKER` (ej.
  `python -m investmentops investigate AAPL`). Un único argumento
  posicional obligatorio, sin flags adicionales en esta fase:
  - Sin `--format` (formato de salida): explícitamente una capacidad de
    la Fase 2 (`ROADMAP.md`: "La salida es texto simple en consola").
  - Sin `--config`: `investigate(ticker, config=None, ...)`
    (`investmentops.core.orchestrator`) ya resuelve `config.local.toml`
    automáticamente por convención; no hay caso de uso real que
    justifique apuntar a otra ruta desde la CLI en el MVP.
- Deja explícitamente fuera de alcance (para las tareas siguientes de la
  misma sección de `TASKS.md`): el parseo real con `argparse`, la
  validación del ticker, la conexión con `investigate(...)`, la
  impresión del resultado en consola y el manejo de mensajes de error.

## Decisiones tomadas

- **Subcomandos desde la Fase 1, aunque hoy solo exista uno
  (`investigate`).** Alternativa considerada y descartada: un único
  comando plano (`python -m investmentops TICKER`). Se prefirió
  subcomandos porque `ARCHITECTURE.md` y `ROADMAP.md` ya dejan explícito
  que habrá más de un comando (comparar, listar, watchlist), y migrar de
  "comando plano" a "subcomandos" más adelante sería un cambio de
  sintaxis disruptivo para quien ya esté usando la herramienta.
- **Nombre del subcomando en inglés (`investigate`), no en español.**
  Consistente con el resto del código del proyecto (módulos, funciones y
  excepciones ya en inglés, ej. la función `investigate()` ya existente
  en el orquestador), reservando el español para los mensajes dirigidos
  al usuario (prompts, mensajes de error) tal como ya se hace en todo el
  proyecto.
- **Ningún flag nuevo en esta tarea.** Tanto `--format` como `--config`
  se consideraron y se descartaron explícitamente por las razones ya
  anotadas arriba, siguiendo el criterio de no sobre-diseñar ya aplicado
  en otras decisiones del proyecto (ver `CACHE.md`, sección "Qué
  determina 'reciente'").

## Validación realizada

Revisión manual del documento contra `ARCHITECTURE.md` (componente 1,
"CLI": "no contiene lógica financiera ni de formateo de reportes; delega
todo") y contra la firma ya existente de
`investmentops.core.orchestrator.investigate(ticker, *, config=None,
provider=None)`, confirmando que la sintaxis propuesta (`investigate
TICKER`) mapea directamente a esa función sin necesidad de argumentos
adicionales en esta fase. No se ejecutó ninguna prueba porque esta tarea
no introduce código.

## Archivos creados o modificados

Creados:
- `investmentops/cli/CLI.md` (nuevo)

Modificados:
- `TASKS.md` (primera tarea de la sección "CLI" marcada como completada,
  con referencia inline a `investmentops/cli/CLI.md`)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`,
`investmentops/cli/__init__.py`, `investmentops/__main__.py` (la
implementación del parseo real es la tarea siguiente, no esta),
`investmentops/core/orchestrator.py` (ni `investigate` ni ninguna otra
función del orquestador cambiaron), ningún otro módulo de código Python
existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`), sin relevancia para esta tarea porque no se
escribió código ni pruebas.

## Próxima tarea recomendada

La siguiente tarea sin marcar en `TASKS.md`, sección "CLI", es:

2. *"Implementar el parseo del argumento ticker."*

Nota para la próxima conversación:
- Ya existe la sintaxis decidida en `investmentops/cli/CLI.md`:
  `python -m investmentops investigate TICKER`, vía `argparse` con
  `add_subparsers` (un único subparser, `investigate`, con un argumento
  posicional obligatorio `TICKER`).
- Esta tarea es puramente de **parseo de argumentos** (construir el
  `ArgumentParser`/subparsers y extraer el valor de `TICKER`), sin tocar
  todavía: la validación del contenido del ticker (tarea separada
  siguiente), la conexión con `investigate(...)` (otra tarea separada),
  ni la impresión de resultados o manejo de errores en consola (las dos
  últimas tareas de la sección).
- El lugar natural para esta función es
  `investmentops/cli/__init__.py` (hoy solo tiene el docstring de
  responsabilidad de la capa) o un módulo nuevo dentro de
  `investmentops/cli/` (ej. `investmentops/cli/parser.py`) si se
  prefiere mantener `__init__.py` como punto de re-exportación, mismo
  patrón ya usado en otras capas del proyecto (ej.
  `investmentops/analysis_engines/__init__.py` re-exportando desde
  `contracts.py`).
