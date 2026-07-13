# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir la estructura del modelo de dominio 'Empresa' (ticker, nombre, sector, mercado)."*

## Cambios realizados

- Se creó `investmentops/data_layer/domain.py`, que define el primer modelo de dominio interno común descrito en ARCHITECTURE.md ("Modelo de datos interno"):
  - `Company`: dataclass inmutable (`frozen=True`) con la identidad básica de una empresa: `ticker`, `name`, `sector` y `market`. Es el tipo que usarán las demás capas (agentes de análisis, generadores de reportes) para referirse a una empresa de forma consistente, sin importar de qué proveedor de datos provino originalmente cada dato.
- Se actualizó `investmentops/data_layer/__init__.py` para re-exportar `Company` desde `domain.py`, de forma que el resto del sistema lo importe directamente desde `investmentops.data_layer` (mismo patrón usado en `data_providers`, `analysis_engines` y `ai_providers`).
- Se agregó `investmentops/tests/test_data_layer_domain.py`, cubriendo: que `Company` conserva correctamente sus cuatro campos, que es inmutable (intentar reasignar un atributo lanza `AttributeError`), y que el modelo no impone un formato fijo de ticker/mercado (se prueba con un ticker del mercado colombiano, relevante para GOALS.md — Tyba/Trii).
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/domain.py`
- `investmentops/tests/test_data_layer_domain.py`

Modificados:
- `investmentops/data_layer/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `investmentops/config/__init__.py`, `investmentops/__main__.py`, `investmentops/__init__.py`, `investmentops/data_providers/__init__.py`, `investmentops/data_providers/contracts.py`, `investmentops/analysis_engines/__init__.py`, `investmentops/analysis_engines/contracts.py`, `investmentops/ai_providers/__init__.py`, `investmentops/ai_providers/contracts.py`, `investmentops/tests/test_environment.py`, `investmentops/tests/test_config.py`, `investmentops/tests/test_data_providers_contracts.py`, `investmentops/tests/test_analysis_engines_contracts.py`, `investmentops/tests/test_ai_providers_contracts.py`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `reports`), que siguen sin implementación.

No se implementó ninguna transformación desde datos crudos de proveedor (`RawProviderData`) hacia `Company`: eso corresponde a la sección "Normalización y almacenamiento" de `TASKS.md`, tarea posterior. Tampoco se agregaron los modelos de dominio restantes (Estados financieros normalizados, Datos de mercado, Noticias, Comparables): cada uno tiene su propia tarea pendiente.

## Decisiones técnicas importantes

- **`investmentops/data_layer/domain.py` como módulo separado (no `__init__.py` directamente)**: se sigue el mismo patrón que `data_providers/contracts.py`, `analysis_engines/contracts.py` y `ai_providers/contracts.py` — la definición vive en un módulo propio y el `__init__.py` solo re-exporta. Esto deja espacio para que los siguientes modelos de dominio (Estados financieros normalizados, Datos de mercado, etc.) se agreguen como módulos adicionales dentro de `data_layer` sin saturar un único archivo ni romper las importaciones ya existentes.
- **`Company` como `dataclass(frozen=True)`**: mismo patrón de inmutabilidad usado en `ProviderMetadata`, `RawProviderData`, `AnalysisResult`, `AnalysisProvenance` y `AIProviderResponse`. Un modelo de dominio compartido entre capas (fuentes de datos, agentes, reportes) no debería poder mutarse accidentalmente mientras fluye por el sistema.
- **Los cuatro campos (`ticker`, `name`, `sector`, `market`) como `str` obligatorios, sin `Optional`**: TASKS.md especifica explícitamente estos cuatro campos como la estructura de "Empresa"; se mantienen simples y requeridos en esta tarea de definición de estructura. Si en el futuro un proveedor no entrega alguno de estos datos (ej. sector desconocido), la decisión de cómo representarlo (cadena vacía, valor por defecto, o volver el campo opcional) se deja para la tarea de "Normalización y almacenamiento", cuando se implemente la transformación real desde datos crudos.
- **Sin validación de contenido** (ej. que el ticker tenga un formato válido, que el mercado sea uno reconocido): igual que en `RawProviderData` y `AnalysisResult`, este contrato/modelo solo define la forma del dato. Validar formato o existencia real de una empresa es responsabilidad de una capa posterior (proveedor de datos o normalización), no de la definición de estructura en sí.
- **Texto libre para `sector` y `market`** (sin enum ni lista cerrada de valores): distintos proveedores de datos pueden reportar sectores/mercados con nomenclaturas distintas; imponer una taxonomía fija en esta etapa acoplaría el modelo de dominio a las convenciones de un proveedor específico, contradiciendo el principio de independencia de proveedor de `ARCHITECTURE.md`.

## Problemas encontrados

Ninguno. Se verificó manualmente que:
- `Company` conserva correctamente sus cuatro campos al construirse.
- `Company` es inmutable (intentar reasignar `ticker` lanza `AttributeError`).
- El modelo acepta sin problema tickers y mercados de distintas convenciones (ej. `"AAPL"`/`"NASDAQ"` y `"ECOPETROL.CL"`/`"BVC"`), sin necesidad de casos especiales en el código.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir la estructura del modelo de dominio 'Estados financieros normalizados' (ingresos, beneficios, deuda, con fuente y fecha)."*
