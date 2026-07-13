"""Fuentes de datos (Data Providers).

Responsabilidad (ver ARCHITECTURE.md, componente 3):
- Cada proveedor es un módulo independiente que obtiene un tipo de dato
  desde una fuente externa: datos financieros fundamentales, datos de
  mercado, noticias y eventos recientes, o datos de comparables/sector.
- Todos los proveedores implementan el mismo contrato: reciben un
  identificador de empresa (ticker) y devuelven datos crudos junto con
  metadatos de procedencia (fuente, fecha de consulta, confiabilidad).
- El orquestador (investmentops.core) no conoce cómo cada proveedor obtiene
  el dato, solo que cumple el contrato. Esto permite agregar un proveedor
  nuevo sin alterar los proveedores existentes ni el core.

El contrato mencionado arriba ya está definido en
`investmentops.data_providers.contracts` (ver TASKS.md, "Contratos e
interfaces" > "Definir el contrato de 'data provider'") y se re-exporta
aquí para que el resto del sistema lo importe directamente desde
`investmentops.data_providers`:

- `DataProvider`: protocolo que debe cumplir todo proveedor (método
  `fetch(ticker) -> RawProviderData`).
- `RawProviderData`: datos crudos + metadatos de procedencia.
- `ProviderMetadata`: metadatos de procedencia (fuente, fecha de consulta,
  confiabilidad).
- `DataProviderError`: excepción común para señalar fallos del proveedor.

Aún sin implementación: ningún proveedor concreto (ver TASKS.md, sección
"Fuente de datos fundamentales" de la Fase 1).
"""

from investmentops.data_providers.contracts import (
    DataProvider,
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)

__all__ = [
    "DataProvider",
    "DataProviderError",
    "ProviderMetadata",
    "RawProviderData",
]
