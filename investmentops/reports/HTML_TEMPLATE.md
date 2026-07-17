# Plantilla base HTML — estructura mínima (Fase 2)

Cubre la tarea "Definir la plantilla base HTML (estructura mínima, sin
diseño elaborado)" (TASKS.md, Fase 2, "Generador HTML").

Esta tarea es de **diseño/documentación**, no de código: fija la
estructura HTML mínima antes de implementar el volcado de contenido
(tarea siguiente, "Implementar el volcado de las mismas secciones que en
Markdown"). No se crea todavía `investmentops/reports/html.py`.

## Decisión: HTML5 mínimo, sin CSS elaborado, mismas secciones y orden que Markdown

El generador HTML reutiliza exactamente la misma estructura de
contenido ya fijada en `investmentops/reports/REPORT_SECTIONS.md`
(encabezado con identidad de la empresa → salud financiera → valoración
→ fallos parciales si existen), consumiendo el mismo `ResearchResult`
sin ningún tipo intermedio nuevo (ver
`investmentops/reports/REPORT_MODEL.md`). Lo único que cambia frente al
generador Markdown es el formato de marcado (etiquetas HTML en vez de
sintaxis Markdown), no el contenido ni el orden.

Conforme al alcance explícito de esta tarea ("sin diseño elaborado"):

- **Sin hoja de estilos externa ni framework CSS.** Como mucho, un
  bloque `<style>` mínimo embebido en el propio `<head>` (tipografía de
  sistema, ancho máximo legible, espaciado básico), suficiente para que
  el reporte sea legible al abrirlo en un navegador sin depender de
  ningún recurso externo (`ARCHITECTURE.md`, "un solo usuario, todo
  local": el archivo debe poder abrirse sin conexión a internet).
- **Sin JavaScript.** El reporte es un documento estático de lectura,
  no una aplicación interactiva.
- **Sin plantillas externas ni motor de templating** (Jinja2 u otro):
  el HTML se construye igual que el Markdown, con las mismas funciones
  puras de Python que ya arman `render_markdown` (concatenar líneas),
  sin sumar una dependencia nueva al proyecto (mismo criterio ya
  aplicado en `CONFIGURATION.md` al elegir TOML de la librería estándar
  en vez de sumar una dependencia de parseo).

## Esqueleto HTML5 mínimo

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Investigación: {ticker}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1rem; }
    h1, h2 { border-bottom: 1px solid #ccc; padding-bottom: 0.25rem; }
  </style>
</head>
<body>
  <h1>Investigación: {ticker}</h1>
  <p>{identidad de la empresa, si name/sector/market no están vacíos}</p>
  <p>Generado: {generated_at ISO 8601}</p>

  <h2>Salud financiera</h2>
  <!-- hallazgos, métricas de soporte, limitaciones, procedencia de IA -->

  <h2>Valoración</h2>
  <!-- hallazgos, métricas de soporte, limitaciones, procedencia de IA -->

  <!-- Fallos parciales, solo si existen -->
</body>
</html>
```

- `<title>` incluye el ticker, para que la pestaña del navegador sea
  identificable si se abren varios reportes a la vez.
- `lang="es"` porque todo el contenido generado (hallazgos, prompts,
  mensajes) ya está en español, conforme al resto del proyecto.
- Los encabezados de sección (`<h2>Salud financiera</h2>`,
  `<h2>Valoración</h2>`) se emiten **siempre**, estén o no presentes sus
  respectivos `AnalysisResult`, mismo comportamiento ya usado por
  `render_markdown` (una sección vacía conserva su encabezado, en vez de
  omitirse en silencio).

## Mapeo de contenido (equivalente al Markdown)

| Elemento Markdown (`render_markdown`)              | Equivalente HTML                                      |
|-----------------------------------------------------|--------------------------------------------------------|
| `# Investigación: {ticker}`                          | `<h1>Investigación: {ticker}</h1>`                     |
| Línea de identidad (`name · sector · market`)        | `<p>{name} · {sector} · {market}</p>` (omitida si vacía) |
| `Generado: {fecha}`                                  | `<p>Generado: {fecha}</p>`                             |
| `## Salud financiera` / `## Valoración`              | `<h2>Salud financiera</h2>` / `<h2>Valoración</h2>`    |
| Hallazgos (`findings`)                               | Un `<p>` por hallazgo                                  |
| `**Métricas de soporte:**` + lista                   | `<h3>Métricas de soporte</h3>` + `<ul><li>clave: valor</li>...</ul>` |
| `**Limitaciones:**` + lista                          | `<h3>Limitaciones</h3>` + `<ul><li>...</li></ul>` (omitida si vacía) |
| `**Generado por:** proveedor (modelo) el fecha`      | `<p><em>Generado por: proveedor (modelo) el fecha</em></p>` |
| Sección de fallos parciales (ya en `format_research_result`, CLI Fase 1) | `<h2>Fallos parciales</h2>` + `<ul><li>[stage] identifier: reason</li>...</ul>` (omitida si `failures` está vacío) |

## Fuera de alcance de esta tarea

- El volcado real de contenido (hallazgos, métricas, limitaciones,
  procedencia) dentro de esta estructura: tarea siguiente en la misma
  sección de `TASKS.md` ("Implementar el volcado de las mismas secciones
  que en Markdown").
- El guardado del archivo HTML generado en disco: tarea separada y
  posterior de la misma sección ("Implementar el guardado del archivo
  HTML generado en una ruta local configurable"), que seguirá el mismo
  patrón ya usado por `save_markdown_report`
  (`investmentops/reports/markdown.py`).
- Cualquier mejora visual más allá de lo mínimo (temas, capacidad de
  imprimir, responsive design elaborado): no hay caso de uso que lo
  justifique todavía, mismo criterio de "no sobre-diseñar antes de
  tener el caso de uso real" ya aplicado en el resto del proyecto (ver
  `investmentops/data_layer/market_data.py`,
  `investmentops/data_layer/CACHE.md`).
- Escapado de caracteres especiales HTML (`<`, `>`, `&`) en el
  contenido dinámico (hallazgos generados por el modelo de IA, nombres
  de empresa, etc.): decisión de implementación que corresponde a la
  tarea siguiente (el volcado de contenido), no a esta tarea de diseño
  de la estructura.
