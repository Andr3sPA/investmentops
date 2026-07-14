"""Cliente mínimo de Financial Modeling Prep (FMP) — datos fundamentales.

Cubre las tareas de TASKS.md, Fase 1, "Fuente de datos fundamentales":

- "Implementar un cliente mínimo que consulte ese proveedor y obtenga
  datos crudos de una empresa por ticker."
- "Adjuntar metadatos de procedencia (nombre de la fuente, fecha/hora de
  consulta) a cada dato crudo obtenido."
- "Implementar manejo de error básico cuando el proveedor no responde o
  el ticker no existe."

El proveedor elegido para el MVP es Financial Modeling Prep (FMP), ver
PROGRESS.md ("Elegir el proveedor de datos financieros fundamentales a
usar para el MVP"). Este módulo implementa el contrato `DataProvider`
(investmentops.data_providers.contracts): recibe un ticker y devuelve
`RawProviderData` (datos crudos + metadatos de procedencia), sin
transformar nada al modelo de dominio interno — esa transformación es
responsabilidad de investmentops.data_layer (tarea posterior, ver
TASKS.md, "Normalización y almacenamiento").

Alcance de "datos crudos" en este cliente: se consultan tres endpoints
básicos de FMP (estado de resultados, balance general y cotización),
combinados en un único `payload` (dict con una clave por endpoint), de
forma que haya suficiente información cruda para las transformaciones
futuras a `FinancialStatement` (ingresos, beneficios, deuda) y
`MarketData` (precio, capitalización, múltiplos). Este cliente no
selecciona ni prioriza qué campos usar de esas respuestas: eso es trabajo
de la capa de normalización.

Fuera de alcance de este módulo:
- La transformación del payload crudo a `FinancialStatement`/`MarketData`
  (ver investmentops.data_layer, tarea posterior).
- El cacheo de resultados (ver TASKS.md, "Normalización y almacenamiento",
  mecanismo de caché local).
- Reintentos automáticos o backoff ante fallos transitorios: el manejo de
  error de esta tarea es básico (señalar el fallo mediante
  `DataProviderError`), no una política de reintentos.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from investmentops.config import load_config
from investmentops.data_providers.contracts import (
    DataProviderError,
    ProviderMetadata,
    RawProviderData,
)

DEFAULT_BASE_URL = "https://financialmodelingprep.com/api/v3"

# Un endpoint por tipo de dato crudo que este cliente combina en un único
# payload. Los nombres de clave del payload coinciden con estos identificadores.
_ENDPOINTS: dict[str, str] = {
    "income_statement": "/income-statement/{ticker}",
    "balance_sheet_statement": "/balance-sheet-statement/{ticker}",
    "quote": "/quote/{ticker}",
}


class FMPFundamentalsProvider:
    """Cliente mínimo de FMP que cumple el contrato `DataProvider`.

    Ver investmentops.data_providers.contracts.DataProvider: cualquier
    objeto con un método `fetch(ticker) -> RawProviderData` cumple el
    contrato de forma estructural (`Protocol`), sin necesidad de heredar
    de una clase base. Esta clase es una implementación concreta de ese
    contrato para el proveedor elegido en la Fase 1 (FMP).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        config: dict[str, Any] | None = None,
        timeout: float = 10.0,
    ) -> None:
        """Crea el cliente, resolviendo credenciales desde argumentos o config.

        Parameters
        ----------
        api_key:
            API key de FMP. Si no se indica, se intenta leer desde
            `config.local.toml`, sección `[data_providers.fundamentals]`
            (ver CONFIGURATION.md).
        base_url:
            URL base de la API de FMP. Si no se indica, se intenta leer
            desde la misma sección de configuración; si tampoco está ahí,
            se usa `DEFAULT_BASE_URL`.
        config:
            Diccionario de configuración ya cargado (como el que devuelve
            `investmentops.config.load_config`). Útil para pruebas, para
            no depender de un `config.local.toml` real en disco. Si no se
            indica y falta `api_key` o `base_url`, se llama a
            `load_config()` para leer el archivo real.
        timeout:
            Tiempo máximo (segundos) de espera por solicitud HTTP.
        """
        if api_key is None or base_url is None:
            cfg = config if config is not None else load_config()
            fundamentals_cfg = cfg.get("data_providers", {}).get("fundamentals", {})
            api_key = api_key or fundamentals_cfg.get("api_key")
            base_url = base_url or fundamentals_cfg.get("base_url")

        if not api_key:
            raise DataProviderError(
                "Falta la API key de FMP. Configúrala en config.local.toml, "
                "sección [data_providers.fundamentals] (ver CONFIGURATION.md)."
            )

        self._api_key = api_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout

    def fetch(self, ticker: str) -> RawProviderData:
        """Obtiene los datos crudos de una empresa desde FMP.

        Consulta los endpoints de estado de resultados, balance general y
        cotización para `ticker`, y combina sus respuestas crudas en un
        único `payload`, junto con los metadatos de procedencia de esta
        consulta (fuente, fecha/hora, confiabilidad).

        Raises
        ------
        DataProviderError
            Si el ticker está vacío, si FMP no responde (error de red),
            si la API key es inválida, o si el ticker no existe (FMP no
            devuelve datos para él).
        """
        if not ticker or not ticker.strip():
            raise DataProviderError("El ticker no puede estar vacío.")

        ticker = ticker.strip().upper()

        payload: dict[str, Any] = {
            key: self._get(path_template.format(ticker=ticker), ticker)
            for key, path_template in _ENDPOINTS.items()
        }

        if not payload["income_statement"] and not payload["quote"]:
            raise DataProviderError(
                f"El ticker '{ticker}' no existe o FMP no devolvió datos "
                "para él."
            )

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)

    def _get(self, path: str, ticker: str) -> Any:
        """Ejecuta una solicitud GET a un endpoint de FMP y devuelve su JSON.

        Traduce cualquier fallo (de red, de autenticación, de formato) a
        `DataProviderError`, conforme al contrato `DataProvider`: nunca
        deja escapar una excepción específica de `requests`.
        """
        url = f"{self._base_url}{path}"
        try:
            response = requests.get(
                url, params={"apikey": self._api_key}, timeout=self._timeout
            )
        except requests.RequestException as exc:
            raise DataProviderError(
                f"No se pudo contactar a FMP para el ticker '{ticker}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise DataProviderError(
                "FMP rechazó la solicitud (API key inválida o sin permisos "
                "para este recurso)."
            )
        if response.status_code == 404:
            return []
        if response.status_code >= 400:
            raise DataProviderError(
                f"FMP respondió con un error ({response.status_code}) para "
                f"el ticker '{ticker}'."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise DataProviderError(
                "FMP devolvió una respuesta que no se pudo interpretar como "
                f"JSON para el ticker '{ticker}'."
            ) from exc
