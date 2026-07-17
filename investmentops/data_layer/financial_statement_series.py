"""Modelo de dominio "Serie de estados financieros normalizados"
(FinancialStatementSeries).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Estados
financieros normalizados — series históricas de ingresos, beneficios,
deuda, flujo de caja, etc., con la fuente y fecha de cada dato."*, y
TASKS.md, Fase 3, sección "Normalización": *"Extender el modelo 'Estados
financieros normalizados' para incluir series temporales (no solo el
dato más reciente)."*

Contexto: `investmentops.data_layer.financial_statements.FinancialStatement`
(Fase 1) representa deliberadamente un único corte -el más reciente- por
empresa, dejando explícito en su propio docstring que extenderlo a series
temporales era alcance explícito y posterior de la Fase 3 (ver también
`investmentops/data_providers/HISTORICAL_DATA.md` y
`FMPFundamentalsProvider.fetch_historical`, que ya consultan y devuelven
varios periodos históricos con procedencia por punto, ver PROGRESS.md).

## Decisión de diseño: reutilizar `FinancialStatement` por punto

En vez de introducir un tipo nuevo para cada punto de la serie, este
módulo reutiliza `FinancialStatement` tal cual (`revenue`, `net_income`,
`debt`, `source`, `period_end`) como el tipo de cada elemento: sus campos
ya son exactamente los que necesita cada punto histórico (ver
`financial_statement_from_raw`, que ya construye un `FinancialStatement`
por corte a partir de un único periodo del payload crudo). Esto evita
duplicar una estructura casi idéntica y mantiene consistencia con el
modelo ya usado en Fase 1 y Fase 2 (agentes de análisis, reportes), que
ya saben trabajar con `FinancialStatement` sin cambios.

`FinancialStatementSeries` es entonces un contenedor simple: el `ticker`
de la empresa y una secuencia ordenada de `FinancialStatement`, del
periodo más reciente al más antiguo — mismo orden que ya devuelve FMP y
que ya asume `financial_statement_from_raw` al tomar el primer elemento
como "el más reciente" (ver `investmentops/data_layer/normalization.py`).

## Qué se deja fuera deliberadamente

- **`queried_at` por punto:** `FMPFundamentalsProvider.fetch_historical`
  ya adjunta `"source"`/`"queried_at"` a cada punto crudo de la serie
  (ver PROGRESS.md, tarea "Adjuntar metadatos de procedencia a cada
  punto de la serie histórica"). Este modelo de dominio solo conserva
  `source` (vía el `FinancialStatement.source` de cada punto), mismo
  criterio que ya aplica `FinancialStatement` en Fase 1: `queried_at` es
  metadato de la *consulta* (`ProviderMetadata`/procedencia cruda), no
  del *dato financiero* en sí, y no se propaga al modelo de dominio
  normalizado (ver `financial_statement_from_raw`, que tampoco lo
  conserva para el corte único de Fase 1).
- **Validación de la serie** (orden, huecos, periodos duplicados): fuera
  de alcance de esta tarea de estructura; corresponde, si aplica, a la
  tarea siguiente ("Implementar la transformación de la respuesta cruda
  histórica al modelo de series temporales") o al futuro motor de
  análisis de evolución (ver ROADMAP.md, Fase 3).
- **Series temporales de `MarketData`:** `ARCHITECTURE.md` y
  `ROADMAP.md` centran la Fase 3 explícitamente en ingresos y
  beneficios, no en series de precio de mercado (ver también
  `HISTORICAL_DATA.md`, "Fuera de alcance de esta tarea"). No se define
  aquí un equivalente para `MarketData`.

Fuera de alcance de este módulo:
- La transformación de la respuesta cruda histórica (`RawProviderData`
  de `fetch_historical`) a este modelo: tarea separada y siguiente en la
  misma sección de `TASKS.md`.
- Extender la caché local para persistir series históricas: tarea
  separada y posterior en la misma sección.
- El motor de análisis de evolución de ingresos y beneficios que
  consumirá este modelo: tarea separada de la Fase 3 (ver ROADMAP.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from investmentops.data_layer.financial_statements import FinancialStatement


@dataclass(frozen=True)
class FinancialStatementSeries:
    """Serie temporal de estados financieros normalizados de una empresa.

    Es el tipo que representará, a partir de la tarea de transformación
    siguiente, la respuesta de `FMPFundamentalsProvider.fetch_historical`
    ya normalizada, y el que consumirá el futuro motor de análisis de
    evolución de ingresos y beneficios (ver ROADMAP.md, Fase 3).

    Attributes
    ----------
    ticker:
        Identificador de la empresa a la que corresponde esta serie (ej.
        ``"AAPL"``), mismo criterio de identidad ya usado por `Company`
        (`investmentops.data_layer.domain`).
    statements:
        Secuencia de `FinancialStatement`, uno por periodo, ordenada del
        más reciente al más antiguo (mismo orden que ya devuelve FMP y
        que ya asume `financial_statement_from_raw` para el corte único
        de Fase 1). Puede tener uno o varios elementos; este módulo no
        impone un mínimo ni valida que los periodos sean contiguos o
        estén libres de huecos (ver "Qué se deja fuera deliberadamente"
        en el docstring del módulo).
    """

    ticker: str
    statements: Sequence[FinancialStatement]
