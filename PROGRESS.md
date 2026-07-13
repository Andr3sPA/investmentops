# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Setup del proyecto → *"Definir el formato y la ubicación del archivo de configuración local (API keys de datos, API keys/endpoints de proveedores de IA, qué proveedor usa cada agente, rutas de caché)."*

## Cambios realizados

- Se agregó `CONFIGURATION.md` en la raíz del proyecto, documentando:
  - El formato elegido (TOML) y su justificación.
  - La ubicación de dos archivos distintos: `config.local.toml` (real, con credenciales, no versionado) y `config.example.toml` (plantilla versionada, sin credenciales).
  - La estructura completa por secciones: `[cache]`, `[data_providers.<nombre>]`, `[ai_providers.<nombre>]`, `[ai_providers.default]`, `[agents]` (selección de proveedor de IA por agente) y `[output]`.
  - Notas de seguridad y el procedimiento de bootstrap (`cp config.example.toml config.local.toml`).
  - Qué queda explícitamente fuera de esta tarea (la carga/parseo real del archivo, que es la tarea siguiente en `TASKS.md`).
- Se agregó `config.example.toml` en la raíz del proyecto: la plantilla versionable con la estructura completa definida en `CONFIGURATION.md`, con todos los valores sensibles vacíos o de ejemplo.
- No se creó `config.local.toml`: por definición no debe versionarse ni distribuirse, y esta tarea es solo de definición, no de implementación de la carga.
- No se modificó `.gitignore`: el patrón `config.local.*` ya definido en la tarea anterior cubre `config.local.toml` sin cambios (verificado).
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `CONFIGURATION.md`
- `config.example.toml`

Modificados:
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `tests/test_environment.py`, y ningún archivo dentro de `investmentops/` (esta tarea no toca código Python ni lógica de negocio).

## Decisiones técnicas importantes

- **Formato TOML**: se eligió por consistencia con `pyproject.toml` (ya usado en el proyecto), por tener soporte nativo de lectura en la librería estándar de Python 3.11 (`tomllib`, sin dependencia externa nueva) y porque su estructura por secciones se ajusta bien a la necesidad de agrupar credenciales por proveedor de datos y por proveedor de IA. Se descartó YAML (requeriría una dependencia externa para parsear y es más sensible a errores de indentación en un archivo con secretos) y `.env` (no soporta bien estructura anidada como "un proveedor de IA por agente").
- **Dos archivos, no uno**: se separó el archivo real (`config.local.toml`, con secretos, no versionado) de una plantilla versionada (`config.example.toml`, sin secretos). Esto permite que cualquiera que clone el repositorio sepa exactamente qué configurar sin exponer ningún dato sensible, y es una práctica estándar para proyectos que manejan API keys.
- **Sección `[agents]` como mapeo explícito agente → proveedor de IA**: se decidió así (en vez de, por ejemplo, que cada agente tenga su proveedor embebido en su propio código) porque es exactamente el mecanismo de extensibilidad que exige `ARCHITECTURE.md`: "cambiar de proveedor... sin que el agente que lo invoca conozca los detalles". Un agente sin entrada explícita cae en `[ai_providers.default]`, evitando tener que listar todos los agentes desde el día uno.
- **Ubicación en la raíz del proyecto**: se mantiene junto a los demás archivos de configuración ya existentes (`pyproject.toml`, `.gitignore`), en vez de crear una carpeta `config/` dedicada, porque por ahora es un único archivo por tipo (real/plantilla) y no hay necesidad de subdividir.
- **No se implementó ninguna lógica de carga**: la lectura de `config.local.toml` con `tomllib`, su validación y su exposición al resto del sistema son responsabilidad de la tarea siguiente ("Implementar la carga de ese archivo de configuración al iniciar el sistema"), que se hará en su propia conversación según el flujo de trabajo acordado.

## Problemas encontrados

- Ninguno. Se validó que `config.example.toml` es TOML válido parseándolo con `tomllib` (librería estándar de Python 3.11), y que el patrón `config.local.*` de `.gitignore` efectivamente cubre `config.local.toml`.

## Próxima tarea recomendada

Fase 1 → Setup del proyecto → *"Implementar la carga de ese archivo de configuración al iniciar el sistema."*
