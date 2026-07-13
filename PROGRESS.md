# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Setup del proyecto → *"Configurar el gestor de dependencias y el entorno del proyecto."*

## Cambios realizados

- Se agregó `pyproject.toml` en la raíz del proyecto, con metadata estándar (PEP 621):
  - `name = "investmentops"`, `version = "0.1.0"`, `requires-python = ">=3.10"`.
  - `dependencies = []`: sin dependencias de negocio todavía, porque ningún proveedor de datos, proveedor de IA ni capa funcional está implementada aún (ver `TASKS.md`).
  - `[project.optional-dependencies].dev`: `pytest` (pruebas) y `ruff` (lint), como base mínima para desarrollo sin sumar herramientas innecesarias en esta etapa.
  - `[tool.setuptools.packages.find]` configurado para descubrir el paquete `investmentops` y sus subpaquetes ya existentes.
  - `[tool.pytest.ini_options]` apuntando a `testpaths = ["tests"]`.
  - `[tool.ruff]` con configuración mínima (`line-length`, `target-version`).
- Se agregó `.python-version` (`3.11`) para fijar la versión de Python del entorno local, compatible con herramientas como `pyenv` o `uv` que la leen automáticamente.
- Se agregó `.gitignore` con las exclusiones estándar de un proyecto Python local: entornos virtuales, bytecode, cachés de pytest/ruff/mypy, artefactos de build, y también exclusiones específicas de este proyecto (archivo de configuración local con credenciales, aún no implementado, y la carpeta de caché local de datos descrita en `ARCHITECTURE.md`).
- Se creó la carpeta **nueva** `tests/`, con un archivo `tests/test_environment.py`: una prueba de humo que solo confirma que `investmentops` y todos sus subpaquetes se importan correctamente tras instalar el entorno. No prueba lógica de negocio (no existe todavía); su único propósito es validar que la configuración del gestor de dependencias es correcta.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `pyproject.toml`
- `.python-version`
- `.gitignore`
- `tests/test_environment.py` (dentro de la carpeta nueva `tests/`)

Modificados:
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `prompts/README.md`, y ningún archivo dentro de `investmentops/` (esta tarea no toca lógica de negocio).

## Decisiones técnicas importantes

- **Gestor de dependencias elegido: `pip` + entornos virtuales estándar (`venv`), con metadata en `pyproject.toml` (PEP 621)**, en vez de herramientas como Poetry o uv. Motivo: es la opción con menor fricción para un proyecto personal, de un solo usuario y sin publicación como paquete (`GOALS.md` descarta explícitamente que sea un producto multi-tenant), no requiere instalar un gestor adicional fuera del ecosistema estándar de Python, y es la más ampliamente compatible con cualquier entorno local. Si en el futuro el número de dependencias crece de forma significativa, esta decisión puede revisarse sin que afecte la arquitectura del proyecto.
- **`dependencies = []` en `pyproject.toml`**: se dejó vacío deliberadamente. Añadir dependencias de proveedores de datos o de IA antes de que esos módulos existan sería anticipar decisiones de implementación que corresponden a tareas posteriores de `TASKS.md` (ej. "Elegir el proveedor de datos financieros fundamentales", "Implementar al menos una integración concreta" de proveedor de IA). Cada tarea futura que dependa de una librería externa deberá añadirla aquí en su propia conversación.
- **Dependencias de desarrollo mínimas (`pytest`, `ruff`)**: se incluyen porque el proyecto ya declara en `TASKS.md` una sección de "Verificación" en cada fase; tener un framework de pruebas y un linter listos desde el entorno base evita tener que reconfigurar el proyecto más adelante. No se agregó `mypy` ni otras herramientas para no sumar configuración innecesaria antes de que exista código que tipar.
- **Carpeta `tests/` con una única prueba de humo**: se creó para que la referencia a `testpaths = ["tests"]` en `pyproject.toml` sea válida y para dejar verificado, de forma automatizable, que la configuración de empaquetado (`[tool.setuptools.packages.find]`) efectivamente descubre todos los subpaquetes existentes. Deliberadamente no se agregaron pruebas de lógica de negocio: esa lógica no existe aún.
- **`.python-version` fijado en `3.11`**: dentro del rango declarado en `pyproject.toml` (`>=3.10`), se eligió `3.11` como versión de desarrollo por ser una versión estable y ampliamente disponible al momento de esta tarea, sin acoplar el proyecto a una versión más nueva que pueda no estar instalada en el entorno del usuario.
- **Verificación realizada**: se creó un entorno virtual temporal, se instaló el proyecto en modo editable (`pip install -e .`) y se confirmó que `investmentops` y los siete subpaquetes existentes se importan sin errores, validando que `pyproject.toml` está correctamente configurado. No fue posible instalar `pytest`/`ruff` (extra `dev`) en el entorno de verificación de esta conversación por no tener acceso a red; esto no es una limitación de la configuración del proyecto, sino del entorno de esta sesión — en una máquina con acceso normal a internet, `pip install -e ".[dev]"` funcionará sin cambios.

## Problemas encontrados

- Ninguno relativo a la configuración en sí. Durante la verificación en el entorno de esta conversación no había acceso a red, lo que impidió descargar `pytest` y `ruff` desde PyPI; se validó en su lugar que la instalación editable del paquete base (`pip install -e .`) y la importación de todos los subpaquetes funcionan correctamente, que es lo que depende directamente de la configuración de `pyproject.toml`.

## Próxima tarea recomendada

Fase 1 → Setup del proyecto → *"Definir el formato y la ubicación del archivo de configuración local (API keys de datos, API keys/endpoints de proveedores de IA, qué proveedor usa cada agente, rutas de caché)."*
