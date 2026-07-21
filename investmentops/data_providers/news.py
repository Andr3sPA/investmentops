# investmentops/data_providers/news.py
"""Cliente mínimo de Financial Modeling Prep (FMP) — datos de noticias.

Cubre las tareas "Implementar el contrato de 'data provider' para noticias
(ticker/nombre de empresa in, lista de eventos crudos out)", "Adjuntar
metadatos de procedencia (fuente, fecha de publicación, fecha de consulta)
a cada noticia cruda" e "Implementar manejo de error si el proveedor de
noticias falla o no devuelve resultados" (TASKS.md, Fase 4, "Fuente de
datos de noticias"), sobre la decisión ya tomada en
`investmentops/data_providers/NEWS_PROVIDER.md`: reutilizar **FMP**, el
mismo proveedor externo ya integrado desde la Fase 1
(`investmentops/data_providers/fundamentals.py`), vía su endpoint
`/v3/stock_news`.

Este módulo implementa el contrato `DataProvider`
(investmentops.data_providers.contracts): recibe un ticker y devuelve
`RawProviderData` (datos crudos + metadatos de procedencia), sin
transformar nada al modelo de dominio interno — esa transformación
("Noticias", modelo de dominio normalizado) es una tarea posterior y
separada (ver TASKS.md, Fase 4, "Normalización").

## Alcance de esta tarea

Cubre el **contrato** (ticker/nombre de empresa como entrada, lista de
eventos crudos como salida, con metadatos de procedencia a nivel de toda
la respuesta), la **procedencia por cada noticia individual**, y ahora el
**manejo de error cuando el proveedor falla o no devuelve resultados**.

### Procedencia por noticia

`RawProviderData.metadata` (un único `ProviderMetadata` para toda la
respuesta) ya identifica de dónde y cuándo se obtuvo la consulta
completa. Esta tarea hace esa procedencia explícita en cada elemento del
`payload`, mismo criterio ya aplicado por `_attach_point_provenance` en
`investmentops/data_providers/fundamentals.py` para la serie histórica
de estados financieros:

- **`source`**: el mismo valor que `RawProviderData.metadata.source`
  (``"fmp"``).
- **`queried_at`**: el mismo valor que
  `RawProviderData.metadata.queried_at`, serializado a ISO 8601 (texto),
  consistente con el resto del proyecto.
- **Fecha de publicación**: ya viene incluida en cada noticia cruda
  como ``"publishedDate"``, tal como la entrega FMP — no hay que
  agregarla, solo conservarla (no se modifica ese campo).

`_attach_news_provenance` construye copias nuevas de cada dict (no muta
las respuestas originales de `response.json()`), igual criterio que
`_attach_point_provenance`.

### Manejo de error: "no devuelve resultados" vs. "falla" (esta tarea)

Dos casos distintos, que esta tarea distingue con cuidado en vez de
tratarlos como el mismo problema:

- **"No devuelve resultados" (lista vacía) NO es un error.** Una empresa
  puede legítimamente no tener noticias recientes según FMP. `fetch`
  sigue devolviendo un `RawProviderData` con `payload == []` en ese caso,
  sin levantar ninguna excepción (ver `test_fetch_treats_empty_list_as_a_valid_response`
  en `investmentops/tests/test_data_providers_news.py`, ya existente).
  Convertir esto en error inventaría un fallo donde no lo hay.
- **"Falla" cubre, desde antes de esta tarea, la falta de respuesta de
  red, autenticación inválida (401/403) y errores de servidor (≥400)**,
  todos ya traducidos a `DataProviderError`.
- **Lo que esta tarea agrega:** el caso en que FMP responde `200` con un
  cuerpo JSON válido mecánicamente (no lanza `ValueError` al parsear),
  pero que **no tiene la forma esperada** (una lista de noticias) — por
  ejemplo, un objeto de error como `{"Error Message": "Invalid API
  KEY"}` (patrón real de FMP ante credenciales inválidas que no siempre
  vienen con un código HTTP de error) o `null`. Sin esta validación, ese
  payload llegaría intacto a `_attach_news_provenance`, que asume que
  cada elemento es un dict iterable de esa forma, y produciría una
  excepción no controlada (`TypeError`) en vez de un `DataProviderError`
  legible, incumpliendo el contrato `DataProvider` (nunca dejar escapar
  una excepción específica sin traducir). Se valida `isinstance(raw_items,
  list)` justo después de parsear el JSON; si no lo es, se levanta
  `DataProviderError` identificando el ticker afectado.

Fuera de alcance de este módulo:
- La transformación del payload crudo (lista de dicts de FMP, ya con
  procedencia por punto) al modelo de dominio "Noticias" normalizado:
  tarea separada y posterior (ver TASKS.md, Fase 4, "Normalización").
- El cacheo de resultados: tarea separada y posterior de la misma
  sección ("Normalización").
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

#: Ruta del endpoint de noticias por ticker de FMP (ver NEWS_PROVIDER.md).
NEWS_ENDPOINT = "/stock_news"

#: Cantidad máxima de noticias a solicitar por consulta, si no se indica
#: explícitamente. FMP acepta un parámetro `limit` sobre este mismo
#: endpoint (mismo patrón ya usado para `period`/`limit` en
#: `FMPFundamentalsProvider.fetch_historical`).
DEFAULT_LIMIT = 50


def _attach_news_provenance(
    items: list[dict[str, Any]], metadata: ProviderMetadata
) -> list[dict[str, Any]]:
    """Adjunta procedencia (`source`, `queried_at`) a cada noticia cruda.

    Construye una lista nueva de dicts (no muta `items`), agregando a
    cada elemento las claves `"source"` (`metadata.source`) y
    `"queried_at"` (`metadata.queried_at`, en formato ISO 8601), de forma
    que cada noticia individual quede trazable hasta su fuente sin
    depender únicamente del `ProviderMetadata` de nivel superior en
    `RawProviderData`. Mismo criterio ya aplicado por
    `_attach_point_provenance` en
    `investmentops.data_providers.fundamentals` para la serie histórica
    de estados financieros.

    La fecha de publicación de cada noticia (``"publishedDate"``, tal
    como la entrega FMP) no se toca: ya viene incluida en cada elemento
    original.

    Parameters
    ----------
    items:
        Lista de dicts crudos (una noticia por elemento), tal como los
        devuelve el endpoint `/stock_news` de FMP. Se asume ya validada
        como lista por quien invoca esta función (ver `fetch`).
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


class FMPNewsProvider:
    """Cliente mínimo de FMP que cumple el contrato `DataProvider` para noticias.

    Ver investmentops.data_providers.contracts.DataProvider: cualquier
    objeto con un método `fetch(ticker) -> RawProviderData` cumple el
    contrato de forma estructural (`Protocol`), sin necesidad de heredar
    de una clase base. Esta clase es una implementación concreta de ese
    contrato para el proveedor de noticias elegido en la Fase 4 (FMP, ver
    `investmentops/data_providers/NEWS_PROVIDER.md`).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        config: dict[str, Any] | None = None,
        timeout: float = 10.0,
        limit: int = DEFAULT_LIMIT,
    ) -> None:
        """Crea el cliente, resolviendo credenciales desde argumentos o config.

        Parameters
        ----------
        api_key:
            API key de FMP para noticias. Si no se indica, se intenta leer
            desde `config.local.toml`, sección `[data_providers.news]`
            (ver CONFIGURATION.md y NEWS_PROVIDER.md, "Configuración").
        base_url:
            URL base de la API de FMP. Si no se indica, se intenta leer
            desde la misma sección de configuración; si tampoco está ahí,
            se usa `DEFAULT_BASE_URL` (la misma URL base ya usada por
            `FMPFundamentalsProvider`).
        config:
            Diccionario de configuración ya cargado (como el que devuelve
            `investmentops.config.load_config`). Útil para pruebas, para
            no depender de un `config.local.toml` real en disco. Si no se
            indica y falta `api_key` o `base_url`, se llama a
            `load_config()` para leer el archivo real.
        timeout:
            Tiempo máximo (segundos) de espera por solicitud HTTP.
        limit:
            Número máximo de noticias a solicitar por consulta, enviado
            como parámetro `limit` a FMP. Por defecto, `DEFAULT_LIMIT`.
        """
        if api_key is None or base_url is None:
            cfg = config if config is not None else load_config()
            news_cfg = cfg.get("data_providers", {}).get("news", {})
            api_key = api_key or news_cfg.get("api_key")
            base_url = base_url or news_cfg.get("base_url")

        if not api_key:
            raise DataProviderError(
                "Falta la API key del proveedor de noticias (FMP). "
                "Configúrala en config.local.toml, sección "
                "[data_providers.news] (ver CONFIGURATION.md)."
            )

        self._api_key = api_key
        self._base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout
        self._limit = limit

    def fetch(self, ticker: str) -> RawProviderData:
        """Obtiene noticias crudas recientes de una empresa desde FMP.

        Consulta el endpoint `/stock_news` de FMP filtrando por `ticker`,
        y devuelve la lista de eventos crudos tal como la entrega FMP
        (sin transformar ni seleccionar campos), con `"source"` y
        `"queried_at"` adjuntados a cada elemento (ver
        `_attach_news_provenance`), junto con los metadatos de
        procedencia de esta consulta a nivel de toda la respuesta.

        Parameters
        ----------
        ticker:
            Identificador de la empresa a consultar (ej. ``"AAPL"``). Se
            normaliza a mayúsculas, mismo criterio ya usado por
            `FMPFundamentalsProvider.fetch`.

        Returns
        -------
        RawProviderData
            `payload` es la lista cruda de noticias devuelta por FMP (uno
            o más dicts con campos como ``symbol``, ``publishedDate``,
            ``title``, ``text``, ``site``, ``url``, más ``"source"`` y
            ``"queried_at"`` adjuntados), sin modificar los campos
            originales. Una lista vacía es una respuesta válida (la
            empresa no tiene noticias recientes según FMP), no un error.

        Raises
        ------
        DataProviderError
            Si el ticker está vacío, si FMP no responde (error de red),
            si la API key es inválida, si FMP responde con un error HTTP,
            si la respuesta no se puede interpretar como JSON, o si el
            JSON devuelto no tiene la forma esperada (una lista de
            noticias) — por ejemplo, un objeto de error de FMP en vez de
            una lista. Nunca deja escapar una excepción específica de
            `requests` ni una excepción no controlada por un formato de
            respuesta inesperado.
        """
        if not ticker or not ticker.strip():
            raise DataProviderError("El ticker no puede estar vacío.")

        ticker = ticker.strip().upper()

        url = f"{self._base_url}{NEWS_ENDPOINT}"
        params: dict[str, Any] = {
            "tickers": ticker,
            "limit": self._limit,
            "apikey": self._api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=self._timeout)
        except requests.RequestException as exc:
            raise DataProviderError(
                f"No se pudo contactar a FMP (noticias) para el ticker "
                f"'{ticker}': {exc}"
            ) from exc

        if response.status_code in (401, 403):
            raise DataProviderError(
                "FMP rechazó la solicitud de noticias (API key inválida o "
                "sin permisos para este recurso)."
            )
        if response.status_code == 404:
            raw_items: Any = []
        elif response.status_code >= 400:
            raise DataProviderError(
                f"FMP respondió con un error ({response.status_code}) al "
                f"consultar noticias para el ticker '{ticker}'."
            )
        else:
            try:
                raw_items = response.json()
            except ValueError as exc:
                raise DataProviderError(
                    "FMP devolvió una respuesta que no se pudo interpretar "
                    f"como JSON al consultar noticias para el ticker "
                    f"'{ticker}'."
                ) from exc

        if raw_items is None:
            raw_items = []

        if not isinstance(raw_items, list):
            raise DataProviderError(
                "FMP devolvió un formato inesperado (se esperaba una lista "
                f"de noticias) al consultar noticias para el ticker "
                f"'{ticker}'."
            )

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        payload = _attach_news_provenance(raw_items, metadata)

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)