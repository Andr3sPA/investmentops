# PROGRESS.md

**Última actualización:** 2026-07-21

## Última tarea completada

Fase 5, "Fuente de datos de comparables" → "Elegir el proveedor o método
para obtener empresas pares/sector de una empresa dada" (TASKS.md).

### Qué se implementó

`investmentops/data_providers/COMPARABLES_PROVIDER.md` (nuevo). Decisión:
reutilizar **Financial Modeling Prep (FMP)**, el mismo proveedor ya
integrado desde la Fase 1 (`FMPFundamentalsProvider`) y reutilizado en
Fase 4 para noticias (`FMPNewsProvider`), esta vez vía su endpoint
`/v4/stock_peers`, que devuelve para un ticker dado una lista de empresas
"pares" (mismo sector/industria, tamaño de mercado comparable) ya
calculada por el propio FMP — evita que este proyecto tenga que definir
o mantener su propio criterio de comparabilidad.

Las métricas clave de cada empresa par (ingresos, beneficio neto, deuda,
precio, capitalización) se obtendrán reutilizando, sin duplicar, los
clientes y transformaciones ya existentes de la Fase 1
(`FMPFundamentalsProvider.fetch`, `financial_statement_from_raw`,
`market_data_from_raw`): la única pieza nueva que aporta esta decisión es
cómo obtener la *lista* de tickers pares.

Se decide usar una sección de configuración nueva y separada,
`[data_providers.comparables]`, siguiendo el mismo criterio ya aplicado
en `NEWS_PROVIDER.md` para no acoplar accidentalmente distintas fuentes
de datos que hoy comparten el mismo proveedor externo.

Es una tarea de decisión/documentación, no de código: no se modificó
ningún archivo `.py` existente ni se creó ningún cliente concreto.

## Archivos creados o modificados

Creados:
- `investmentops/data_providers/COMPARABLES_PROVIDER.md`

Modificados:
- `TASKS.md` (una línea: tarea marcada como completada, con referencia a
  la decisión)
- `PROGRESS.md` (este archivo)

## Próxima tarea recomendada

Fase 5, "Fuente de datos de comparables":
- "Implementar la consulta de comparables (lista de empresas pares) para
  un ticker." Implica crear `investmentops/data_providers/comparables.py`
  con un cliente mínimo (similar a `FMPNewsProvider`) que consulte
  `/v4/stock_peers` para un ticker y devuelva un `RawProviderData` con la
  lista cruda de tickers pares, leyendo su API key desde
  `[data_providers.comparables]` en `config.local.toml`.