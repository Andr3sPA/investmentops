"""Cliente mínimo de Financial Modeling Prep (FMP) — datos de noticias.

Cubre la tarea "Implementar el contrato de 'data provider' para noticias
(ticker/nombre de empresa in, lista de eventos crudos out)" (TASKS.md,
Fase 4, "Fuente de datos de noticias"), sobre la decisión ya tomada en
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

Cubre únicamente el **contrato**: ticker/nombre de empresa como entrada,
lista de eventos crudos (tal como los devuelve FMP, sin modificar) como
salida, con los metadatos de procedencia ya exigidos por
`RawProviderData` (fuente, fecha/hora de consulta, confiabilidad) a nivel
de toda la respuesta. Dos piezas quedan explícitamente para tareas
separadas y posteriores de la misma sección de `TASKS.md`:

- **Metadatos de procedencia por cada noticia cruda** (fecha de
  publicación, además de fuente/fecha de consulta ya presentes a nivel
  de respuesta): tarea siguiente ("Adjuntar metadatos de procedencia...
  a cada noticia cruda"), análoga a `_attach_point_provenance` en
  `fundamentals.py` para la serie histórica.
- **Manejo de error si el proveedor no devuelve resultados** (ej. una
  empresa sin noticias recientes): tarea siguiente y separada
  ("Implementar manejo de error si el proveedor de noticias falla o no
  devuelve resultados"). Por ahora, una lista vacía es una respuesta
  válida (una empresa puede legítimamente no tener noticias recientes),
  no un error — a diferencia de `FMPFundamentalsProvider.fetch`, donde
  una respuesta vacía en todos los endpoints sí distingue "ticker no
  existe". Esta tarea sí traduce fallos de red, autenticación, HTTP y
  formato a `DataProviderError`, porque eso es lo mínimo exigido por el
  contrato `DataProvider` para no dejar escapar excepciones específicas
  de `requests` sin traducir (ver `investmentops/data_providers/contracts.py`).

## Configuración

Lee sus credenciales desde una sección **nueva y separada**,
`[data_providers.news]` (ver `NEWS_PROVIDER.md`, "Configuración"), no
desde `[data_providers.fundamentals]`, aunque ambas secciones apunten
hoy al mismo proveedor externo (FMP). `ProviderMetadata.source` se
identifica igualmente como ``"fmp"`` (el proveedor externo real, mismo
identificador ya usado por `FMPFundamentalsProvider`): lo que cambia
entre ambos clientes es la sección de configuración que cada uno lee,
no el nombre de la fuente.

Fuera de alcance de este módulo:
- La transformación del payload crudo (lista de dicts de FMP) al modelo
  de dominio "Noticias" normalizado: tarea separada y posterior (ver
  TASKS.md, Fase 4, "Normalización").
- El cacheo de resultados: tarea separada y posterior de la misma
  sección ("Normalización").
- Adjuntar procedencia por cada noticia individual y decidir cómo tratar
  una lista de resultados vacía: ver "Alcance de esta tarea" arriba.
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
        (sin transformar ni seleccionar campos), junto con los metadatos
        de procedencia de esta consulta.

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
            ``title``, ``text``, ``site``, ``url``), sin modificar. Una
            lista vacía es una respuesta válida (la empresa no tiene
            noticias recientes según FMP), no un error — ver "Alcance de
            esta tarea" en el docstring del módulo.

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
            payload: Any = []
        elif response.status_code >= 400:
            raise DataProviderError(
                f"FMP respondió con un error ({response.status_code}) al "
                f"consultar noticias para el ticker '{ticker}'."
            )
        else:
            try:
                payload = response.json()
            except ValueError as exc:
                raise DataProviderError(
                    "FMP devolvió una respuesta que no se pudo interpretar "
                    f"como JSON al consultar noticias para el ticker "
                    f"'{ticker}'."
                ) from exc

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)