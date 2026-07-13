"""Modelo de dominio "Empresa" (Company).

Ver ARCHITECTURE.md, "Modelo de datos interno (conceptual)": *"Empresa —
identidad básica (ticker, nombre, sector, mercado)."*, y TASKS.md, Fase 1,
sección "Contratos e interfaces": *"Definir la estructura del modelo de
dominio 'Empresa' (ticker, nombre, sector, mercado)."*

Este módulo define únicamente la **estructura** del modelo de dominio
"Empresa": la identidad básica que usan el resto de las capas (fuentes de
datos, agentes de análisis, reportes) para referirse a una empresa de
forma consistente, sin importar de qué proveedor provino originalmente
cada dato (ver ARCHITECTURE.md, componente 4, "Normalización y
almacenamiento").

Este es el primero de varios modelos de dominio que vivirán en
`investmentops.data_layer` (ver ARCHITECTURE.md, "Modelo de datos
interno"): los siguientes (Estados financieros normalizados, Datos de
mercado, Noticias, Comparables) se definen en tareas separadas y
posteriores (ver TASKS.md, "Contratos e interfaces"), cada uno en su
propio módulo si su complejidad lo justifica.

Fuera de alcance de este módulo:
- La transformación de los datos crudos de un proveedor
  (investmentops.data_providers.RawProviderData) a este modelo: esa
  transformación es responsabilidad de investmentops.data_layer (tarea
  posterior, ver TASKS.md, sección "Normalización y almacenamiento").
- La validación de que un ticker/sector/mercado sea válido o exista
  realmente: este módulo solo define la forma del dato, no reglas de
  negocio sobre su contenido.
- Los demás modelos de dominio (Estados financieros normalizados, Datos
  de mercado, Noticias, Comparables): cada uno se define en su propia
  tarea (ver TASKS.md, "Contratos e interfaces").
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    """Identidad básica de una empresa dentro del modelo de dominio interno.

    Este es el tipo que usan las demás capas (agentes de análisis,
    generadores de reportes) para referirse a una empresa de forma común,
    independientemente del proveedor de datos del que haya salido cada
    dato original (ver ARCHITECTURE.md, "Modelo de datos interno").

    Attributes
    ----------
    ticker:
        Identificador bursátil de la empresa, tal como se usa para
        consultarla en los proveedores de datos (ej. ``"AAPL"``,
        ``"ECOPETROL.CL"``). Es el identificador primario de la empresa
        dentro del sistema.
    name:
        Nombre legible de la empresa (ej. ``"Apple Inc."``).
    sector:
        Sector o industria a la que pertenece la empresa (ej.
        ``"Tecnología"``, ``"Energía"``), tal como lo reporte la fuente de
        datos. Es texto libre: este módulo no impone una taxonomía fija de
        sectores.
    market:
        Mercado o bolsa donde cotiza la empresa (ej. ``"NASDAQ"``,
        ``"NYSE"``, ``"BVC"`` para la Bolsa de Valores de Colombia,
        relevante para empresas operadas vía Tyba/Trii). Es texto libre
        por la misma razón que `sector`.
    """

    ticker: str
    name: str
    sector: str
    market: str
