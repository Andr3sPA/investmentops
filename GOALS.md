# InvestmentOps — Objetivos del Proyecto

## Problema que resuelve

Antes de invertir en una empresa a través de plataformas como Tyba o Trii, es necesario investigarla: entender su salud financiera, su valoración, su evolución histórica, sus riesgos y el contexto que la rodea. Hoy esa investigación está dispersa en múltiples fuentes (estados financieros, noticias, comparables del sector, opiniones de distintas escuelas de análisis) y hacerla de forma manual, cada vez, es lento y propenso a omisiones.

InvestmentOps existe para **centralizar y estructurar el proceso de investigación previo a una decisión de inversión**, presentando la información relevante de forma clara y organizada para que quien invierte —en este caso, el propio autor del proyecto— pueda formarse un juicio informado.

Es una herramienta de **apoyo al análisis**, no un sistema de gestión de portafolio ni un asesor automático.

## Qué NO resuelve este proyecto

Para que el alcance quede explícito y no se desvíe con el tiempo:

- **No es una aplicación SaaS.** No está pensada para terceros, no tiene multi-tenancy.
- **No tiene múltiples usuarios ni autenticación.** Es una herramienta personal, de un solo usuario.
- **No tiene frontend en el MVP.** No hay interfaz web ni gráfica.
- **No expone una API REST en esta primera versión.**
- **No administra portafolios.** No hace seguimiento de posiciones, rendimientos, aportes, ni rebalanceo.
- **No ejecuta ni conecta con órdenes de compra/venta.** No interactúa con Tyba, Trii ni ningún bróker para operar.
- **No toma decisiones de inversión.** No dice "compra" o "vende", ni entrega recomendaciones prescriptivas.
- **No sustituye el juicio del inversionista.** Su función es informar y organizar, no decidir.

## Cómo se usará

El sistema se ejecutará **completamente de forma local**, mediante una **CLI**. Se invoca sobre una empresa o ticker específico y devuelve información organizada para apoyar el análisis antes de tomar una decisión de inversión.

## Preguntas que el MVP debe ayudar a responder

1. ¿Esta empresa está financieramente sana?
2. ¿Está cara o barata (valoración)?
3. ¿Cómo han evolucionado sus ingresos?
4. ¿Cómo han evolucionado sus beneficios?
5. ¿Qué riesgos tiene?
6. ¿Qué noticias recientes podrían afectarla?
7. ¿Cómo se compara con empresas similares (comparables del sector)?
8. ¿Qué dirían distintas estrategias o escuelas de inversión sobre esta empresa?

## Objetivos del MVP

- Permitir consultar, vía CLI, información financiera básica de una empresa (salud financiera, ingresos, beneficios, valoración) de forma estructurada y legible.
- Presentar la evolución histórica de ingresos y beneficios de forma que se puedan identificar tendencias.
- Identificar y listar riesgos relevantes de la empresa.
- Recopilar noticias recientes relacionadas con la empresa.
- Permitir comparar la empresa con pares del mismo sector en métricas clave.
- Ofrecer, sobre la misma empresa, distintas "lecturas" o perspectivas según diferentes estrategias de inversión conocidas (por ejemplo, value investing, growth investing, análisis de calidad, etc.), presentadas como opiniones contrastables entre sí, no como una única verdad.
- Mantener siempre un rol informativo: el sistema explica y contextualiza datos, pero **nunca emite una recomendación de compra o venta ni una decisión final**.

## Principio rector

InvestmentOps debe ayudar a **entender mejor una inversión antes de tomarla**, no a automatizar la decisión de invertir. El usuario sigue siendo, en todo momento, quien decide.
