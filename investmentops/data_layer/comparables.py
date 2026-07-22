"""Modelo de dominio "Comparables" (Comparables / PeerComparable).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Comparables
— conjunto de empresas pares y sus métricas equivalentes."*, y TASKS.md,
Fase 5, sección "Normalización": *"Definir el modelo de dominio
'Comparables' (conjunto de empresas pares y sus métricas equivalentes)."*

Este módulo define únicamente la **estructura** del modelo de dominio
"Comparables": la representación común de un conjunto de empresas pares
de una empresa investigada, junto con las cifras normalizadas de cada
una, que usará el futuro motor de análisis de posicionamiento relativo
(ver ROADMAP.md, Fase 5, y TASKS.md, "Motor de análisis: posicionamiento
relativo") y los generadores de reportes, sin importar de qué proveedor
provino originalmente cada dato (ver ARCHITECTURE.md, componente 4,
"Normalización y almacenamiento").

## Decisión de diseño: reutilizar `FinancialStatement`/`MarketData` por par

Igual que `FinancialStatementSeries` (Fase 3) reutiliza `FinancialStatement`
tal cual como tipo de cada punto de la serie, en vez de introducir un tipo
nuevo casi idéntico, este módulo reutiliza `FinancialStatement` y
`MarketData` (ambos ya normalizados desde la Fase 1) como las cifras de
cada empresa par: son exactamente los datos que ya sabe obtener y
normalizar el sistema para cualquier empresa (ver
`investmentops.core.orchestrator.fetch_and_normalize`, ya reutilizada sin
cambios por `fetch_peer_key_metrics` para cada ticker par, tarea "Fuente
de datos de comparables" de esta misma fase, ya completada). No se
inventa ningún campo nuevo ni una estructura de "métricas equivalentes"
distinta de la que el sistema ya normaliza para la propia empresa
investigada.

`PeerComparable` es el tipo intermedio que agrupa, para una empresa par
concreta, su `ticker` junto con esas dos cifras normalizadas.
`Comparables` es el contenedor simple que agrupa, para la empresa
investigada, su `ticker` y la secuencia de `PeerComparable` de sus pares
(en el mismo orden en que el proveedor de comparables los entregó, sin
reordenar ni filtrar — mismo criterio ya documentado en
`investmentops/data_providers/COMPARABLES_PROVIDER.md`, "la lista de
pares... se usa tal cual la entrega FMP").

## Relación con `investmentops.core.orchestrator.PeerMetrics`

`investmentops.core.orchestrator.PeerMetrics` (ya implementado en la
tarea "Implementar la consulta de métricas clave... para cada empresa
par" de esta misma fase, ver TASKS.md y PROGRESS.md) tiene exactamente la
misma forma que `PeerComparable` (`ticker`, `financial_statement`,
`market_data`): no es una coincidencia, sino la razón por la que este
modelo de dominio no introduce ningún campo nuevo. La diferencia es de
**capa**, no de contenido:

- `PeerMetrics` vive en `investmentops.core.orchestrator` como resultado
  de la composición *on-the-fly* que hace `fetch_peer_key_metrics`
  (consulta comparables → por cada par, reutiliza `fetch_and_normalize`),
  sin pasar por una capa de normalización dedicada — es, en espíritu, más
  parecido a `NormalizedCompanyData` (también en el orquestador) que a un
  modelo de dominio de `data_layer`.
- `Comparables`/`PeerComparable`, definidos aquí, son el modelo de
  dominio formal en `investmentops.data_layer`, pensado como el tipo de
  salida de una futura función de transformación
  (`comparables_from_...`, tarea siguiente: "Implementar la
  transformación de los datos crudos de comparables al modelo
  normalizado") y como el tipo que se cacheará (tarea "Implementar el
  guardado de comparables normalizados en la caché local...").

Esta tarea **no modifica** `investmentops/core/orchestrator.py` ni
`PeerMetrics`: decidir si `fetch_peer_key_metrics` pasa a construir y
devolver este nuevo modelo de dominio (en vez de, o además de,
`PeerMetrics`) es una decisión de implementación que corresponde a la
tarea siguiente, no a esta tarea de definición de estructura.

## Qué se deja fuera deliberadamente

- **Procedencia por empresa par** (`source`/`queried_at` del proveedor de
  comparables, ya adjuntados por punto en el payload crudo por
  `_attach_comparables_provenance`, ver
  `investmentops/data_providers/comparables.py`): no se propaga a este
  modelo de dominio. `FinancialStatement.source`/`MarketData.source` ya
  identifican, por su cuenta, la fuente de las cifras de cada par (mismo
  criterio ya aplicado por `FinancialStatementSeries`, que tampoco
  propaga `queried_at` por punto al modelo de dominio: es metadato de la
  *consulta*, no del *dato* en sí).
- **Cálculo de posicionamiento relativo** (en qué métricas la empresa
  investigada está por encima/debajo de sus pares): responsabilidad del
  futuro motor de análisis de posicionamiento relativo (ver TASKS.md,
  "Motor de análisis: posicionamiento relativo"), no de este modelo de
  dominio, que solo representa el dato ya normalizado.
- **Validación de que los tickers pares sean válidos o coherentes**: este
  módulo solo define la forma del dato, mismo criterio ya aplicado por
  `Company`/`FinancialStatement`/`MarketData`/`News`.

Fuera de alcance de este módulo:
- La transformación de los datos crudos de
  `investmentops.data_providers.comparables.FMPComparablesProvider.fetch`
  a este modelo: tarea separada y siguiente (ver TASKS.md, Fase 5,
  "Normalización" > "Implementar la transformación de los datos crudos de
  comparables al modelo normalizado").
- El cacheo/persistencia de `Comparables` normalizados: tarea separada y
  posterior de la misma sección.
- El motor de análisis que consume este modelo (comparación métrica a
  métrica): tarea separada de la sección "Motor de análisis:
  posicionamiento relativo".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData


@dataclass(frozen=True)
class PeerComparable:
    """Cifras normalizadas de una empresa par (comparable) individual.

    Es el tipo de cada elemento de `Comparables.peers`: agrupa, para una
    empresa par concreta, su identidad básica (`ticker`) junto con sus
    cifras ya normalizadas (`FinancialStatement`, `MarketData`), las
    mismas que el sistema ya sabe obtener y normalizar para cualquier
    empresa desde la Fase 1 (ver
    `investmentops.core.orchestrator.fetch_and_normalize`).

    Attributes
    ----------
    ticker:
        Identificador bursátil de la empresa par (ej. ``"MSFT"``), tal
        como lo entrega el proveedor de comparables (ver
        `investmentops.data_providers.comparables.FMPComparablesProvider`).
    financial_statement:
        Estados financieros normalizados de la empresa par (ver
        `investmentops.data_layer.FinancialStatement`).
    market_data:
        Datos de mercado normalizados de la misma empresa par (ver
        `investmentops.data_layer.MarketData`).
    """

    ticker: str
    financial_statement: FinancialStatement
    market_data: MarketData


@dataclass(frozen=True)
class Comparables:
    """Conjunto de empresas pares (comparables) y sus métricas equivalentes.

    Es el tipo que usará el futuro motor de análisis de posicionamiento
    relativo (ver ROADMAP.md, Fase 5) como parte del modelo de dominio
    normalizado de una empresa, y que los generadores de reportes citarán
    para mostrar frente a qué pares se comparó la empresa investigada
    (ver ARCHITECTURE.md, "Reproducibilidad y trazabilidad").

    Attributes
    ----------
    ticker:
        Identificador de la empresa investigada, para la que se
        obtuvieron los pares (ej. ``"AAPL"``), mismo criterio de
        identidad ya usado por `Company`
        (`investmentops.data_layer.domain`) y por
        `FinancialStatementSeries`.
    peers:
        Secuencia de `PeerComparable`, una por cada empresa par, en el
        mismo orden en que el proveedor de comparables las entregó (ver
        `investmentops/data_providers/COMPARABLES_PROVIDER.md`: la lista
        no se reordena ni se filtra). Puede estar vacía si la empresa
        investigada no tiene pares según el proveedor (caso válido, no un
        error, ver `FMPComparablesProvider.fetch`).
    """

    ticker: str
    peers: Sequence[PeerComparable]