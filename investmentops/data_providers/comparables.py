"""Cliente mínimo de Financial Modeling Prep (FMP) — empresas comparables.

Cubre las tareas "Implementar la consulta de comparables (lista de
empresas pares) para un ticker" y "Adjuntar metadatos de procedencia a
los datos de comparables" (TASKS.md, Fase 5, "Fuente de datos de
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

## Alcance de la primera tarea (ya cubierta)

Contrato básico: ticker de entrada, lista cruda de empresas pares
(`payload`, tal como la entrega FMP) de salida, junto con los metadatos
de procedencia de la consulta completa (`ProviderMetadata`, mismo
criterio ya usado por `FMPFundamentalsProvider.fetch`/
`FMPNewsProvider.fetch`). Incluye manejo de error básico (red,
autenticación, errores de servidor, JSON inválido) porque el contrato
`DataProvider` ya exige señalar cualquier fallo mediante
`DataProviderError`, nunca devolviendo datos inventados o parciales.

## Procedencia por empresa par individual (esta tarea)

Cubre la tarea "Adjuntar metadatos de procedencia a los datos de
comparables" (TASKS.md, Fase 5, "Fuente de datos de comparables").
`RawProviderData.metadata` (un único `ProviderMetadata` para toda la
respuesta) ya identifica de dónde y cuándo se obtuvo la consulta
completa. Esta tarea hace esa procedencia explícita en cada elemento del
`payload`, mismo criterio ya aplicado por `_attach_point_provenance`
(`investmentops/data_providers/fundamentals.py`, serie histórica) y
`_attach_news_provenance` (`investmentops/data_providers/news.py`,
noticias):

- **`source`**: el mismo valor que `RawProviderData.metadata.source`
  (``"fmp"``).
- **`queried_at`**: el mismo valor que
  `RawProviderData.metadata.queried_at`, serializado a ISO 8601 (texto).

`_attach_comparables_provenance` construye copias nuevas de cada dict
del payload (no muta las respuestas originales de `response.json()`),
igual criterio que `_attach_point_provenance`/`_attach_news_provenance`.
Como FMP devuelve, para `/stock_peers`, una lista con (a lo sumo) un
único elemento (ver "Forma del payload crudo" más abajo), esta función
opera igual sobre esa lista, sin asumir ni depender de una cantidad fija
de elementos: si en el futuro FMP cambiara esa forma, la función seguiría
funcionando sin cambios.

No se agrega aquí ninguna validación de que `payload` tenga la forma
esperada (a diferencia de `FMPNewsProvider.fetch`, que sí valida
`isinstance(raw_items, list)`): esa validación de "formato inesperado"
no forma parte de las tareas ya definidas para este proveedor en
`TASKS.md`, y añadirla ahora sería alcance no pedido por esta tarea.

## Forma del payload crudo

FMP devuelve, para `/v4/stock_peers?symbol=<ticker>`, una lista con (a lo
sumo) un único elemento: ``[{"symbol": "AAPL", "companyName": "...",
"peersList": ["MSFT", "GOOG", ...]}]``. Este módulo no interpreta esa
forma más allá de adjuntar procedencia a cada elemento: no extrae
`peersList` ni transforma ningún campo (esa extracción ya vive en
`investmentops.core.orchestrator.fetch_peer_tickers`, que sigue leyendo
`payload[0].get("peersList")` sin verse afectado por las claves nuevas
`"source"`/`"queried_at"` agregadas aquí).

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


def _attach_comparables_provenance(
    items: list[dict[str, Any]], metadata: ProviderMetadata
) -> list[dict[str, Any]]:
    """Adjunta procedencia (`source`, `queried_at`) a cada elemento crudo.

    Construye una lista nueva de dicts (no muta `items`), agregando a
    cada elemento las claves `"source"` (`metadata.source`) y
    `"queried_at"` (`metadata.queried_at`, en formato ISO 8601), de forma
    que cada empresa par individual quede trazable hasta su fuente sin
    depender únicamente del `ProviderMetadata` de nivel superior en
    `RawProviderData`. Mismo criterio ya aplicado por
    `_attach_point_provenance` en
    `investmentops.data_providers.fundamentals` y por
    `_attach_news_provenance` en `investmentops.data_providers.news`.

    Parameters
    ----------
    items:
        Lista de dicts crudos, tal como los devuelve el endpoint
        `/stock_peers` de FMP (típicamente un único elemento con
        `"peersList"`, ver "Forma del payload crudo" en el docstring del
        módulo). Puede estar vacía (FMP no encontró pares).
    metadata:
        La procedencia de la consulta que obtuvo `items` (mismo
        `ProviderMetadata` que se adjunta a nivel de todo el
        `RawProviderData`).

    Returns
    -------
    list[dict[str, Any]]
        Una copia de `items`, con `"source"`/`"queried_at"` agregados a
        cada elemento.
    """
    return [
        {**item, "source": metadata.source, "queried_at": metadata.queried_at.isoformat()}
        for item in items
    ]


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
        devuelve la respuesta cruda ya con procedencia adjuntada a cada
        elemento (ver `_attach_comparables_provenance`), junto con los
        metadatos de procedencia de esta consulta a nivel de toda la
        respuesta (fuente, fecha/hora, confiabilidad).

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
            `/stock_peers` (típicamente un único elemento con
            `"peersList"`), con `"source"`/`"queried_at"` agregados a
            cada elemento, sin modificar sus campos originales. Una
            lista vacía es una respuesta válida (FMP no encontró pares
            para el ticker), no un error: interpretar esa ausencia es
            responsabilidad de la capa de normalización (tarea
            posterior).

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
            raw_payload: Any = []
        elif response.status_code >= 400:
            raise DataProviderError(
                f"FMP respondió con un error ({response.status_code}) al "
                f"consultar comparables para el ticker '{ticker}'."
            )
        else:
            try:
                raw_payload = response.json()
            except ValueError as exc:
                raise DataProviderError(
                    "FMP devolvió una respuesta que no se pudo "
                    f"interpretar como JSON al consultar comparables "
                    f"para el ticker '{ticker}'."
                ) from exc

        if raw_payload is None:
            raw_payload = []

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        payload = _attach_comparables_provenance(raw_payload, metadata)

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)