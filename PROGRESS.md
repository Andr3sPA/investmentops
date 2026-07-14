# InvestmentOps — Progreso

**Última actualización:** 2026-07-13

## Última tarea completada

Fase 1 → Fuente de datos fundamentales → *"Elegir el proveedor de datos financieros fundamentales a usar para el MVP (decisión, no implementación)."*

## Decisión tomada

**Proveedor elegido: Financial Modeling Prep (FMP).**

Esta es una tarea de decisión, no de código: no se creó ni modificó ningún archivo Python. El resultado es la elección documentada aquí y en `TASKS.md`, que guiará la siguiente tarea ("Implementar un cliente mínimo que consulte ese proveedor...").

## Investigación realizada

Se compararon tres candidatos con información vigente a julio de 2026:

- **Alpha Vantage**: vendor oficial de NASDAQ, con buena cobertura de fundamentales (`INCOME_STATEMENT`, `BALANCE_SHEET`) y múltiplos (`OVERVIEW`). Su nivel gratuito actual es de solo 25 solicitudes/día (5 por minuto), insuficiente incluso para una investigación completa de una sola empresa (estados financieros + datos de mercado) sin quedarse corto.
- **Financial Modeling Prep (FMP)**: proveedor oficial, con datos de fundamentales derivados de SEC EDGAR (la misma fuente regulatoria que usan las empresas públicas). Su nivel gratuito (plan Basic) permite 250 llamadas/día, con datos de cierre de día y ~5 años de historial. Buena cobertura tanto de estados financieros como de múltiplos y datos de mercado.
- **yfinance**: librería no oficial (envuelve/scrapea Yahoo Finance), sin necesidad de API key ni cuota diaria formal. Atractiva para un proyecto de un solo usuario y bajo volumen, pero con riesgo real de romperse sin aviso ante cambios de Yahoo Finance, al no ser un servicio oficial ni contractual.

## Justificación de la decisión

- El usuario confirmó que el uso será de aproximadamente **una consulta al día**, lo que hace irrelevante el límite diario como criterio decisivo (los 250 req/día de FMP son ampliamente suficientes; incluso los de Alpha Vantage alcanzarían, aunque con menos margen).
- Con el criterio de calidad y confiabilidad como factor principal, **FMP** es preferible a **yfinance** por ser un proveedor oficial y contractual: no depende de scraping no documentado ni corre riesgo de romperse sin aviso ante un cambio de Yahoo Finance, lo cual es importante para una herramienta que el usuario planea usar de forma recurrente (ver ROADMAP.md, Fases 8-9, watchlist y automatización diaria).
- Frente a **Alpha Vantage**, FMP ofrece datos de fundamentales con mejor trazabilidad (provienen de SEC EDGAR) y una cobertura de múltiplos/datos de mercado más completa, relevante para `investmentops.data_layer.MarketData` (P/E, P/B, capitalización, precio) además de `FinancialStatement` (ingresos, beneficios, deuda).
- Esta elección es reversible sin impacto en el resto del sistema: conforme a `ARCHITECTURE.md` ("Extensibilidad"), el contrato `DataProvider` (`investmentops.data_providers.contracts`) ya aísla al orquestador de los detalles de FMP; si en el futuro se quisiera cambiar de proveedor (o sumar otro, ej. para datos del mercado colombiano vía Tyba/Trii), bastaría con implementar un nuevo adaptador que cumpla el mismo contrato, sin modificar el resto del sistema.

## Archivos creados o modificados

Creados: ninguno.

Modificados:
- `TASKS.md` (tarea marcada como completada, con la decisión documentada inline)
- `PROGRESS.md` (este archivo)

No modificados: `GOALS.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONFIGURATION.md`, `config.example.toml`, `prompts/README.md`, `.gitignore`, `pyproject.toml`, `.python-version`, y todo `investmentops/` (código y tests): esta tarea no requería cambios de código.

## Problemas encontrados

Ninguno.

## Próxima tarea recomendada

Fase 1 → Fuente de datos fundamentales → *"Implementar un cliente mínimo que consulte ese proveedor y obtenga datos crudos de una empresa por ticker."*

Nota para la próxima conversación: esta tarea sí requiere código. Deberá:
- Implementar un módulo bajo `investmentops/data_providers/` (ej. `fundamentals.py` o similar) que cumpla el contrato `DataProvider` ya definido (`investmentops.data_providers.contracts.DataProvider`: método `fetch(ticker) -> RawProviderData`).
- Leer la API key de FMP desde `config.local.toml`, sección `[data_providers.fundamentals]` (ya prevista en `config.example.toml` y documentada en `CONFIGURATION.md`), usando `investmentops.config.load_config`.
- Devolver los datos crudos de FMP tal cual (sin transformar al modelo de dominio `FinancialStatement`/`MarketData` — esa transformación es una tarea posterior, "Normalización y almacenamiento").
- Probablemente requiera una dependencia HTTP (ej. `requests` o `httpx`), que hoy no está en `pyproject.toml` (`dependencies = []`); habrá que decidir cuál añadir y actualizar `pyproject.toml`.
- Como esta tarea hará una llamada HTTP real a la API de FMP, las pruebas automatizadas deberán simular (mockear) la respuesta en vez de depender de una llamada de red real y de una API key válida en el entorno de test.
