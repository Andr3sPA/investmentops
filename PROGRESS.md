# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir la estructura de 'Resultado de investigación' (agregación de resultados de análisis para una empresa)."*

## Cambios realizados

- Se creó `investmentops/core/research_result.py`, que define la última pieza pendiente del "Modelo de datos interno" descrito en ARCHITECTURE.md:
  - `ResearchResult` (dataclass inmutable): agregación de todos los resultados de análisis de una empresa en un momento dado. Contiene `company` (la `Company` investigada), `analysis_results` (colección de `AnalysisResult` de los agentes que se ejecutaron con éxito), `failures` (fallos parciales explícitos) y `generated_at` (cuándo se ensambló).
  - `ResearchFailure` (dataclass inmutable): registro explícito de un fallo parcial (`stage`, `identifier`, `reason`), pensado para que el orquestador capture ahí cualquier `DataProviderError` o `AnalysisEngineError` sin detener el resto del flujo, cumpliendo el requisito de ARCHITECTURE.md ("Manejo de errores y limitaciones") de que el resultado final refleje explícitamente qué no se pudo obtener, en vez de omitirlo en silencio.
  - Un `ResearchResult` puede tener `analysis_results` no vacío con `failures` vacío (investigación exitosa completa), ambos no vacíos (éxito parcial), o `analysis_results` vacío con solo `failures` (fallo total pero explícito) — el tipo no impone que todo salga bien para ser válido.
- Se actualizó `investmentops/core/__init__.py` (hasta ahora solo un docstring sin código) para re-exportar `ResearchResult` y `ResearchFailure`, siguiendo el mismo patrón ya usado en `ai_providers`, `analysis_engines` y `data_providers`: la estructura vive en un submódulo propio y se re-exporta en el `__init__.py` del paquete.
- Se agregó `investmentops/tests/test_core_research_result.py`, cubriendo: agregación de empresa + resultados de análisis, convivencia de resultados exitosos con fallos parciales, el caso límite de solo fallos (sin ningún análisis exitoso), e inmutabilidad de ambos tipos.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/core/research_result.py`
- `investmentops/tests/test_core_research_result.py`

Modificados:
- `investmentops/core/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, y el resto de `investmentops/` (`cli`, `data_providers`, `data_layer`, `analysis_engines`, `ai_providers`, `reports`, `config`), que no requirieron cambios para esta tarea.

No se implementó la lógica que efectivamente ensambla un `ResearchResult` invocando fuentes de datos y motores de análisis reales: eso corresponde a la sección "Orquestador mínimo" de `TASKS.md`, tarea posterior. Tampoco se implementó ningún generador de reportes que consuma este tipo (Fase 2).

## Decisiones técnicas importantes

- **`ResearchResult` vive en `investmentops.core`, no en `investmentops.data_layer`**: mismo criterio ya aplicado con `AnalysisResult` (ver PROGRESS.md, entrada anterior) — no es un dato que se obtenga de un proveedor externo y se normalice, sino la salida propia del orquestador (ARCHITECTURE.md, componente 2: "Ensamblar los resultados de todos los análisis en un modelo de 'resultado de investigación' único"). Vive junto al componente que lo produce, evitando una dependencia circular o artificial de `core` hacia un tipo que "debería" ser suyo pero estuviera definido en otra capa.
- **`ResearchFailure` como tipo explícito y separado de `ResearchResult`**, en vez de, por ejemplo, una lista de strings: ARCHITECTURE.md pide que el resultado final "refleje explícitamente qué información no pudo obtenerse" — un tipo estructurado (`stage`, `identifier`, `reason`) permite que un futuro generador de reportes distinga programáticamente entre un fallo de fuente de datos y uno de motor de análisis, y a qué proveedor/agente concreto corresponde, sin tener que parsear texto libre.
- **`stage: str` en vez de una enumeración cerrada** (ej. `Literal["data_provider", "analysis_engine"]`): se mantiene texto libre por el mismo criterio ya usado en `ProviderMetadata.reliability` — no acoplar esta estructura genérica a los dos únicos tipos de fallo que existen hoy, dejando espacio para que fases futuras (ej. Fase 4 con fuente de noticias, Fase 5 con comparables) reutilicen el mismo tipo sin modificarlo.
- **`analysis_results` y `failures` no son mutuamente excluyentes ni uno implica el otro**: se probó explícitamente (`test_research_result_can_hold_partial_failures_alongside_successful_results`, `test_research_result_supports_empty_analysis_results_with_failures_only`) que el tipo admite éxito parcial y fallo total sin casos especiales, reflejando el principio de ARCHITECTURE.md de que un fallo en una fuente o agente no debe detener el resto del flujo.
- **`generated_at` a nivel de `ResearchResult`, distinto de `AnalysisProvenance.generated_at`**: cada `AnalysisResult` ya registra cuándo se generó su propia interpretación; `ResearchResult.generated_at` registra cuándo el orquestador ensambló el conjunto, que puede ser (levemente) posterior al de cada análisis individual. Mismo criterio de no confundir "fecha del dato" con "fecha de consulta/ensamblado" ya aplicado en `FinancialStatement.period_end` vs. `ProviderMetadata.queried_at`.

## Problemas encontrados

Ninguno. Se verificó manualmente que `ResearchResult` y `ResearchFailure`:
- Agregan correctamente una `Company` con varios `AnalysisResult`.
- Permiten que resultados exitosos convivan con fallos parciales sin excluirse mutuamente.
- Admiten el caso límite de una investigación sin ningún análisis exitoso (solo fallos), sin que el tipo lo rechace.
- Son inmutables (reasignar cualquier campo lanza `AttributeError`).

## Próxima tarea recomendada

Con esto queda completa la sección "Contratos e interfaces" de la Fase 1 en `TASKS.md`. La siguiente sección pendiente es "Fuente de datos fundamentales", cuya primera tarea es:

*"Elegir el proveedor de datos financieros fundamentales a usar para el MVP (decisión, no implementación)."*

Nota para la próxima conversación: esta es una tarea de **decisión**, no de código — probablemente conviene resolverla conversando con el usuario sobre qué proveedor prefiere (ej. Alpha Vantage, Financial Modeling Prep, yfinance u otro), en vez de asumir uno unilateralmente, dado que implica una API key real que el usuario deberá completar en su propio `config.local.toml`.
