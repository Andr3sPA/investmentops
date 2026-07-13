# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Contratos e interfaces → *"Definir la estructura del modelo de dominio 'Estados financieros normalizados' (ingresos, beneficios, deuda, con fuente y fecha)."*

## Cambios realizados

- Se creó `investmentops/data_layer/financial_statements.py`, que define el segundo modelo de dominio interno común descrito en ARCHITECTURE.md ("Modelo de datos interno"):
  - `FinancialStatement`: dataclass inmutable (`frozen=True`) con las cifras financieras básicas de una empresa en **un único corte** (el más reciente disponible): `revenue` (ingresos), `net_income` (beneficio/utilidad neta), `debt` (deuda total), más `source` (proveedor del que provienen las cifras) y `period_end` (fecha de corte a la que corresponden, distinta de la fecha en que se consultó el dato).
  - El alcance de esta tarea se limita deliberadamente a un solo periodo por empresa: `ARCHITECTURE.md` describe este modelo a futuro como "series históricas", pero extenderlo a varios periodos es una tarea explícita y posterior de la Fase 3 (ROADMAP.md / TASKS.md, "Normalización" > "Extender el modelo... para incluir series temporales"), que depende de una fuente de datos histórica y un motor de análisis de evolución que todavía no existen.
- Se actualizó `investmentops/data_layer/__init__.py` para re-exportar también `FinancialStatement` (junto a `Company`, ya existente), de forma que el resto del sistema lo importe directamente desde `investmentops.data_layer`.
- Se agregó `investmentops/tests/test_data_layer_financial_statements.py`, cubriendo: que `FinancialStatement` conserva correctamente sus cinco campos (incluyendo `source` y `period_end`), que es inmutable, y que admite beneficio neto negativo (empresa con pérdidas) sin necesidad de casos especiales.
- Se marcó la tarea como completada en `TASKS.md`.

## Archivos creados o modificados

Creados:
- `investmentops/data_layer/financial_statements.py`
- `investmentops/tests/test_data_layer_financial_statements.py`

Modificados:
- `investmentops/data_layer/__init__.py`
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, `investmentops/config/__init__.py`, `investmentops/__main__.py`, `investmentops/__init__.py`, `investmentops/data_layer/domain.py`, `investmentops/data_providers/__init__.py`, `investmentops/data_providers/contracts.py`, `investmentops/analysis_engines/__init__.py`, `investmentops/analysis_engines/contracts.py`, `investmentops/ai_providers/__init__.py`, `investmentops/ai_providers/contracts.py`, `investmentops/tests/test_environment.py`, `investmentops/tests/test_config.py`, `investmentops/tests/test_data_providers_contracts.py`, `investmentops/tests/test_analysis_engines_contracts.py`, `investmentops/tests/test_ai_providers_contracts.py`, `investmentops/tests/test_data_layer_domain.py`, y los demás subpaquetes de `investmentops/` (`cli`, `core`, `reports`), que siguen sin implementación.

No se implementó ninguna transformación desde datos crudos de proveedor (`RawProviderData`) hacia `FinancialStatement`: eso corresponde a la sección "Normalización y almacenamiento" de `TASKS.md`, tarea posterior. Tampoco se agregó el modelo "Datos de mercado" ni el soporte de series históricas: cada uno tiene su propia tarea pendiente.

## Decisiones técnicas importantes

- **Un solo corte por empresa, no una serie temporal**: `TASKS.md` en esta tarea de Fase 1 pide explícitamente "ingresos, beneficios, deuda, con fuente y fecha" (singular), y `ROADMAP.md`/`TASKS.md` reservan para la Fase 3 la extensión explícita a series históricas ("no solo el dato más reciente"). Definir ya una estructura de serie de tiempo adelantaría una decisión de diseño (¿lista de cortes? ¿un dato por año/trimestre?) sin que exista todavía la fuente de datos histórica que la alimentaría, violando el principio de no sobre-diseñar antes de tener el caso de uso real.
- **`period_end: date` (no `datetime`)**: un estado financiero corresponde a un periodo fiscal (ej. cierre de año o trimestre), no a un instante preciso; se usa `datetime.date` en vez de `datetime.datetime` para reflejar eso con precisión, a diferencia de `ProviderMetadata.queried_at` (que sí es un instante de consulta y por eso usa `datetime`).
- **`source: str` como campo simple** (no un objeto `ProviderMetadata` anidado): a diferencia de `RawProviderData` (que sí anida un objeto `ProviderMetadata` completo con `queried_at` y `reliability`), aquí basta con `source` porque `period_end` ya cumple el rol de "fecha del dato" que pedía la tarea; anidar el mismo objeto de metadatos de proveedor habría duplicado la noción de fecha (la de consulta vs. la de corte) sin necesidad en esta etapa. Si más adelante se necesita `reliability` o `queried_at` explícitos en este modelo, se puede extender sin romper el contrato actual.
- **`revenue`, `net_income`, `debt` como `float` obligatorios, sin `Optional`**: mismo criterio que en `Company` — se mantienen simples y requeridos en esta tarea de definición de estructura. Cómo representar un dato faltante de un proveedor concreto (cadena vacía, `None`, valor por defecto) se decide en la tarea de "Normalización y almacenamiento", cuando exista la transformación real desde datos crudos.
- **`net_income` admite valores negativos sin validación**: una empresa con pérdidas es un caso normal, no un error; el modelo no impone que las cifras sean positivas, coherente con el principio de "el sistema informa, no decide" — no le corresponde a esta estructura juzgar si una cifra es "buena" o "mala", solo representarla fielmente.
- **`FinancialStatement` en un módulo propio (`financial_statements.py`)**, no en `domain.py` junto a `Company`: se sigue el mismo criterio ya documentado en la tarea anterior (un módulo por modelo de dominio cuando su complejidad lo justifica), dejando `domain.py` disponible para identidad básica y facilitando que la extensión a series históricas de la Fase 3 se haga en este mismo archivo sin tocar `Company`.

## Problemas encontrados

Ninguno. Se verificó manualmente que:
- `FinancialStatement` conserva correctamente sus cinco campos al construirse.
- `FinancialStatement` es inmutable (intentar reasignar `revenue` lanza `AttributeError`).
- El modelo admite un `net_income` negativo (empresa con pérdidas) sin necesidad de casos especiales en el código.

## Próxima tarea recomendada

Fase 1 → Contratos e interfaces → *"Definir la estructura del modelo de dominio 'Datos de mercado' (precio, capitalización, múltiplos, fecha de corte)."*
