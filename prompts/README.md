# Prompts

Esta carpeta vive **fuera** del paquete Python (`investmentops/`), a la
misma altura que la raíz del proyecto. Contiene el prompt de cada agente
de análisis (y, más adelante, del agente de reporte) como un archivo de
texto independiente, tal como lo exige `ARCHITECTURE.md`:

> "Prompts como artefactos, no como código. El texto de los prompts de
> cada agente vive en archivos independientes (fuera del código Python),
> de forma que puedan revisarse, versionarse y ajustarse sin tocar la
> lógica de orquestación ni de parsing."

## Convención

- Un archivo de prompt por agente, en formato Markdown (`.md`).
- Nombre de archivo igual al identificador del agente/motor de análisis,
  en `snake_case` (ej. `financial_health.md`, `valuation.md`). Ese mismo
  identificador es el que usará el agente en código para localizar su
  prompt.
- El contenido de cada archivo es texto plano/Markdown: instrucciones para
  el modelo de lenguaje sobre cómo interpretar los datos y métricas que
  recibe. No contiene código Python ni lógica de parseo.
- Ningún prompt debe pedirle al modelo que emita una recomendación de
  compra/venta ni un veredicto final, conforme al principio rector de
  `GOALS.md` y a la restricción arquitectónica de `ARCHITECTURE.md`.

## Estado actual

Todavía no hay archivos de prompt: los agentes de análisis (salud
financiera, valoración, etc.) aún no están implementados. Esta carpeta
queda lista para que cada agente, al implementarse, agregue su propio
archivo aquí (ver `TASKS.md`, secciones "Agente de análisis: salud
financiera" y "Agente de análisis: valoración" de la Fase 1).