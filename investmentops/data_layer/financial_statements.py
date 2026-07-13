"""Modelo de dominio "Estados financieros normalizados" (FinancialStatement).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Estados
financieros normalizados — series históricas de ingresos, beneficios,
deuda, flujo de caja, etc., con la fuente y fecha de cada dato."*, y
TASKS.md, Fase 1, sección "Contratos e interfaces": *"Definir la
estructura del modelo de dominio 'Estados financieros normalizados'
(ingresos, beneficios, deuda, con fuente y fecha)."*

Este módulo define únicamente la **estructura** del modelo de dominio
"Estados financieros normalizados": la representación común de las cifras
financieras básicas de una empresa (ingresos, beneficios, deuda) que usan
los agentes de análisis (ej. salud financiera, valoración) y los
generadores de reportes, sin importar de qué proveedor provino
originalmente cada dato (ver ARCHITECTURE.md, componente 4, "Normalización
y almacenamiento").

Alcance de esta tarea (Fase 1): un único corte —el más reciente
disponible— por empresa, con su propia fuente y fecha. `ARCHITECTURE.md`
describe este modelo a futuro como "series históricas"; extenderlo para
soportar varios periodos (varios años/trimestres) es una tarea explícita
y posterior de la Fase 3 (ver TASKS.md, Fase 3, "Normalización" > "Extender
el modelo 'Estados financieros normalizados' para incluir series
temporales (no solo el dato más reciente)"). Definir aquí ya una
estructura de serie temporal adelantaría trabajo de esa fase sin que
todavía exista la fuente de datos histórica ni el motor de análisis de
evolución que la consumiría (ver ROADMAP.md, Fase 3).

Fuera de alcance de este módulo:
- La transformación de los datos crudos de un proveedor
  (investmentops.data_providers.RawProviderData) a este modelo: esa
  transformación es responsabilidad de investmentops.data_layer (tarea
  posterior, ver TASKS.md, sección "Normalización y almacenamiento").
- El cálculo de ratios o métricas derivadas (liquidez, endeudamiento,
  rentabilidad, múltiplos de valoración): eso es responsabilidad de cada
  agente de análisis concreto (ver TASKS.md, "Agente de análisis: salud
  financiera" y "Agente de análisis: valoración"), que consume este
  modelo como entrada.
- El soporte de series históricas (varios periodos): tarea explícita de
  la Fase 3 (ver más arriba).
- La validación de que las cifras sean coherentes o realistas: este
  módulo solo define la forma del dato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialStatement:
    """Cifras financieras básicas normalizadas de una empresa, en un corte.

    Es el tipo que usan los agentes de análisis (ej. salud financiera,
    valoración) como parte del modelo de dominio normalizado de una
    empresa (`company_data` en `investmentops.analysis_engines`), y que
    los generadores de reportes citan para mostrar de dónde y de cuándo
    provienen las cifras (ver ARCHITECTURE.md, "Reproducibilidad y
    trazabilidad").

    Attributes
    ----------
    revenue:
        Ingresos totales reportados por la empresa en el periodo de
        `period_end` (ej. ingresos anuales o trimestrales, según lo que
        entregue la fuente de datos).
    net_income:
        Beneficio o utilidad neta del mismo periodo.
    debt:
        Deuda total (financiera) reportada al cierre del periodo.
    source:
        Identificador del proveedor de datos del que proviene esta
        información (ej. ``"example_provider"``), tal como se configura
        en `config.local.toml` bajo `[data_providers.<nombre>]` (ver
        CONFIGURATION.md). Permite trazar estas cifras hasta su fuente,
        igual que `ProviderMetadata.source` en
        `investmentops.data_providers.contracts`.
    period_end:
        Fecha de corte a la que corresponden estas cifras (ej. cierre del
        último año o trimestre fiscal reportado). No debe confundirse con
        la fecha en que se *consultó* el dato (eso vive en los metadatos
        de procedencia del proveedor, `ProviderMetadata.queried_at`):
        `period_end` es la fecha del propio estado financiero.
    """

    revenue: float
    net_income: float
    debt: float
    source: str
    period_end: date
