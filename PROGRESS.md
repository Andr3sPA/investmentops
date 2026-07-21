# InvestmentOps — Progreso

**Última actualización:** 2026-07-20

## Última tarea completada

Fase 4, "Fuente de datos de noticias" → "Elegir el proveedor de noticias
a usar para el MVP." (TASKS.md).

### Qué se implementó

Tarea de decisión/documentación, no de código (mismo tipo de tarea ya
resuelta en `HISTORICAL_DATA.md`, Fase 3, y en la elección de FMP como
proveedor fundamental en Fase 1).

Nuevo archivo `investmentops/data_providers/NEWS_PROVIDER.md`:

- Evalúa cinco opciones: FMP (`/v3/stock_news`), NewsAPI.org, Finnhub
  (`/company-news`), Alpha Vantage (`NEWS_SENTIMENT`) y Marketaux.
- **Decisión: reutilizar FMP**, el proveedor ya integrado desde la Fase
  1 (`FMPFundamentalsProvider`), vía su endpoint `/v3/stock_news`. Se
  descarta sumar un proveedor externo nuevo por: (1) ya está integrado y
  ya tiene credenciales gestionadas vía `config.local.toml`; (2) el
  endpoint ya devuelve los campos que exige el modelo "Noticias" de
  `ARCHITECTURE.md` (fecha, fuente, resumen) sin inventar datos; (3) no
  suma ninguna dependencia nueva (mismo cliente `requests` ya usado);
  (4) a diferencia de Alpha Vantage, no impone un análisis de sentimiento
  ya calculado por un tercero, dejando la interpretación a los propios
  motores de análisis del sistema.
- Deja documentado que la implementación siguiente deberá usar una
  sección de configuración **nueva y separada**,
  `[data_providers.news]`, sin acoplarla a
  `[data_providers.fundamentals]` aunque ambas apunten hoy al mismo
  proveedor externo.

No se tocó ningún código (`investmentops/data_providers/fundamentals.py`
no se modificó): esta tarea es puramente de decisión, la implementación
del cliente concreto es la tarea siguiente de la misma sección.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/NEWS_PROVIDER.md`

Modificados:
- `TASKS.md` (tarea marcada como completada)
- `PROGRESS.md` (este archivo)

No modificados: ningún archivo de código Python.

## Próxima tarea recomendada

Fase 4, "Fuente de datos de noticias" → "Implementar el contrato de
'data provider' para noticias (ticker/nombre de empresa in, lista de
eventos crudos out)", sobre la decisión ya tomada en
`investmentops/data_providers/NEWS_PROVIDER.md` (FMP, endpoint
`/v3/stock_news`).