"""Motores de análisis (Agentes de IA / Analysis Engines).

Responsabilidad (ver ARCHITECTURE.md, componente 5):
- Cada motor de análisis es un agente especializado que responde a una de
  las preguntas de investigación de GOALS.md (ej. salud financiera,
  valoración, riesgos, evolución de ingresos/beneficios, noticias
  relevantes, comparables, lecturas por estrategia de inversión).
- Todos los agentes comparten un contrato común: reciben el modelo de
  dominio normalizado (investmentops.data_layer) de una empresa y, cuando
  aplica, métricas ya calculadas de forma determinística, y devuelven un
  resultado estructurado (hallazgos, métricas, advertencias) — nunca una
  recomendación de acción.
- Cada agente carga su prompt desde un archivo independiente (fuera del
  código Python) e invoca al proveedor de IA configurado a través de la
  interfaz común (investmentops.ai_providers), nunca directamente a un SDK.
- Un agente no depende de otro agente ni de una fuente de datos específica;
  depende del modelo de dominio interno y de la interfaz de proveedores de
  IA.

Aún sin implementación (ver TASKS.md, secciones "Agente de análisis: salud
financiera" y "Agente de análisis: valoración" de la Fase 1).
"""
