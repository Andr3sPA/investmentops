"""Contrato de "Data Provider" (Fuentes de datos).

Ver ARCHITECTURE.md, componente 3 ("Fuentes de datos"), y TASKS.md, Fase 1,
sección "Contratos e interfaces": *"Definir el contrato de 'data provider'
(entrada: ticker; salida: datos crudos + metadatos de procedencia)."*

Este módulo NO implementa ningún proveedor concreto (eso es una tarea
posterior, ver TASKS.md, sección "Fuente de datos fundamentales"). Solo
define el contrato que todo proveedor de datos debe cumplir, de forma que:

- El orquestador (investmentops.core) pueda invocar cualquier proveedor sin
  conocer su implementación concreta.
- Agregar un proveedor nuevo (ej. para el mercado colombiano, o uno de
  noticias/comparables en fases futuras) no requiera modificar el
  orquestador ni los proveedores ya existentes (ver ARCHITECTURE.md,
  "Extensibilidad").

Resumen del contrato (ver ARCHITECTURE.md, componente 3):

- **Entrada:** un identificador de empresa (ticker).
- **Salida:** datos crudos (sin normalizar) junto con metadatos de
  procedencia: fuente, fecha/hora de consulta y confiabilidad.
- **Fallos:** un proveedor que no puede responder (proveedor caído, ticker
  inexistente, formato inesperado, etc.) debe señalarlo mediante
  `DataProviderError`, nunca devolviendo datos parciales o inventados en su
  lugar. Esto es lo que le permite al orquestador (ver ARCHITECTURE.md,
  "Manejo de errores y limitaciones") continuar con las demás fuentes y
  dejar el fallo explícito en el resultado, en vez de fallar en silencio o
  detener todo el flujo.

Fuera de alcance de este módulo:
- Cualquier implementación concreta de proveedor (HTTP, SDK, etc.).
- La transformación de `payload` (datos crudos) al modelo de dominio común
  (Estados financieros normalizados, Datos de mercado): eso corresponde a
  investmentops.data_layer.
- Validación del formato/contenido de `payload`: cada proveedor concreto es
  responsable de que sus propios datos sean coherentes; este contrato solo
  exige que, si no puede garantizarlo, levante `DataProviderError` en vez
  de devolver algo incorrecto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


class DataProviderError(RuntimeError):
    """Error al obtener datos desde un proveedor externo.

    Cubre cualquier fallo del propio proveedor: no responde, el ticker no
    existe, devuelve un formato inesperado, etc. El orquestador
    (investmentops.core) captura este tipo de excepción para continuar con
    las demás fuentes en vez de detener todo el flujo (ver
    ARCHITECTURE.md, "Manejo de errores y limitaciones").
    """


@dataclass(frozen=True)
class ProviderMetadata:
    """Metadatos de procedencia de un dato obtenido de un proveedor.

    Attributes
    ----------
    source:
        Nombre identificador del proveedor/fuente concreta que entregó el
        dato (ej. ``"example_provider"``). Debe coincidir con el nombre
        usado en `config.local.toml` bajo `[data_providers.<nombre>]`
        (ver CONFIGURATION.md), de forma que un reporte pueda trazar cada
        dato hasta su configuración de origen.
    queried_at:
        Fecha y hora en que se realizó la consulta al proveedor.
    reliability:
        Descripción breve y legible de la confiabilidad de la fuente para
        este dato (ej. ``"alta"``, ``"media"``, ``"estimado"``). Es texto
        libre y no se valida contra una lista fija: cada proveedor decide
        cómo describir su propia confiabilidad.
    """

    source: str
    queried_at: datetime
    reliability: str


@dataclass(frozen=True)
class RawProviderData:
    """Resultado crudo (sin normalizar) de consultar un proveedor.

    Este es el tipo de salida que todo "data provider" debe devolver. El
    contenido de `payload` es intencionalmente de forma libre (`Any`) y
    específico de cada proveedor: la responsabilidad de traducirlo al
    modelo de dominio común (Empresa, Estados financieros normalizados,
    Datos de mercado) es de investmentops.data_layer, no de este contrato
    ni del proveedor.

    Attributes
    ----------
    ticker:
        El identificador de empresa consultado, tal como se recibió.
    payload:
        Los datos crudos devueltos por el proveedor, en su forma original
        (ej. el JSON/dict que entrega su API), sin transformar.
    metadata:
        Metadatos de procedencia de esta consulta (ver `ProviderMetadata`).
    """

    ticker: str
    payload: Any
    metadata: ProviderMetadata


@runtime_checkable
class DataProvider(Protocol):
    """Contrato común que debe cumplir todo proveedor de datos.

    Cualquier módulo bajo investmentops.data_providers que implemente este
    contrato puede ser invocado por el orquestador sin que este último
    conozca su implementación concreta (ver ARCHITECTURE.md, "Regla de
    dependencia" y "Extensibilidad").

    Se define como `Protocol` (tipado estructural) en vez de una clase
    base abstracta: cualquier objeto que exponga un método `fetch` con
    esta firma cumple el contrato, sin necesidad de heredar de una clase
    concreta. Esto deja abierta la forma de la implementación concreta
    (función envuelta en una clase simple, cliente HTTP, etc.) para la
    tarea de "Fuente de datos fundamentales" en TASKS.md.
    """

    def fetch(self, ticker: str) -> RawProviderData:
        """Obtiene los datos crudos de una empresa desde este proveedor.

        Parameters
        ----------
        ticker:
            Identificador de la empresa a consultar (ej. ``"AAPL"``).

        Returns
        -------
        RawProviderData
            Los datos crudos obtenidos, junto con sus metadatos de
            procedencia.

        Raises
        ------
        DataProviderError
            Si el proveedor no responde, el ticker no existe, o la
            respuesta no se puede interpretar. Nunca debe devolver datos
            inventados o parciales como si fueran válidos.
        """
        ...
