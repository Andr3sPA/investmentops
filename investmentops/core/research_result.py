"""Modelo "Resultado de investigación" (ResearchResult).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Resultado
de investigación — agregación de todos los resultados de análisis para
una empresa en un momento dado; es lo que finalmente consumen los
generadores de reportes."*, y TASKS.md, Fase 1, sección "Contratos e
interfaces": *"Definir la estructura de 'Resultado de investigación'
(agregación de resultados de análisis para una empresa)."*

Este módulo define únicamente la **estructura** de "Resultado de
investigación": el tipo que el orquestador (componente 2 de
ARCHITECTURE.md) produce al ensamblar, para una empresa dada, los
`AnalysisResult` de todos los motores de análisis ejecutados
(investmentops.analysis_engines), junto con cualquier fallo parcial
ocurrido durante el proceso (una fuente de datos o un motor de análisis
que no pudo completarse). Es, a su vez, el tipo que consumirán los
generadores de reportes (investmentops.reports, aún sin implementar, ver
TASKS.md Fase 2).

Se define en `investmentops.core` (y no en `investmentops.data_layer`,
junto a `Company`, `FinancialStatement` y `MarketData`) por el mismo
criterio ya aplicado con `AnalysisResult`
(investmentops.analysis_engines.contracts): `ResearchResult` no es un dato
que se obtenga de un proveedor externo y se normalice, sino la **salida**
del propio orquestador — el tipo natural para vivir junto al componente
que lo produce (ver ARCHITECTURE.md, "Vista general de capas", componente
2, "Ensamblar los resultados de todos los análisis en un modelo de
'resultado de investigación' único").

Fuera de alcance de este módulo:
- La lógica que efectivamente ensambla un `ResearchResult` (invocar
  fuentes de datos y motores de análisis, capturar sus fallos): eso es
  una tarea posterior y separada (ver TASKS.md, "Orquestador mínimo").
- Cualquier lógica de reportes (Markdown, HTML, JSON) que consuma este
  tipo: corresponde a investmentops.reports (Fase 2).
- La persistencia de un `ResearchResult` en caché/histórico (relevante
  para las Fases 7-9, "Registro personal de investigaciones" y
  "Watchlist"): no es parte de esta tarea de Fase 1.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.data_layer.domain import Company


@dataclass(frozen=True)
class ResearchFailure:
    """Registro explícito de un fallo parcial ocurrido durante una investigación.

    Ver ARCHITECTURE.md, "Manejo de errores y limitaciones": *"Si una
    fuente de datos falla o no tiene información, el orquestador debe
    permitir continuar con las fuentes y análisis restantes, y el reporte
    final debe reflejar explícitamente qué información no pudo
    obtenerse, en vez de fallar silenciosamente o inventar datos."* Este
    tipo es el que le permite a `ResearchResult` cumplir esa exigencia:
    en vez de omitir en silencio una fuente o un agente que falló, el
    orquestador agrega un `ResearchFailure` por cada fallo capturado
    (`DataProviderError` o `AnalysisEngineError`), dejando el resultado
    final completo pero honesto sobre lo que no pudo resolverse.

    Attributes
    ----------
    stage:
        Etapa del flujo de investigación en la que ocurrió el fallo. Es
        texto libre (no una enumeración cerrada) para no acoplar esta
        estructura a las etapas concretas que existan hoy; en la práctica,
        el orquestador de Fase 1 usará valores como ``"data_provider"`` o
        ``"analysis_engine"`` (ver investmentops.data_providers.contracts
        y investmentops.analysis_engines.contracts, cuyas excepciones
        `DataProviderError` y `AnalysisEngineError` son las que el
        orquestador captura para construir este registro).
    identifier:
        Identificador de qué, dentro de esa etapa, fue lo que falló (ej.
        el nombre del proveedor de datos configurado, o el
        `analysis_id` del agente de análisis que no pudo completarse).
    reason:
        Descripción legible del fallo (típicamente el mensaje de la
        excepción capturada), para que el reporte final pueda mostrarle
        al usuario qué ocurrió sin necesidad de que este revise logs.
    """

    stage: str
    identifier: str
    reason: str


@dataclass(frozen=True)
class ResearchResult:
    """Agregación de todos los resultados de análisis de una empresa.

    Es el tipo que el orquestador (investmentops.core) produce al final de
    una investigación (ver ARCHITECTURE.md, "Resumen del flujo de una
    investigación", pasos 5-6), y el que consumirán los generadores de
    reportes (investmentops.reports) para producir Markdown, HTML o JSON.

    Attributes
    ----------
    company:
        La empresa investigada (ver investmentops.data_layer.Company),
        identidad básica (ticker, nombre, sector, mercado) a la que
        corresponden todos los `analysis_results` agregados aquí.
    analysis_results:
        Los `AnalysisResult` (ver
        investmentops.analysis_engines.contracts.AnalysisResult)
        producidos por cada motor de análisis que se ejecutó
        exitosamente para esta empresa (ej. salud financiera,
        valoración). Un motor que falló no aparece aquí: su fallo se
        refleja en `failures`, nunca con un resultado inventado o
        parcial disfrazado de completo.
    failures:
        Fallos parciales ocurridos durante la investigación (una fuente
        de datos que no respondió, un motor de análisis que no pudo
        completarse), conforme a ARCHITECTURE.md, "Manejo de errores y
        limitaciones". Una investigación exitosa de punta a punta tiene
        esta colección vacía; no es un indicador de que la investigación
        completa haya fallado, sino de qué partes específicas no
        pudieron resolverse mientras el resto sigue disponible en
        `analysis_results`.
    generated_at:
        Fecha y hora en que el orquestador ensambló este resultado de
        investigación (distinta de `AnalysisProvenance.generated_at` de
        cada análisis individual, que registra cuándo se generó esa
        interpretación puntual).
    """

    company: Company
    analysis_results: Sequence[AnalysisResult]
    failures: Sequence[ResearchFailure]
    generated_at: datetime
