"""Capa CLI (punto de entrada).

Responsabilidad (ver ARCHITECTURE.md, componente 1):
- Parsear comandos y argumentos del usuario (ej. investigar una empresa por
  ticker, elegir formato de salida).
- Validar argumentos básicos (ticker, formato, rango de fechas).
- Invocar al orquestador (investmentops.core) y mostrar progreso/errores.
- No contiene lógica financiera ni de formateo de reportes; todo eso se
  delega a las capas correspondientes.

Aún sin implementación (ver TASKS.md, sección "CLI" de la Fase 1).
"""
