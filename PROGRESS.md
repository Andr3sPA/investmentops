# InvestmentOps — Progreso

**Última actualización:** 2026-07-16

## Última tarea completada

Fase 1 → CLI → *"Implementar mensajes de error legibles en consola ante fallos del flujo."*

Con esta tarea se completa por entero la sección "CLI" de la Fase 1 en `TASKS.md`.

## Verificación previa (sin duplicar trabajo)

Antes de implementar, se confirmó que esta tarea **no** estaba satisfecha
todavía: `investmentops/__main__.py` ya capturaba `ConfigError`, pero con
un mensaje mínimo sin prefijo claro (`f"[config] {exc}"`), impreso con
`print()` normal (es decir, mezclado con `stdout`, no separado a
`stderr`), y sin que el proceso terminara con un código de salida
distinto de `0` ante ese fallo. Además, todo el flujo vivía directamente
dentro del bloque `if __name__ == "__main__":`, sin una función
invocable ni testeable de forma aislada — no existía ningún archivo de
pruebas para `investmentops.__main__`. Por lo tanto, esta tarea sí
requería código nuevo.

Se revisó también qué otros fallos de flujo podrían llegar a escapar
hasta este punto: `investigate()` (`investmentops/core/orchestrator.py`)
ya captura `DataProviderError`, `NormalizationError`, `PromptError`,
`AgentProviderSelectionError` y `AIProviderError`, traduciéndolos a
`ResearchFailure` dentro del propio `ResearchResult` (ya presentados por
`format_research_result`, ver la tarea anterior). El único fallo que
puede escapar de `dispatch` en el uso normal de la CLI
(`config=None`, cada pieza del pipeline resuelve `config.local.toml`
por sí misma) es `ConfigError`. Los argumentos inválidos de `argparse`
(ticker vacío, subcomando ausente/desconocido, `--help`) ya terminan el
proceso con un mensaje legible en `stderr` vía el mecanismo estándar de
`argparse` (`SystemExit`), sin necesidad de intervención adicional.

## Qué se implementó

**`investmentops/__main__.py`** (modificado) — se extrajo el flujo
completo a una función `main(argv: Sequence[str] | None = None) -> int`,
en vez de dejarlo solo en el bloque `if __name__ == "__main__":`:

- `main()` llama a `parse_args(argv)` (propaga `SystemExit` de
  `argparse` sin capturarlo, comportamiento estándar y ya legible).
- Si `dispatch(args)` tiene éxito, imprime
  `format_research_result(result)` en `stdout` y devuelve `0`.
- Si `dispatch(args)` levanta `ConfigError`, imprime
  `f"Error de configuración: {exc}"` en **`stderr`** (con
  `file=sys.stderr`, para no mezclarlo con la salida normal del programa
  ni con scripts que redirijan solo `stdout`) y devuelve `1`. El mensaje
  de `ConfigError` ya trae, desde `investmentops/config/__init__.py`, la
  instrucción concreta para resolverlo (`cp config.example.toml
  config.local.toml`), así que el nuevo prefijo `"Error de
  configuración: "` solo aporta contexto sin reconstruir esa guía.
- El bloque `if __name__ == "__main__":` quedó reducido a
  `sys.exit(main())`, propagando el código de salida devuelto por
  `main()` (mecanismo estándar para que el proceso real termine con el
  código correcto).
- Se actualizó por completo el docstring del módulo, documentando el
  alcance exacto de esta tarea: qué fallos puede dejar escapar
  `dispatch` (solo `ConfigError`), por qué los argumentos inválidos de
  `argparse` no requieren manejo adicional, y el contrato de `main()`.

**`investmentops/tests/test_main.py`** (nuevo) — cubre:
- Éxito: `main()` devuelve `0` e imprime el resultado formateado en
  `stdout`, sin nada en `stderr` (mockeando `dispatch` para no depender
  de una llamada de red real ni de un `config.local.toml` real en
  disco).
- `ConfigError`: `main()` devuelve `1`, imprime un mensaje con el
  prefijo `"Error de configuración"` en `stderr`, y no imprime nada en
  `stdout`.
- Argumentos inválidos (`ticker` ausente, subcomando desconocido):
  `main()` deja escapar `SystemExit` (comportamiento estándar de
  `argparse`, no interceptado).
- `main(argv=[...])` no depende de `sys.argv` real (se verifica
  monkeypencheando `sys.argv` a un valor distinto del `argv` explícito
  pasado a `main()`).

## Decisiones tomadas

- **Extraer `main()` en vez de solo mejorar el mensaje en el bloque
  `if __name__`.** Sin una función invocable, esta tarea no era testeable
  sin capturar un proceso completo (`subprocess`), lo cual habría sido
  más frágil y lento. Extraer `main(argv=None) -> int` es un cambio
  mínimo y estándar en CLIs de Python, consistente con el patrón ya usado
  en `investmentops.cli.parse_args` (que también acepta `argv=None`).
- **Mensaje de error a `stderr`, no a `stdout`.** Antes, el mensaje de
  `ConfigError` se imprimía con `print()` normal (`stdout`), igual que el
  resultado exitoso. Separar ambos flujos es una práctica estándar de
  CLIs: permite a quien invoque el programa distinguir salida útil de
  mensajes de error (ej. `python -m investmentops investigate AAPL >
  reporte.txt` no debería terminar con un mensaje de error dentro del
  archivo de salida).
- **Código de salida `1` ante `ConfigError`.** Antes, el proceso siempre
  terminaba con código `0` (por ausencia de `sys.exit(...)` con un valor
  explícito), incluso cuando el flujo no pudo ejecutarse en absoluto.
  Devolver `1` sigue la convención estándar de Unix (`0` = éxito, distinto
  de cero = error) y permite que scripts que invoquen esta CLI detecten
  el fallo mediante el código de salida, no solo parseando el texto.
- **No se traduce ningún otro tipo de excepción.** Se revisó
  explícitamente que `investigate()` ya no deja escapar
  `DataProviderError`, `NormalizationError`, `PromptError`,
  `AgentProviderSelectionError` ni `AIProviderError` (los traduce a
  `ResearchFailure`, ya presentados por `format_research_result`), y que
  los errores de `argparse` ya son legibles por su propio mecanismo
  estándar. Agregar un `except Exception` genérico "por si acaso" iría
  contra el principio de no inventar manejo de errores para casos que no
  están identificados como reales en esta fase del proyecto (ver
  `ARCHITECTURE.md`, "Manejo de errores y limitaciones": declarar
  honestamente lo que se maneja, no aparentar cobertura genérica).

## Archivos creados o modificados

Creados:
- `investmentops/tests/test_main.py` (nuevo)

Modificados:
- `investmentops/__main__.py` (se extrajo `main(argv=None) -> int`; el
  mensaje de `ConfigError` ahora va a `stderr` con un prefijo claro y el
  proceso termina con código de salida `1`; docstring del módulo
  reescrito)
- `TASKS.md` (tarea "Implementar mensajes de error legibles en consola
  ante fallos del flujo" marcada como completada; con esto se completa
  por entero la sección "CLI" de la Fase 1)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`,
`CONFIGURATION.md`, `config.example.toml`, `investmentops/cli/CLI.md`,
`investmentops/cli/__init__.py`, `investmentops/core/orchestrator.py`,
ningún otro módulo de código Python existente.

## Problemas encontrados

Ninguno nuevo. Se mantiene el hallazgo ya anotado en actualizaciones
anteriores sobre la duplicación de carpetas de pruebas (`tests/` vs.
`investmentops/tests/`); el archivo de pruebas nuevo de esta tarea se
colocó en `investmentops/tests/`, consistente con el resto de módulos de
código de la Fase 1 (en particular con `test_cli.py`,
`test_cli_dispatch.py` y `test_cli_output.py`, que también viven ahí).

## Próxima tarea recomendada

Con esta tarea se completa por entero la sección "CLI" de la Fase 1.
Las tareas restantes de `TASKS.md` para la Fase 1 son las de
"Verificación" (pruebas manuales de punta a punta, no tareas de código
nuevo per se: probar con un ticker real, probar con un ticker
inválido/inexistente, confirmar que las interpretaciones vienen del
modelo de lenguaje y no de reglas fijas, y confirmar que cambiar el
proveedor de IA de un agente vía configuración no requiere tocar
código). Con eso, la Fase 1 completa (`ROADMAP.md`) quedaría cerrada de
punta a punta.

Nota para la próxima conversación: si se decide abordar la sección
"Verificación", conviene aclarar primero si el objetivo es (a) dejar
constancia por escrito de que esas verificaciones manuales se realizaron
(ej. una sección nueva en `PROGRESS.md` con los resultados observados),
o (b) tratarlas como fuera de alcance de este flujo de trabajo
automatizado por tratarse explícitamente de pasos *manuales* (requieren
una API key real de FMP y de Anthropic, y ejecutar el CLI de verdad).
Si se prefiere continuar con trabajo de código, la Fase 1 ya está
completa y la siguiente pieza natural sería iniciar la Fase 2 ("Generar
un reporte profesional"), comenzando por su primera tarea: "Definir la
estructura común que consumirán los generadores (a partir del
'Resultado de investigación')".
