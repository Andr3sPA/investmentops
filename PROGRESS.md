# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Fuente de datos de comparables" → "Implementar la consulta de
comparables (lista de empresas pares) para un ticker" (TASKS.md).

### Qué se implementó

`FMPComparablesProvider` en `investmentops/data_providers/comparables.py`
(nuevo). Cumple el contrato `DataProvider`
(investmentops.data_providers.contracts): `fetch(ticker)` consulta el
endpoint `/stock_peers` de la API **v4** de FMP (distinta de la v3 usada
por `FMPFundamentalsProvider`/`FMPNewsProvider`) y devuelve un
`RawProviderData` cuyo `payload` es la respuesta cruda tal como la
entrega FMP (típicamente una lista con un único elemento que incluye
`"peersList"`), sin transformarla ni extraer los tickers pares — esa
interpretación es responsabilidad de la capa de normalización, tarea
separada y posterior de esta misma sección.

Sigue exactamente el mismo patrón ya usado por `FMPNewsProvider`
(`investmentops/data_providers/news.py`): lee sus credenciales desde una
sección nueva y separada, `[data_providers.comparables]` (no desde
`[data_providers.fundamentals]`, aunque ambas apunten hoy al mismo
proveedor externo), y traduce cualquier fallo (red, autenticación,
errores de servidor, JSON inválido) a `DataProviderError`. Una lista
vacía (FMP no encontró empresas pares para el ticker) se trata como una
respuesta válida, no como un error.

Se actualizaron `config.example.toml` y `CONFIGURATION.md` con la nueva
sección `[data_providers.comparables]`, siguiendo el mismo criterio ya
aplicado para `[data_providers.news]` en la Fase 4.

Quedan explícitamente fuera de esta tarea (ver TASKS.md, tareas
siguientes de la misma sección): adjuntar procedencia por empresa par
individual, y consultar las métricas clave de cada par reutilizando
`FMPFundamentalsProvider.fetch`/`financial_statement_from_raw`/
`market_data_from_raw`.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/comparables.py`
- `investmentops/tests/test_data_providers_comparables.py`

Modificados:
- `config.example.toml` (nueva sección `[data_providers.comparables]`)
- `CONFIGURATION.md` (mención de la nueva sección)
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la implementación)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Fuente de datos de comparables":
- "Implementar la consulta de métricas clave (las ya normalizadas en
  fases previas) para cada empresa par." Implica, para cada ticker par
  devuelto por `FMPComparablesProvider.fetch`, reutilizar
  `FMPFundamentalsProvider.fetch` + `financial_statement_from_raw` +
  `market_data_from_raw` (ya existentes desde la Fase 1) para obtener sus
  cifras normalizadas, sin duplicar esos clientes ni transformaciones.