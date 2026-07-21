# InvestmentOps — Configuración local

Este documento define **el formato y la ubicación** del archivo de
configuración local de InvestmentOps, conforme a lo descrito en
`ARCHITECTURE.md` (sección "Manejo de configuración y credenciales"):

> "La configuración (API keys de proveedores de datos, API keys/endpoints
> de proveedores de IA, qué proveedor de IA usa cada agente, preferencias
> de formato de salida, rutas de caché) se gestiona mediante archivos de
> configuración locales, no mediante un sistema de gestión de usuarios."

Esta tarea **solo define** el formato, la ubicación y la estructura del
archivo. La lógica que lo lee al iniciar el sistema es una tarea
posterior y separada (ver `TASKS.md`, "Implementar la carga de ese
archivo de configuración al iniciar el sistema").

## Formato elegido: TOML

Se eligió **TOML** en vez de YAML, JSON o `.env`, por los siguientes
motivos:

- El proyecto ya usa TOML para su propia metadata (`pyproject.toml`), lo
  que mantiene un único formato de configuración en todo el repositorio.
- Python 3.11 (versión fijada en `.python-version`) incluye `tomllib` en
  la librería estándar para lectura de TOML, sin sumar una dependencia
  externa nueva solo para parsear configuración.
- A diferencia de `.env` (pares clave-valor planos), TOML permite
  estructurar la configuración en secciones (`[cache]`, `[ai_providers]`,
  etc.), lo cual es necesario aquí porque hay varios proveedores de datos
  y de IA, cada uno con sus propias credenciales.
- A diferencia de YAML, TOML no depende de la indentación para expresar
  estructura y no requiere una librería externa para escribirlo/leerlo en
  Python 3.11+, lo que reduce superficie de error en un archivo que
  contiene credenciales.

## Ubicación

- **Archivo real de configuración (con credenciales):** `config.local.toml`,
  en la **raíz del proyecto**.
  - Ya está excluido de git por el patrón `config.local.*` definido en
    `.gitignore` desde la tarea de configuración del entorno. No requiere
    cambios adicionales al `.gitignore`.
  - Este archivo **no se versiona** y **no se distribuye**: cada usuario
    lo crea localmente a partir de la plantilla.
- **Plantilla versionada (sin credenciales reales):** `config.example.toml`,
  también en la raíz del proyecto. Se versiona en git para que cualquiera
  que clone el proyecto sepa qué claves de configuración existen y con
  qué estructura, sin exponer ningún secreto.

Bootstrap esperado para un usuario nuevo del proyecto:

```bash
cp config.example.toml config.local.toml
# luego editar config.local.toml y completar las API keys reales
```

## Estructura del archivo

El archivo se organiza en las siguientes secciones, alineadas con lo que
exige `ARCHITECTURE.md`:

- **`[cache]`** — ruta local donde la capa de normalización y
  almacenamiento (`investmentops.data_layer`) persiste los datos
  normalizados y el histórico de consultas.
- **`[data_providers.<nombre>]`** — una sección por proveedor de datos
  configurado (ej. `[data_providers.fundamentals]` para el proveedor de
  datos financieros fundamentales de la Fase 1, `[data_providers.news]`
  para el proveedor de noticias de la Fase 4, ver
  `investmentops/data_providers/NEWS_PROVIDER.md`, y
  `[data_providers.comparables]` para el proveedor de empresas
  pares/comparables de la Fase 5, ver
  `investmentops/data_providers/COMPARABLES_PROVIDER.md`). Cada una
  guarda su propia API key y, si aplica, la URL base del proveedor —
  incluso si varias secciones apuntan hoy al mismo proveedor externo
  (como `fundamentals`, `news` y `comparables`, las tres resueltas hoy
  contra FMP), se mantienen separadas para no acoplar accidentalmente su
  configuración.
- **`[ai_providers.<nombre>]`** — una sección por proveedor de IA
  soportado por la interfaz común (`investmentops.ai_providers`):
  `anthropic`, `gemini`, `openai`, `ollama`. Cada una guarda su API key
  (u otro dato de acceso) y, si aplica, su endpoint/URL base — relevante
  sobre todo para Ollama, que corre de forma local.
- **`[ai_providers.default]`** — proveedor y modelo de IA usados por
  cualquier agente que no tenga una asignación específica en `[agents]`.
- **`[agents]`** — mapeo explícito de qué proveedor de IA usa cada agente
  de análisis (por su identificador, el mismo que se usa para localizar
  su prompt en `prompts/`, ver `prompts/README.md`). Si un agente no
  aparece aquí, se asume `[ai_providers.default]`. Esto es lo que permite
  cambiar el proveedor de un agente puntual sin tocar su código
  (principio de independencia de proveedor de `ARCHITECTURE.md`).
- **`[output]`** — preferencias de formato de salida de reportes
  (relevante desde la Fase 2) y la carpeta donde se guardan.

La estructura completa y comentada vive en `config.example.toml`.

## Seguridad

- `config.local.toml` nunca debe compartirse ni subirse a un repositorio
  remoto; el `.gitignore` ya lo excluye.
- `config.example.toml` debe mantenerse siempre con valores vacíos o de
  ejemplo (`""`, `"tu-api-key-aqui"`), nunca con credenciales reales.
- Si en el futuro se agrega un nuevo proveedor de datos o de IA (ver
  "Extensibilidad" en `ARCHITECTURE.md`), su sección correspondiente debe
  añadirse tanto a `config.example.toml` como a este documento, sin
  modificar las secciones de los proveedores ya existentes.

## Fuera de alcance de esta tarea

- La lectura/parseo de `config.local.toml` al iniciar el sistema (tarea
  siguiente en `TASKS.md`).
- La validación de que las claves requeridas estén presentes.
- Cualquier lógica de negocio que consuma estos valores (eso corresponde
  a las capas `investmentops.data_providers`, `investmentops.ai_providers`
  y `investmentops.data_layer`, aún sin implementar).