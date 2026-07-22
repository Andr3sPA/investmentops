"""Normalización y almacenamiento (Data Layer).

Responsabilidad (ver ARCHITECTURE.md, componente 4):
- Convertir los datos crudos y heterogéneos de cada proveedor
  (investmentops.data_providers) a un modelo de dominio interno común
  (ej. una representación estándar de "estado de resultados", sin importar
  de qué proveedor vino).
- Cachear localmente los datos obtenidos, para evitar llamadas repetidas a
  APIs externas y permitir trabajar offline con datos ya descargados.
- Mantener un histórico simple de consultas (qué se consultó, cuándo, con
  qué resultado) para trazabilidad.
- El almacenamiento es local (archivos o una base embebida), coherente con
  el requisito de "un solo usuario, todo local".

Esta capa aísla al resto del sistema de los formatos particulares de cada
API externa.

Los modelos de dominio definidos hasta ahora ya están implementados en sus
propios módulos (ver TASKS.md, "Contratos e interfaces") y se re-exportan
aquí para que el resto del sistema los importe directamente desde
`investmentops.data_layer`:

- `Company` (en `investmentops.data_layer.domain`): identidad básica de
  una empresa (ticker, nombre, sector, mercado).
- `FinancialStatement` (en `investmentops.data_layer.financial_statements`):
  estados financieros normalizados de una empresa en un corte (ingresos,
  beneficios, deuda, con fuente y fecha).
- `FinancialStatementSeries` (en
  `investmentops.data_layer.financial_statement_series`): serie temporal
  de `FinancialStatement`, uno por periodo, ordenada del más reciente al
  más antiguo (ver TASKS.md, Fase 3, "Normalización" > "Extender el
  modelo 'Estados financieros normalizados' para incluir series
  temporales").
- `MarketData` (en `investmentops.data_layer.market_data`): datos de
  mercado normalizados de una empresa en un corte (precio, capitalización,
  múltiplos, con fuente y fecha de corte).
- `News` (en `investmentops.data_layer.news`): evento noticioso
  normalizado relacionado con una empresa (titular, resumen, fuente,
  fecha de publicación, enlace).
- `Comparables`/`PeerComparable` (en `investmentops.data_layer.comparables`):
  conjunto de empresas pares de una empresa investigada y sus cifras
  normalizadas equivalentes (`FinancialStatement`/`MarketData` por par),
  ver TASKS.md, Fase 5, "Normalización" > "Definir el modelo de dominio
  'Comparables'". Aún sin un consumidor real: la transformación desde la
  respuesta cruda de `FMPComparablesProvider.fetch` es una tarea separada
  y posterior de la misma sección.

Aún sin implementación (ver TASKS.md, sección "Normalización y
almacenamiento" de la Fase 1, "Normalización" de la Fase 3, "Normalización"
de la Fase 4, y "Normalización" de la Fase 5).
"""

from investmentops.data_layer.comparables import Comparables, PeerComparable
from investmentops.data_layer.domain import Company
from investmentops.data_layer.financial_statement_series import (
    FinancialStatementSeries,
)
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.news import News

__all__ = [
    "Comparables",
    "Company",
    "FinancialStatement",
    "FinancialStatementSeries",
    "MarketData",
    "News",
    "PeerComparable",
]