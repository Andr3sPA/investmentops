"""Pruebas para el cargador de archivos de prompt
(investmentops.analysis_engines.prompts).

Cubre la nota de `PROGRESS.md` para la tarea "Implementar la invocación
al proveedor de IA configurado con esas métricas + el prompt" (TASKS.md,
Fase 1, "Agente de análisis: salud financiera"): un mecanismo reutilizable
de carga de prompts desde `prompts/<agent_id>.md`, no acoplado a ningún
agente concreto.
"""

from pathlib import Path

import pytest

from investmentops.analysis_engines.prompts import PromptError, load_prompt


def test_load_prompt_reads_content_from_file(tmp_path: Path) -> None:
    (tmp_path / "dummy_agent.md").write_text(
        "Instrucciones de prueba para el agente.", encoding="utf-8"
    )

    content = load_prompt("dummy_agent", prompts_dir=tmp_path)

    assert content == "Instrucciones de prueba para el agente."


def test_load_prompt_raises_when_file_missing(tmp_path: Path) -> None:
    with pytest.raises(PromptError, match="No se encontró"):
        load_prompt("nonexistent_agent", prompts_dir=tmp_path)


def test_load_prompt_raises_when_file_is_empty(tmp_path: Path) -> None:
    (tmp_path / "empty_agent.md").write_text("   \n  ", encoding="utf-8")

    with pytest.raises(PromptError, match="vacío"):
        load_prompt("empty_agent", prompts_dir=tmp_path)


def test_prompt_error_is_a_runtime_error() -> None:
    assert issubclass(PromptError, RuntimeError)


def test_load_prompt_reads_real_financial_health_prompt_from_project() -> None:
    """Sin `prompts_dir` explícito, debe encontrar prompts/financial_health.md
    en la raíz real del proyecto (ver prompts/README.md)."""
    content = load_prompt("financial_health")

    assert "salud financiera" in content.lower()
    assert "recomendación" in content.lower() or "veredicto" in content.lower()
