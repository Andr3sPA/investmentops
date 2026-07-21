# investmentops/data_providers/COMPARABLES_PROVIDER.md
# Fuente de datos de comparables — elección del proveedor/método (Fase 5)

Cubre la tarea "Elegir el proveedor o método para obtener empresas
pares/sector de una empresa dada" (TASKS.md, Fase 5, "Fuente de datos de
comparables").

Esta tarea es de **decisión**, no de implementación: fija qué proveedor
externo (o método) se usará para obtener la lista de empresas pares de
una empresa dada, antes de implementar el cliente concreto (tarea
siguiente de esta misma sección, "Implementar la consulta de comparables
(lista de empresas pares) para un ticker"). Sigue el mismo criterio ya
aplicado en la Fase 1 para datos fundamentales (ver TASKS.md, decisión:
FMP), en la Fase 3 para series históricas
(`investmentops/data_providers/HISTORICAL_DATA.md`) y en la Fase 4 para
noticias (`investmentops/data_providers/NEWS_PROVIDER.md`).

## Opciones consideradas

- **Financial Modeling Prep (FMP), endpoint `/v4/stock_peers`** — el
  proveedor ya integrado desde la Fase 1
  (`investmentops/data_providers/fundamentals.py`), que además expone un
  endpoint dedicado a devolver, para un ticker dado, una lista de
  empresas "pares" (mismo sector/industria, tamaño de mercado similar),
  ya calculada por el propio FMP.
- **Construir la lista de pares nosotros mismos** (ej. consultar el
  sector de la empresa vía `/v3/profile/{ticker}` y luego filtrar un
  universo de tickers por ese mismo sector) — requeriría un endpoint
  adicional de "screener" o mantener un universo propio de tickers por
  sector, más lógica de filtrado que no aporta nada sobre lo que FMP ya
  resuelve directamente.
- **Un proveedor externo nuevo especializado en comparables** (ej.
  herramientas de "peer analysis" de otros proveedores financieros) —
  implicaría gestionar una credencial adicional sin necesidad concreta,
  mismo motivo por el que se descartaron alternativas a FMP en
  `NEWS_PROVIDER.md`.

## Decisión: Financial Modeling Prep (FMP), endpoint `/v4/stock_peers`

Se elige reutilizar **FMP**, el mismo proveedor ya elegido y validado en
las Fases 1, 3 y 4, en vez de sumar un proveedor externo nuevo o
construir lógica de filtrado propia. Motivos:

- **Ya integrado y ya pagado/autorizado.** El proyecto ya gestiona su
  propia API key de FMP vía `config.local.toml`
  (`[data_providers.fundamentals]`, ver CONFIGURATION.md). Sumar un
  cliente nuevo para comparables reutiliza la misma infraestructura ya
  usada por `FMPFundamentalsProvider`/`FMPNewsProvider`.
- **Resuelve directamente lo que pide `ARCHITECTURE.md`.** El endpoint
  `/v4/stock_peers` devuelve, para un ticker, una lista de tickers pares
  ya calculada por FMP (mismo sector/industria y tamaño de mercado
  comparable), sin que este proyecto tenga que definir ni mantener su
  propio criterio de "qué hace a dos empresas comparables" — evita
  inventar una heurística de selección de pares sin base, mismo
  principio ya aplicado en otros módulos del proyecto (declarar/usar lo
  que el dato disponible permite, no aproximar lo que no está).
- **Las métricas de cada par ya son las que el sistema ya sabe obtener y
  normalizar.** Una vez obtenida la lista de tickers pares, sus métricas
  clave (ingresos, beneficio neto, deuda, precio, capitalización) se
  consultan y normalizan con los mismos clientes y transformaciones ya
  existentes (`FMPFundamentalsProvider.fetch`,
  `financial_statement_from_raw`, `market_data_from_raw`, Fase 1): no se
  necesita ningún endpoint ni transformación nueva para las cifras en sí,
  solo para obtener la lista de pares.
- **Sin dependencias nuevas**, mismo criterio de "no sobre-diseñar antes
  de tener el caso de uso real" ya aplicado en el resto del proyecto (ver
  `investmentops/data_layer/market_data.py`,
  `investmentops/data_layer/CACHE.md`).

## Configuración (para la tarea de implementación siguiente)

El cliente concreto (tarea siguiente, "Implementar la consulta de
comparables (lista de empresas pares) para un ticker") deberá leer sus
credenciales desde una sección **nueva y separada**,
`[data_providers.comparables]`, en `config.local.toml`/
`config.example.toml` — mismo criterio ya aplicado en
`NEWS_PROVIDER.md`: no reutilizar `[data_providers.fundamentals]` aunque
ambas apunten hoy al mismo proveedor externo (FMP), para no acoplar
accidentalmente ambas fuentes si en el futuro cambia una sin la otra.

## Alcance de "empresas pares" para el MVP de esta fase

- La lista de pares que devuelve `/v4/stock_peers` no se filtra ni se
  reordena por este proyecto: se usa tal cual la entrega FMP, mismo
  criterio ya aplicado a las noticias (`NEWS_RELEVANCE.md`, "sin
  filtrado temático... el sistema no inventa una señal que no existe").
- No se define aquí un límite máximo de pares a comparar: esa decisión
  (si aplica) corresponde a la tarea de implementación del cliente
  concreto o del motor de análisis de posicionamiento relativo,
  siguiendo el mismo criterio de no sobre-diseñar antes de tener el caso
  de uso real.

## Fuera de alcance de esta tarea

- La implementación del cliente concreto que consulte `/v4/stock_peers`
  (tarea siguiente, "Implementar la consulta de comparables (lista de
  empresas pares) para un ticker").
- La consulta de métricas clave para cada empresa par (tarea separada y
  posterior de la misma sección: "Implementar la consulta de métricas
  clave... para cada empresa par") — reutilizará, sin duplicar, los
  clientes y transformaciones ya existentes de la Fase 1.
- Adjuntar metadatos de procedencia a los datos de comparables (tarea
  separada y posterior en la misma sección).
- El modelo de dominio "Comparables" y su transformación (ver TASKS.md,
  Fase 5, "Normalización").
- Actualizar `config.example.toml`/`CONFIGURATION.md` con la nueva
  sección `[data_providers.comparables]`: se hará como parte de la tarea
  de implementación del cliente concreto, no de esta decisión.