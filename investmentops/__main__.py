"""Punto de entrada de conveniencia: `python -m investmentops`.

Esto NO es la implementación de la CLI (eso corresponde a las tareas de la
sección "CLI" en TASKS.md, Fase 1). Por ahora solo confirma que la
estructura base del proyecto se puede ejecutar sin errores y que la
configuración local (`config.local.toml`) se puede cargar al iniciar el
sistema (ver investmentops.config y CONFIGURATION.md).
"""

from investmentops.config import ConfigError, load_config

if __name__ == "__main__":
    print("InvestmentOps - estructura base del proyecto (en construccion).")
    print("Ver TASKS.md para el estado de las tareas y ROADMAP.md para las fases.")

    try:
        load_config()
    except ConfigError as exc:
        print(f"\n[config] {exc}")
    else:
        print("\n[config] config.local.toml cargado correctamente.")
