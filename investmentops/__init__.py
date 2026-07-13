"""InvestmentOps.

Herramienta CLI local de apoyo a la investigación previa a una decisión de
inversión. Ver GOALS.md (qué resuelve y qué no) y ARCHITECTURE.md (capas y
contratos) en la raíz del proyecto.

Este paquete organiza el sistema en las capas descritas en ARCHITECTURE.md:

- cli               -> punto de entrada, parseo de comandos.
- core              -> orquestador (coordina fuentes, análisis y reportes).
- data_providers     -> fuentes de datos externas (financieras, mercado,
                        noticias, comparables).
- data_layer         -> normalización al modelo de dominio interno y
                        caché/histórico local.
- analysis_engines   -> agentes de análisis (salud financiera, valoración,
                        riesgos, estrategias, etc.), apoyados en IA.
- ai_providers       -> interfaz común de proveedores de IA (Gemini, Claude,
                        OpenAI, Ollama), transversal a analysis_engines y
                        reports.
- reports            -> generadores de reportes (Markdown, HTML, JSON).
- config            -> carga de la configuración local (config.local.toml),
                        ver CONFIGURATION.md.

Ningún módulo de análisis/datos/reportes contiene aún lógica de negocio:
la estructura base sigue vacía salvo por la carga de configuración local
(investmentops.config), ya implementada (ver TASKS.md, sección "Setup del
proyecto").
"""
