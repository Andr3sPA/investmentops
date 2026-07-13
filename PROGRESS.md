# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Setup del proyecto → *"Implementar la carga de ese archivo de configuración al iniciar el sistema."*

## Cambios realizados

- Se creó el subpaquete `investmentops/config/` con `investmentops/config/__init__.py`, que implementa:
  - `load_config(path=None)`: lee y parsea `config.local.toml` usando `tomllib` (librería estándar de Python 3.11, sin dependencias externas), y devuelve su contenido como `dict` anidado, sin validar ni completar valores por defecto (fuera de alcance de esta tarea, ver `CONFIGURATION.md`).
  - `_default_config_path()`: resuelve la ruta por defecto de `config.local.toml` en la raíz del proyecto (junto a `pyproject.toml` y `config.example.toml`), sin asumir un directorio de trabajo concreto.
  - `ConfigError`: excepción propia, con mensajes legibles en español, para dos casos: archivo ausente (indicando el comando de bootstrap `cp config.example.toml config.local.toml`) y archivo presente pero con TOML inválido.
- Se actualizó `investmentops/__main__.py` para invocar `load_config()` al iniciar el sistema (`python -m investmentops`), mostrando un mensaje de éxito si se cargó correctamente, o el mensaje de `ConfigError` si el archivo no existe o es inválido — sin detener la ejecución con una traza sin contexto.
- Se actualizó `investmentops/__init__.py` para documentar la nueva capa `config` dentro de la estructura de paquetes descrita en el docstring.
- Se agregó `tests/test_config.py` con pruebas para: carga exitosa de un TOML válido, `ConfigError` cuando el archivo no existe, `ConfigError` cuando el archivo existe pero no es TOML válido, y que la ruta por defecto apunta correctamente a la raíz del proyecto.
- Se actualizó `tests/test_environment.py` para incluir `investmentops.config` en la lista de subpaquetes que deben poder importarse.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/config/__init__.py`
- `tests/test_config.py`

Modificados:
- `investmentops/__main__.py`
- `investmentops/__init__.py`
- `tests/test_environment.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `data_providers`, `data_layer`, `analysis_engines`, `ai_providers`, `reports`), que siguen sin implementación.

No se creó `config.local.toml`: sigue siendo un archivo local, no versionado, que cada usuario genera a partir de `config.example.toml`. El comportamiento de `load_config()` ante su ausencia se cubre explícitamente en las pruebas y en el mensaje de `ConfigError`.

## Decisiones técnicas importantes

- **`tomllib` de la librería estándar, sin dependencias nuevas**: consistente con la justificación ya dada en `CONFIGURATION.md` para elegir TOML; Python 3.11 (fijado en `.python-version`) lo incluye de forma nativa, en modo binario (`"rb"`), que es lo que `tomllib` requiere.
- **Devolver el `dict` crudo, sin validar ni tipar**: la tarea de `TASKS.md` pide explícitamente solo la *carga*; la validación de claves requeridas es una tarea separada y futura (ya anotada como fuera de alcance en `CONFIGURATION.md`). Evita acoplar esta pieza pequeña a la forma final que tomará la configuración cuando se implementen los proveedores concretos.
- **Excepción propia `ConfigError` en vez de dejar propagar `FileNotFoundError`/`tomllib.TOMLDecodeError`**: permite que quien use este módulo (por ahora `__main__.py`, más adelante la CLI real) capture un único tipo de error con un mensaje ya pensado para el usuario final, en español y con el comando exacto de bootstrap, en vez de una traza técnica.
- **Ruta por defecto calculada desde `__file__`, no desde el directorio de trabajo actual**: `Path(__file__).resolve().parent.parent.parent` ubica la raíz del proyecto sin importar desde qué carpeta se ejecute `python -m investmentops`, evitando que el comando falle solo por no estar parado en la raíz.
- **Integración mínima en `__main__.py`**: dado que la CLI real (`investmentops.cli`) todavía no está implementada (tarea posterior en `TASKS.md`), se conectó `load_config()` al único punto de entrada ejecutable que existe hoy, de forma no bloqueante (si falla, se informa y el proceso simplemente termina ese mensaje, sin lanzar una excepción sin capturar). Cuando se implemente la CLI real, esta misma función se invocará desde ahí.
- **Sin `config.local.toml` de prueba en el repo**: las pruebas usan `tmp_path` de `pytest` para crear archivos TOML temporales (válidos e inválidos) en vez de depender de un archivo real de configuración, manteniendo las pruebas aisladas y sin necesidad de credenciales.

## Problemas encontrados

Ninguno. Se verificó manualmente que `load_config()`:
- Carga correctamente un TOML válido y expone sus secciones anidadas (`cache`, `ai_providers.default`, etc.) tal como se accederían en código futuro.
- Lanza `ConfigError` con un mensaje claro cuando el archivo no existe, incluyendo el comando de bootstrap.
- `_default_config_path()` resuelve correctamente a la raíz del proyecto en este entorno de trabajo.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'data provider' (entrada: ticker; salida: datos crudos + metadatos de procedencia)."*
