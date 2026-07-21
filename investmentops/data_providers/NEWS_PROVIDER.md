# Fuente de datos de noticias — elección del proveedor (Fase 4)

Cubre la tarea "Elegir el proveedor de noticias a usar para el MVP"
(TASKS.md, Fase 4, "Fuente de datos de noticias").

Esta tarea es de **decisión**, no de implementación: fija qué proveedor
externo se usará para obtener noticias/eventos recientes de una empresa,
antes de implementar el cliente concreto (tarea siguiente de esta misma
sección, "Implementar el contrato de 'data provider' para noticias...").
Sigue el mismo criterio ya aplicado en la Fase 1 para datos fundamentales
(ver "Elegir el proveedor de datos financieros fundamentales a usar para
el MVP", TASKS.md, decisión: FMP) y en la Fase 3 para series históricas
(ver `investmentops/data_providers/HISTORICAL_DATA.md`).

## Opciones consideradas

- **Financial Modeling Prep (FMP), endpoint `/v3/stock_news`** — el
  proveedor ya integrado en el proyecto desde la Fase 1
  (`investmentops/data_providers/fundamentals.py`), que además de datos
  fundamentales expone un endpoint de noticias por ticker.
- **NewsAPI.org** — proveedor genérico de noticias (no especializado en
  mercados financieros), requeriría una API key y credenciales nuevas.
- **Finnhub (`/company-news`)** — proveedor financiero con endpoint de
  noticias por empresa, requeriría una integración y API key nuevas.
- **Alpha Vantage (`NEWS_SENTIMENT`)** — incluye análisis de sentimiento
  ya calculado por el proveedor, lo que iría contra el principio de
  `ARCHITECTURE.md` de que la interpretación es responsabilidad de los
  agentes de análisis del propio sistema (vía IA o cálculo
  determinístico), no de un tercero externo.
- **Marketaux** — proveedor de noticias financieras con filtrado por
  ticker, tampoco integrado hoy en el proyecto.

## Decisión: Financial Modeling Prep (FMP), endpoint `/v3/stock_news`

Se elige reutilizar **FMP**, el mismo proveedor ya elegido y validado en
la Fase 1 para datos fundamentales, en vez de sumar un proveedor externo
nuevo. Motivos:

- **Ya integrado y ya pagado/autorizado.** El proyecto ya tiene un
  cliente HTTP funcional para FMP (`FMPFundamentalsProvider`, ver
  `investmentops/data_providers/fundamentals.py`) y ya gestiona su propia
  API key vía `config.local.toml` (`[data_providers.fundamentals]`, ver
  CONFIGURATION.md). Sumar un proveedor de noticias distinto implicaría
  gestionar una credencial adicional sin necesidad concreta.
- **Cubre lo que pide el modelo de dominio "Noticias"** (ver
  `ARCHITECTURE.md`, "Modelo de datos interno (conceptual)": *"Noticias
  — eventos con fecha, fuente y resumen"*): el endpoint
  `/v3/stock_news` de FMP devuelve, por cada noticia, `symbol`,
  `publishedDate`, `title`, `text` (resumen/cuerpo), `site` (fuente) y
  `url`, suficiente para construir ese modelo sin datos inventados.
- **No suma ninguna dependencia nueva.** El mismo cliente `requests` ya
  usado por `FMPFundamentalsProvider` sirve para este endpoint adicional,
  mismo criterio de "no sobre-diseñar antes de tener el caso de uso real"
  ya aplicado en el resto del proyecto (ver
  `investmentops/data_layer/market_data.py`,
  `investmentops/data_layer/CACHE.md`).
- **Sin análisis de sentimiento de terceros.** A diferencia de Alpha
  Vantage, FMP entrega noticias crudas (texto, fecha, fuente) sin una
  interpretación ya calculada por el proveedor externo, dejando la
  interpretación/filtrado a los motores de análisis del propio sistema
  (ver ARCHITECTURE.md, componente 5, "Motores de análisis").

## Configuración (para la tarea de implementación siguiente)

El cliente concreto (tarea siguiente, "Implementar el contrato de 'data
provider' para noticias...") deberá leer sus credenciales desde una
sección **nueva y separada**, `[data_providers.news]`, en
`config.local.toml`/`config.example.toml` — no desde
`[data_providers.fundamentals]`, aunque en la práctica ambas apunten hoy
al mismo proveedor externo (FMP). Esto es consistente con
`CONFIGURATION.md` ("Una sección por proveedor... El nombre de la
subsección es el identificador que el proveedor usa en código") y evita
acoplar accidentalmente ambas fuentes: si en el futuro se cambia el
proveedor de noticias (o el de fundamentales) sin tocar el otro, no hay
que desenredar una sección compartida.

## Fuera de alcance de esta tarea

- La implementación del cliente concreto que consulte
  `/v3/stock_news` (tarea siguiente, "Implementar el contrato de 'data
  provider' para noticias (ticker/nombre de empresa in, lista de eventos
  crudos out)").
- Adjuntar metadatos de procedencia a cada noticia cruda (tarea separada
  y posterior en la misma sección).
- El manejo de error del cliente (tarea separada y posterior).
- La transformación a un modelo de dominio "Noticias" normalizado (ver
  TASKS.md, Fase 4, "Normalización").
- Actualizar `config.example.toml`/`CONFIGURATION.md` con la nueva
  sección `[data_providers.news]`: se hará como parte de la tarea de
  implementación del cliente concreto, no de esta decisión.