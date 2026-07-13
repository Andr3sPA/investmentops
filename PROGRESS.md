# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'analysis engine' / agente de IA (entrada: modelo de dominio normalizado + métricas precalculadas cuando aplique; salida: resultado estructurado)."*

## Cambios realizados

- Se creó `investmentops/analysis_engines/contracts.py`, que define el contrato común que debe cumplir todo motor de análisis / agente de IA (ver ARCHITECTURE.md, componente 5):
  - `AnalysisEngineError`: excepción común para señalar cualquier fallo del agente (el proveedor de IA no responde, su respuesta no se puede interpretar, faltan datos imprescindibles), de forma que el orquestador pueda capturarla y continuar con los demás análisis en vez de detener todo el flujo o inventar hallazgos.
  - `AnalysisProvenance`: dataclass inmutable con la procedencia de la interpretación — `ai_provider`, `ai_model` y `generated_at` — exigida por `ARCHITECTURE.md` ("metadatos de procedencia... qué proveedor y modelo de IA generó la interpretación").
  - `AnalysisResult`: dataclass inmutable que agrupa `analysis_id`, `findings` (hallazgos en lenguaje natural producidos por el agente), `supporting_metrics` (métricas calculadas de forma determinística), `limitations` (advertencias) y `provenance` (`AnalysisProvenance`). Es el tipo "Resultado de análisis" descrito en `ARCHITECTURE.md`, "Modelo de datos interno".
  - `AnalysisEngine`: `Protocol` (tipado estructural, `runtime_checkable`) con un único método `analyze(company_data, metrics=None) -> AnalysisResult`. Cualquier objeto que exponga ese método cumple el contrato, sin necesidad de heredar de una clase base concreta.
- Se actualizó `investmentops/analysis_engines/__init__.py` para re-exportar `AnalysisEngine`, `AnalysisEngineError`, `AnalysisProvenance` y `AnalysisResult` desde `contracts.py`, de forma que el resto del sistema los importe directamente desde `investmentops.analysis_engines`.
- Se agregó `tests/test_analysis_engines_contracts.py`, con un agente mínimo de prueba (`_DummyEngine`) que cumple el contrato y otro que falla (`_FailingEngine`), cubriendo: cumplimiento del protocolo `AnalysisEngine`, forma del resultado (`AnalysisResult` + `AnalysisProvenance`), el carácter opcional del parámetro `metrics`, propagación de `AnalysisEngineError`, e inmutabilidad de ambas dataclasses.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/analysis_engines/contracts.py`
- `tests/test_analysis_engines_contracts.py`

Modificados:
- `investmentops/analysis_engines/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `investmentops/config/__init__.py`, `investmentops/__main__.py`, `investmentops/__init__.py`, `investmentops/data_providers/__init__.py`, `investmentops/data_providers/contracts.py`, `tests/test_environment.py`, `tests/test_config.py`, `tests/test_data_providers_contracts.py`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `data_layer`, `ai_providers`, `reports`), que siguen sin implementación.

No se implementó ningún agente concreto (eso corresponde a las secciones "Agente de análisis: salud financiera" y "Agente de análisis: valoración" de `TASKS.md`, tareas posteriores): este trabajo solo define el contrato/interfaz.

## Decisiones técnicas importantes

- **Mismo patrón que `investmentops.data_providers.contracts`**: `Protocol` + `runtime_checkable` en vez de una clase base abstracta, dataclasses `frozen=True` para el resultado y su procedencia, y una excepción propia (`AnalysisEngineError`) heredando de `RuntimeError`. Mantener el mismo patrón entre contratos reduce la carga cognitiva al leer el código y refuerza el principio de `ARCHITECTURE.md` de que el orquestador conoce interfaces, no implementaciones concretas.
- **`company_data: Any` en `AnalysisEngine.analyze`**: la estructura concreta del modelo de dominio normalizado ("Empresa", "Estados financieros normalizados", "Datos de mercado") todavía no está definida — son tareas separadas y posteriores dentro de "Contratos e interfaces" en `TASKS.md`. Tipar `company_data` de forma laxa ahora evita acoplar este contrato genérico a un diseño de modelo de dominio que aún no existe, igual que `RawProviderData.payload` se dejó como `Any` en el contrato de proveedores de datos.
- **`metrics: Mapping[str, Any] | None = None`**: se deja opcional porque no todos los agentes necesariamente reciben sus métricas precalculadas desde afuera; algunos pueden calcularlas internamente a partir de `company_data`. Lo que el contrato sí exige es que las métricas usadas terminen expuestas en `AnalysisResult.supporting_metrics`, de forma que el resultado final siempre sea trazable y reproducible, sin importar en qué punto del flujo se calcularon.
- **`findings` como `Sequence[str]` en vez de un único bloque de texto**: permite que un agente exprese varios hallazgos independientes (ej. uno por ratio interpretado) sin forzar una única cadena larga; los generadores de reporte (Fase 2) pueden decidir si los concatenan o los listan.
- **Restricción "nunca un veredicto de compra/venta" documentada solo como comentario, no forzada estructuralmente**: el contrato no puede impedir en tiempo de ejecución que un agente redacte una recomendación dentro de `findings`, porque es texto libre generado por un LLM. Esa restricción se refuerza en la capa de prompts (ver `prompts/README.md`) y debe verificarse manualmente al implementar cada agente (ver TASKS.md, "Verificación" de la Fase 1).
- **`AnalysisEngineError` separado de `DataProviderError`**: aunque ambos son fallos operacionales que el orquestador debe capturar, mantenerlos como tipos distintos permite que el "Resultado de investigación" (tarea futura) distinga en su reporte si lo que falló fue obtener datos o interpretarlos, que son fallos con causas y remedios distintos para el usuario.
- **Sin manejo de reintentos ni validación del contenido de `findings`/`limitations` en el contrato**: eso es responsabilidad de la implementación concreta de cada agente (parseo de la respuesta del proveedor de IA) y de la interfaz de proveedores de IA (aún pendiente, ver TASKS.md), no del contrato en sí.

## Problemas encontrados

Ninguno. Se verificó manualmente que:
- Un agente mínimo que implementa `analyze(company_data, metrics=None) -> AnalysisResult` satisface `isinstance(agente, AnalysisEngine)`.
- `AnalysisResult` y `AnalysisProvenance` son inmutables (intentar reasignar un atributo lanza `AttributeError`).
- Un agente que levanta `AnalysisEngineError` propaga el error correctamente y con su mensaje.
- El parámetro `metrics` es efectivamente opcional: al omitirlo, el agente de prueba usa sus propias métricas por defecto.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir el contrato de 'AI provider' (entrada: prompt + datos estructurados; salida: respuesta del modelo + metadatos de proveedor/modelo usado), común para Gemini, Claude, OpenAI y Ollama."*
