"""Cliente mínimo de Financial Modeling Prep (FMP) — empresas comparables.

Cubre la tarea "Implementar la consulta de comparables (lista de empresas
pares) para un ticker" (TASKS.md, Fase 5, "Fuente de datos de
comparables"), sobre la decisión ya tomada en
`investmentops/data_providers/COMPARABLES_PROVIDER.md`: reutilizar
**Financial Modeling Prep (FMP)**, el mismo proveedor ya integrado desde
la Fase 1, vía su endpoint `/v4/stock_peers`.

Este módulo implementa el contrato `DataProvider`
(investmentops.data_providers.contracts): recibe un ticker y devuelve
`RawProviderData` (datos crudos + metadatos de procedencia), sin
transformar nada al modelo de dominio interno — esa transformación
("Comparables", modelo de dominio normalizado) es una tarea posterior y
separada (ver TASKS.md, Fase 5, "Normalización").

## Alcance de esta tarea

Cubre únicamente el **contrato básico**: ticker de entrada, lista cruda
de empresas pares (`payload`, tal como la entrega FMP, sin transformar)
de salida, junto con los metadatos de procedencia de la consulta
completa (`ProviderMetadata`, mismo criterio ya usado por
`FMPFundamentalsProvider.fetch`/`FMPNewsProvider.fetch`). Incluye manejo
de error básico (red, autenticación, errores de servidor, JSON
inválido) porque el contrato `DataProvider` ya exige señalar cualquier
fallo mediante `DataProviderError`, nunca devolviendo datos inventados o
parciales — el mismo criterio ya aplicado en
`FMPFundamentalsProvider.fetch` y `FMPNewsProvider.fetch`, ninguno de los
cuales pudo entregarse "mínimo" sin ese manejo de error.

Explícitamente fuera de alcance de esta tarea (ver TASKS.md, tareas
siguientes de esta misma sección):
- **Procedencia por empresa par individual** (adjuntar `"source"`/
  `"queried_at"` a cada elemento del payload, mismo patrón ya usado por
  `_attach_point_provenance`/`_attach_news_provenance`): tarea separada y
  posterior ("Adjuntar metadatos de procedencia a los datos de
  comparables").
- **La consulta de métricas clave para cada empresa par** (reutilizando
  `FMPFundamentalsProvider.fetch`, `financial_statement_from_raw`,
  `market_data_from_raw`, ya existentes desde la Fase 1): tarea separada
  y posterior ("Implementar la consulta de métricas clave... para cada
  empresa par").
- **La transformación del payload crudo al modelo de dominio
  "Comparables"**: corresponde a investmentops.data_layer (ver TASKS.md,
  Fase 5, "Normalización").
- **El cacheo de resultados**: tarea separada y posterior de la misma
  sección de "Normalización".

## Forma del payload crudo

FMP devuelve, para `/v4/stock_peers?symbol=<ticker>`, una lista con (a lo
sumo) un único elemento: ``[{"symbol": "AAPL", "companyName": "...",
"peersList": ["MSFT", "GOOG", ...]}]``. Este módulo no interpreta esa
forma ni extrae `peersList`: `payload` conserva la respuesta cruda tal
cual, igual criterio que `FMPNewsProvider.fetch` (el `payload` es la
lista cruda devuelta por FMP, sin seleccionar ni transformar campos) y
que `FMPFundamentalsProvider.fetch` (el payload combina las respuestas
crudas de sus endpoints, sin normalizar). Interpretar `peersList` (y
manejar el caso de una lista vacía cuando FMP no encuentra pares) es
responsabilidad de la capa de normalización, tarea posterior.

Fuera de alcance de este módulo:
- Cualquier transformación del payload crudo al modelo de dominio
  "Comparables": responsabilidad de investmentops.data_layer (tarea
  posterior, ver TASKS.md, "Normalización").
- El cacheo de resultados (ver TASKS.md, "Normalización" > "Implementar
  el guardado de comparables normalizados en la caché local...").
- Reintentos automáticos o backoff ante fallos transitorios.
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

DEFAULT_BASE_URL = "https://financialmodelingprep.com/api/v4"

#: Ruta del endpoint de comparables/pares de FMP (ver
#: COMPARABLES_PROVIDER.md).
PEERS_ENDPOINT = "/stock_peers"


class FMPComparablesProvider:
    """Cliente mínimo de FMP que cumple el contrato `DataProvider` para comparables.

    Ver investmentops.data_providers.contracts.DataProvider: cualquier
    objeto con un método `fetch(ticker) -> RawProviderData` cumple el
    contrato de forma estructural (`Protocol`), sin necesidad de heredar
    de una clase base. Esta clase es una implementación concreta de ese
    contrato para el proveedor de comparables elegido en la Fase 5 (FMP,
    ver `investmentops/data_providers/COMPARABLES_PROVIDER.md`).
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
            API key de FMP para comparables. Si no se indica, se intenta
            leer desde `config.local.toml`, sección
            `[data_providers.comparables]` (ver CONFIGURATION.md y
            COMPARABLES_PROVIDER.md, "Configuración"). Esta sección es
            deliberadamente distinta de `[data_providers.fundamentals]`,
            aunque ambas apunten hoy al mismo proveedor externo (FMP).
        base_url:
            URL base de la API de FMP. Si no se indica, se intenta leer
            desde la misma sección de configuración; si tampoco está ahí,
            se usa `DEFAULT_BASE_URL` (la URL base de la API v4 de FMP,
            distinta de la v3 usada por `FMPFundamentalsProvider`/
            `FMPNewsProvider`, ya que `/stock_peers` es un endpoint v4).
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
            comparables_cfg = cfg.get("data_providers", {}).get("comparables", {})
            api_key = api_key or comparables_cfg.get("api_key")
            base_url = base_url or comparables_cfg.get("base_url")

        if not api_key:
            raise DataProviderError(
                "Falta la API key del proveedor de comparables (FMP). "
                "Configúrala en config.local.toml, sección "
                "[data_providers.comparables] (ver CONFIGURATION.md)."
            )

        self._api_key = api_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout

    def fetch(self, ticker: str) -> RawProviderData:
        """Obtiene la lista cruda de empresas pares de una empresa desde FMP.

        Consulta el endpoint `/stock_peers` de FMP para `ticker`, y
        devuelve la respuesta cruda tal como la entrega FMP (sin
        transformar), junto con los metadatos de procedencia de esta
        consulta (fuente, fecha/hora, confiabilidad).

        Parameters
        ----------
        ticker:
            Identificador de la empresa a consultar (ej. ``"AAPL"``). Se
            normaliza a mayúsculas, mismo criterio ya usado por
            `FMPFundamentalsProvider.fetch`/`FMPNewsProvider.fetch`.

        Returns
        -------
        RawProviderData
            `payload` es la respuesta cruda devuelta por FMP para
            `/stock_peers` (una lista, típicamente con un único elemento
            que incluye `"peersList"`), sin modificar. Una lista vacía es
            una respuesta válida (FMP no encontró pares para el ticker),
            no un error: interpretar esa ausencia es responsabilidad de
            la capa de normalización (tarea posterior).

        Raises
        ------
        DataProviderError
            Si el ticker está vacío, si FMP no responde (error de red),
            si la API key es inválida, si FMP responde con un error HTTP,
            o si la respuesta no se puede interpretar como JSON. Nunca
            deja escapar una excepción específica de `requests` sin
            traducir.
        """
        if not ticker or not ticker.strip():
            raise DataProviderError("El ticker no puede estar vacío.")

        ticker = ticker.strip().upper()

        url = f"{self._base_url}{PEERS_ENDPOINT}"
        params: dict[str, Any] = {"symbol": ticker, "apikey": self._api_key}

        try:
            response = requests.get(url, params=params, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DataProviderError(
                f"No se pudo contactar a FMP (comparables) para el ticker "
                f"'{ticker}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise DataProviderError(
                "FMP rechazó la solicitud de comparables (API key "
                "inválida o sin permisos para este recurso)."
            )
        if response.status_code == 404:
            payload: Any = []
        elif response.status_code >= 400:
            raise DataProviderError(
                f"FMP respondió con un error ({response.status_code}) al "
                f"consultar comparables para el ticker '{ticker}'."
            )
        else:
            try:
                payload = response.json()
            except ValueError as exc:
                raise DataProviderError(
                    "FMP devolvió una respuesta que no se pudo "
                    f"interpretar como JSON al consultar comparables "
                    f"para el ticker '{ticker}'."
                ) from exc

        if payload is None:
            payload = []

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)