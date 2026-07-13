"""Modelo de dominio "Datos de mercado" (MarketData).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Datos de
mercado — precio, capitalización, múltiplos, con fecha de corte."*, y
TASKS.md, Fase 1, sección "Contratos e interfaces": *"Definir la
estructura del modelo de dominio 'Datos de mercado' (precio,
capitalización, múltiplos, fecha de corte)."*

Este módulo define únicamente la **estructura** del modelo de dominio
"Datos de mercado": la representación común de los datos de cotización de
una empresa (precio, capitalización bursátil, múltiplos de valoración)
que usan los agentes de análisis (en particular el de valoración, ver
TASKS.md, "Agente de análisis: valoración") y los generadores de
reportes, sin importar de qué proveedor provino originalmente cada dato
(ver ARCHITECTURE.md, componente 4, "Normalización y almacenamiento").

Igual que `FinancialStatement` (ver
investmentops.data_layer.financial_statements), el alcance de esta tarea
de Fase 1 es un único corte —el más reciente disponible— por empresa, no
una serie histórica. Extender este modelo a series temporales no está
contemplado explícitamente en el roadmap de la forma en que sí lo está
para `FinancialStatement` (ver TASKS.md, Fase 3, "Normalización"); si en
el futuro se necesitara, se abordaría como una tarea separada y explícita,
siguiendo el mismo criterio de no sobre-diseñar antes de tener el caso de
uso real.

Fuera de alcance de este módulo:
- La transformación de los datos crudos de un proveedor
  (investmentops.data_providers.RawProviderData) a este modelo: esa
  transformación es responsabilidad de investmentops.data_layer (tarea
  posterior, ver TASKS.md, sección "Normalización y almacenamiento").
- El cálculo de los múltiplos (ej. P/E, P/B): este módulo solo representa
  los múltiplos ya calculados/obtenidos, no los deriva. El cálculo
  determinístico de múltiplos a partir de precio, capitalización y
  estados financieros es responsabilidad del agente de análisis de
  valoración (ver TASKS.md, "Agente de análisis: valoración").
- El soporte de series históricas (varios cortes de mercado en el
  tiempo): no forma parte de esta tarea.
- La validación de que las cifras sean coherentes o realistas: este
  módulo solo define la forma del dato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Mapping


@dataclass(frozen=True)
class MarketData:
    """Datos de mercado (cotización) normalizados de una empresa, en un corte.

    Es el tipo que usan los agentes de análisis (en particular el de
    valoración) como parte del modelo de dominio normalizado de una
    empresa (`company_data` en `investmentops.analysis_engines`), y que
    los generadores de reportes citan para mostrar de dónde y de cuándo
    provienen las cifras de mercado (ver ARCHITECTURE.md,
    "Reproducibilidad y trazabilidad").

    Attributes
    ----------
    price:
        Precio de cotización de la acción/instrumento al cierre de
        `as_of`, en la moneda que reporte la fuente de datos (este modelo
        no impone ni valida una moneda concreta).
    market_cap:
        Capitalización bursátil de la empresa al cierre de `as_of`.
    multiples:
        Múltiplos de valoración ya calculados u obtenidos de la fuente
        (ej. ``{"pe": 18.4, "pb": 3.1}``), como mapeo de identificador de
        múltiplo (texto libre, en minúsculas, ej. ``"pe"`` para
        price/earnings) a su valor numérico. Este módulo no impone qué
        múltiplos concretos deben estar presentes ni valida sus nombres:
        cuáles se calculan y con qué fórmula es responsabilidad del
        agente de análisis de valoración (ver TASKS.md, "Agente de
        análisis: valoración"), no de este modelo de dominio.
    source:
        Identificador del proveedor de datos del que proviene esta
        información (ej. ``"example_provider"``), tal como se configura
        en `config.local.toml` bajo `[data_providers.<nombre>]` (ver
        CONFIGURATION.md). Mismo criterio que `FinancialStatement.source`.
    as_of:
        Fecha de corte a la que corresponden estos datos de mercado (ej.
        el cierre de la sesión bursátil consultada). No debe confundirse
        con la fecha en que se *consultó* el dato (eso vive en los
        metadatos de procedencia del proveedor,
        `ProviderMetadata.queried_at`): `as_of` es la fecha del propio
        dato de mercado, igual que `period_end` en `FinancialStatement`.
    """

    price: float
    market_cap: float
    multiples: Mapping[str, float]
    source: str
    as_of: date
