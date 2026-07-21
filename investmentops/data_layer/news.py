"""Modelo de dominio "Noticias" (News).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Noticias —
eventos con fecha, fuente y resumen."*, y TASKS.md, Fase 4, sección
"Normalización": *"Definir el modelo de dominio 'Noticias' (fecha,
fuente, resumen)."*

Este módulo define únicamente la **estructura** del modelo de dominio
"Noticias": la representación común de un evento noticioso relacionado
con una empresa (titular, resumen, fuente, fecha de publicación) que
usará el futuro motor de análisis de noticias relevantes (ver
ROADMAP.md, Fase 4, y TASKS.md, "Motor de análisis: noticias relevantes")
y los generadores de reportes, sin importar de qué proveedor provino
originalmente cada noticia (ver ARCHITECTURE.md, componente 4,
"Normalización y almacenamiento").

Este es el cuarto modelo de dominio de `investmentops.data_layer`, junto
a `Company`, `FinancialStatement`/`FinancialStatementSeries` y
`MarketData` (todos definidos en Fase 1/Fase 3). Sigue el mismo patrón ya
usado por esos modelos: un `dataclass(frozen=True)` simple, sin lógica de
negocio ni validación de contenido, que solo fija la forma del dato.

## Campos elegidos

`ARCHITECTURE.md` pide explícitamente "fecha, fuente y resumen". A esos
tres se agregan dos campos adicionales ya disponibles sin costo en los
datos crudos que entrega `FMPNewsProvider.fetch`
(`investmentops/data_providers/news.py`) y que son necesarios para que
una noticia sea útil en un reporte:

- **`title`**: el titular de la noticia (``"title"`` en el payload crudo
  de FMP). Sin él, un "resumen" aislado no tiene contexto suficiente para
  que el usuario decida si le interesa leer más.
- **`summary`**: el resumen/cuerpo de la noticia (``"text"`` en el
  payload crudo de FMP). Es el campo "resumen" que pide `ARCHITECTURE.md`.
- **`source`**: el sitio/medio que publicó la noticia (``"site"`` en el
  payload crudo de FMP, ej. ``"example_news_site"``), **no** el proveedor
  de datos (`"fmp"`) que la entregó. Esta distinción es deliberada: dos
  noticias de la misma consulta a FMP pueden venir de sitios distintos
  (Reuters, Bloomberg, etc.), y esa es la "fuente" periodística relevante
  para el usuario — el proveedor de datos (`fmp`) ya queda registrado en
  otro nivel (`ProviderMetadata.source`, ver
  `investmentops.data_providers.contracts`), no en este modelo de
  dominio. Mismo criterio ya aplicado por `FinancialStatement.source`/
  `MarketData.source`, que también identifican la fuente del dato
  financiero (ej. ``"fmp"``) y no duplican la procedencia de la consulta.
- **`published_at`**: fecha y hora de publicación de la noticia
  (``"publishedDate"`` en el payload crudo de FMP, ej.
  ``"2026-07-15 09:00:00"``). Se usa `datetime`, no `date` (a diferencia
  de `FinancialStatement.period_end`/`MarketData.as_of`), porque FMP
  entrega esta fecha con granularidad de minutos: para noticias, saber si
  algo se publicó a las 9:00 o a las 23:00 del mismo día puede ser
  relevante (ej. antes o después del cierre del mercado), mientras que un
  estado financiero anual/trimestral no tiene esa granularidad que
  preservar.
- **`url`**: enlace a la noticia completa (``"url"`` en el payload crudo
  de FMP). Permite que el reporte final enlace a la fuente original, en
  línea con `ARCHITECTURE.md`, "Reproducibilidad y trazabilidad" — un
  resumen por sí solo no le permite al usuario verificar la noticia
  completa si lo necesita.

## Qué se deja fuera deliberadamente

- **`queried_at`** (cuándo se consultó la noticia): al igual que
  `FinancialStatement`/`MarketData` en Fase 1, este es un metadato de la
  *consulta* (ya vive en `ProviderMetadata.queried_at` y, por punto, en
  el propio payload crudo vía `_attach_news_provenance`, ver
  `investmentops/data_providers/news.py`), no del *dato* de dominio en
  sí. No se propaga a este modelo, mismo criterio ya aplicado.
- **Cualquier interpretación de relevancia o filtrado** (ej. si la
  noticia es reciente o relevante para la empresa): es responsabilidad
  del futuro motor de análisis de noticias (ver TASKS.md, "Motor de
  análisis: noticias relevantes"), no de este modelo de dominio, que solo
  representa el dato ya normalizado.
- **Validación de contenido** (ej. que `url` sea una URL válida, que
  `published_at` no esté en el futuro): este módulo, igual que los demás
  modelos de dominio del proyecto, solo define la forma del dato.

Fuera de alcance de este módulo:
- La transformación de los datos crudos de un proveedor
  (investmentops.data_providers.RawProviderData) a este modelo: esa
  transformación es responsabilidad de investmentops.data_layer (tarea
  separada y siguiente, ver TASKS.md, Fase 4, "Normalización" >
  "Implementar la transformación de noticias crudas al modelo
  normalizado").
- El cacheo/persistencia de noticias normalizadas: tareas separadas y
  posteriores de la misma sección.
- El motor de análisis que consume este modelo (filtrado, resumen,
  relevancia): tarea separada de la sección "Motor de análisis: noticias
  relevantes".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class News:
    """Un evento noticioso normalizado relacionado con una empresa.

    Es el tipo que usará el futuro motor de análisis de noticias
    relevantes (ver ROADMAP.md, Fase 4) como parte del modelo de dominio
    normalizado de una empresa, y que los generadores de reportes citarán
    para mostrar de dónde y de cuándo proviene cada noticia (ver
    ARCHITECTURE.md, "Reproducibilidad y trazabilidad").

    Attributes
    ----------
    title:
        Titular de la noticia.
    summary:
        Resumen o cuerpo de la noticia, tal como lo entrega la fuente de
        datos (este módulo no genera ni recorta el resumen; eso, si
        aplica, es responsabilidad del futuro motor de análisis de
        noticias).
    source:
        Medio o sitio que publicó la noticia (ej. ``"Reuters"``), **no**
        el proveedor de datos que la entregó (ese dato vive en
        `ProviderMetadata.source`, ver
        `investmentops.data_providers.contracts`). Es texto libre: este
        módulo no impone una lista fija de medios reconocidos.
    published_at:
        Fecha y hora en que se publicó la noticia, según la fuente.
    url:
        Enlace a la noticia completa en su fuente original.
    """

    title: str
    summary: str
    source: str
    published_at: datetime
    url: str