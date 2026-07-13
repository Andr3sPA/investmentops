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

El modelo de dominio "Empresa" (identidad básica: ticker, nombre, sector,
mercado) ya está definido en `investmentops.data_layer.domain` (ver
TASKS.md, "Contratos e interfaces" > "Definir la estructura del modelo de
dominio 'Empresa'") y se re-exporta aquí para que el resto del sistema lo
importe directamente desde `investmentops.data_layer`:

- `Company`: identidad básica de una empresa (ticker, nombre, sector,
  mercado).

Aún sin implementación (ver TASKS.md, secciones "Contratos e interfaces"
restantes de esta capa —Estados financieros normalizados, Datos de
mercado— y "Normalización y almacenamiento" de la Fase 1).
"""

from investmentops.data_layer.domain import Company

__all__ = [
    "Company",
]
