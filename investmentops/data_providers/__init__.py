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

Aún sin implementación (ver TASKS.md, secciones "Contratos e interfaces" y
"Fuente de datos fundamentales" de la Fase 1).
"""
