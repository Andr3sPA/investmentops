"""Carga de archivos de prompt de agentes de análisis (Prompts como artefactos).

Cubre la necesidad, señalada en `PROGRESS.md` como nota para esta tarea,
de contar con "un mecanismo simple de carga de prompts desde
`prompts/<agent_id>.md` reutilizable por futuros agentes (ej. valoración,
Fase 6), en vez de hardcodear la ruta solo para financial_health". Este
módulo implementa exactamente ese mecanismo, sin acoplarse a ningún
agente concreto.

Conforme a `ARCHITECTURE.md` ("Prompts como artefactos, no como código")
y `prompts/README.md` ("Nombre de archivo igual al identificador del
agente/motor de análisis, en snake_case... Ese mismo identificador es el
que usará el agente en código para localizar su prompt"), este módulo
solo sabe traducir un `agent_id` (ej. ``"financial_health"``) a la ruta
`prompts/<agent_id>.md` (relativa a la raíz del proyecto) y devolver su
contenido como texto plano, sin interpretar ni validar el contenido del
prompt más allá de confirmar que no está vacío.

Fuera de alcance de este módulo:
- El contenido de cada prompt concreto: eso vive en los propios archivos
  bajo `prompts/` (ver `prompts/README.md`).
- La invocación al proveedor de IA con el prompt cargado: eso es
  responsabilidad de cada agente concreto (ver
  `investmentops.analysis_engines.financial_health.invoke_financial_health_agent`
  como primer caso de uso).
"""

from __future__ import annotations

from pathlib import Path


class PromptError(RuntimeError):
    """Error al localizar o leer el archivo de prompt de un agente.

    Cubre el caso en que no existe un archivo `prompts/<agent_id>.md`
    para el `agent_id` solicitado, en que existe pero no se puede leer
    (fallo de E/S), o en que existe pero está vacío (un prompt vacío no
    es un prompt válido para invocar a un proveedor de IA, ver
    `investmentops.ai_providers.contracts.AIProvider.complete`, que
    también rechaza prompts vacíos).
    """


def _default_prompts_dir() -> Path:
    """Ruta esperada de la carpeta `prompts/` en la raíz del proyecto.

    Este archivo vive en `investmentops/analysis_engines/prompts.py`, es
    decir dos niveles por debajo de la raíz del proyecto
    (`investmentops/analysis_engines/` -> `investmentops/` -> raíz), la
    misma ubicación relativa que ya usa
    `investmentops.config._default_config_path` para
    `config.local.toml`.
    """
    return Path(__file__).resolve().parent.parent.parent / "prompts"


def load_prompt(agent_id: str, *, prompts_dir: str | Path | None = None) -> str:
    """Carga el contenido del archivo de prompt de un agente.

    Parameters
    ----------
    agent_id:
        Identificador del agente de análisis (ej. ``"financial_health"``),
        el mismo usado en `config.local.toml` bajo `[agents]` (ver
        CONFIGURATION.md) y para nombrar su archivo de prompt (ver
        `prompts/README.md`).
    prompts_dir:
        Carpeta donde buscar `<agent_id>.md`. Si no se indica, se usa
        `prompts/` en la raíz del proyecto. Parámetro pensado sobre todo
        para pruebas, sin depender de los archivos reales del repositorio.

    Returns
    -------
    str
        El contenido de texto plano/Markdown del archivo de prompt, tal
        cual está en disco (sin procesar ni interpretar).

    Raises
    ------
    PromptError
        Si el archivo `<agent_id>.md` no existe en la carpeta de prompts,
        si ocurre un fallo de E/S al leerlo, o si su contenido está vacío
        (o son solo espacios en blanco).
    """
    directory = Path(prompts_dir) if prompts_dir is not None else _default_prompts_dir()
    prompt_path = directory / f"{agent_id}.md"

    if not prompt_path.is_file():
        raise PromptError(
            f"No se encontró el archivo de prompt para el agente "
            f"'{agent_id}' en '{prompt_path}'. Ver prompts/README.md "
            "para la convención de nombres esperada."
        )

    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromptError(
            f"No se pudo leer el archivo de prompt '{prompt_path}': {exc}"
        ) from exc

    if not content.strip():
        raise PromptError(f"El archivo de prompt '{prompt_path}' está vacío.")

    return content
