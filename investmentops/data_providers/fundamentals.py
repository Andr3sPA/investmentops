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

## Series históricas (Fase 3, "Fuente de datos histórica")

Cubre además dos tareas de TASKS.md, Fase 3, "Fuente de datos histórica":

- "Implementar la consulta de series históricas de ingresos y beneficios
  para un ticker." (ya completada, ver PROGRESS.md).
- "Adjuntar metadatos de procedencia a cada punto de la serie
  histórica." (esta tarea).

Conforme a lo ya investigado y documentado en
`investmentops/data_providers/HISTORICAL_DATA.md`: los mismos dos
endpoints ya usados por `fetch()` para el estado de resultados y el
balance general (`income-statement`, `balance-sheet-statement`) ya
devuelven, de forma nativa, un arreglo con varios periodos históricos —
no se necesita otro endpoint ni otro proveedor.

`fetch_historical(ticker, period="annual", limit=5)` es el método que
consulta esa serie:

- Consulta únicamente `income-statement` y `balance-sheet-statement`
  (no `quote`): conforme a `HISTORICAL_DATA.md`, la Fase 3 se centra
  explícitamente en ingresos y beneficios, no en series de precio de
  mercado.
- Envía `period` y `limit` como parámetros de consulta adicionales,
  junto a `apikey`, reutilizando `_get` (extendido para aceptar
  parámetros extra sin cambiar su comportamiento por defecto: `fetch()`
  sigue enviando únicamente `apikey`, sin `period`/`limit`).
- Devuelve un `RawProviderData` cuyo `payload` conserva **todos** los
  periodos devueltos por FMP (no solo el primero): la responsabilidad de
  descartar o consumir esos periodos adicionales corresponde a la capa
  de normalización (tarea separada y posterior de esta misma sección de
  la Fase 3, "Normalización").
- Señala `DataProviderError` ante ticker vacío, `period` fuera de
  `{"annual", "quarter"}`, `limit` menor a 1, fallos de red/autenticación
  /formato (mismo criterio que `fetch()`), o si FMP no devuelve ningún
  periodo para el ticker.

### Procedencia por punto (esta tarea)

`RawProviderData.metadata` (un único `ProviderMetadata` para toda la
respuesta) ya identifica de dónde y cuándo se obtuvo la consulta
completa, igual que en `fetch()`. Sin embargo, la tarea de TASKS.md pide
explícitamente procedencia **por cada punto** de la serie, no solo a
nivel de la respuesta completa — relevante de cara a la sección
"Normalización" de la Fase 3, que transformará esta serie a un modelo de
dominio temporal y necesitará poder trazar cada periodo individual hasta
su fuente sin depender únicamente del contenedor externo.

Como todos los puntos de una misma llamada a `fetch_historical`
provienen de la misma consulta (mismo proveedor, mismo instante de
consulta), no hay procedencia *distinta* que calcular por punto: lo que
hace esta tarea es hacer esa procedencia explícita en cada elemento de
la serie, en vez de dejarla implícita solo en el metadato de nivel
superior. `_attach_point_provenance` agrega, a cada dict crudo de
`income_statement`/`balance_sheet_statement`, dos claves nuevas:

- `"source"`: el mismo valor que `RawProviderData.metadata.source`
  (``"fmp"``).
- `"queried_at"`: el mismo valor que
  `RawProviderData.metadata.queried_at`, serializado a ISO 8601 (texto),
  consistente con el formato ya usado para fechas en el resto del
  proyecto (ver `investmentops/data_layer/cache.py`, `cached_at`).

No se mutan los dicts originales devueltos por FMP: `_attach_point_provenance`
construye copias nuevas (`{**point, ...}`), de forma que un dict crudo
con una clave `"source"`/`"queried_at"` propia de FMP (no ocurre hoy,
pero por seguridad) no sea sobrescrita de forma sorpresiva para quien
inspeccione el payload — en la práctica, ninguno de los dos endpoints de
FMP consultados devuelve esas claves.

Fuera de alcance de este método (ver TASKS.md, tareas siguientes de esta
misma sección):
- Cualquier transformación al modelo de dominio de series temporales
  (tareas de la sección "Normalización" de la Fase 3), que es quien
  consumirá estas claves de procedencia por punto.

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

# Endpoints consultados por `fetch_historical`: solo ingresos y
# beneficios (ver "Series históricas" en el docstring del módulo). No
# incluye `quote`, ya que la Fase 3 (ROADMAP.md) no cubre series de
# precio de mercado.
_HISTORICAL_ENDPOINTS: dict[str, str] = {
    "income_statement": "/income-statement/{ticker}",
    "balance_sheet_statement": "/balance-sheet-statement/{ticker}",
}

# Valores admitidos para el parámetro `period` de `fetch_historical`,
# consistentes con los valores que acepta la API de FMP para estos
# mismos endpoints (ver HISTORICAL_DATA.md).
_VALID_PERIODS = ("annual", "quarter")


def _attach_point_provenance(
    points: list[dict[str, Any]], metadata: ProviderMetadata
) -> list[dict[str, Any]]:
    """Adjunta procedencia (`source`, `queried_at`) a cada punto de una serie.

    Construye una lista nueva de dicts (no muta `points`), agregando a
    cada elemento las claves `"source"` (`metadata.source`) y
    `"queried_at"` (`metadata.queried_at`, en formato ISO 8601), de forma
    que cada punto individual de la serie histórica quede trazable hasta
    su fuente sin depender únicamente del `ProviderMetadata` de nivel
    superior en `RawProviderData`. Ver "Procedencia por punto" en el
    docstring del módulo.

    Parameters
    ----------
    points:
        Lista de dicts crudos (ej. un elemento por periodo fiscal), tal
        como los devuelve un endpoint de FMP.
    metadata:
        La procedencia de la consulta que obtuvo `points` (mismo
        `ProviderMetadata` que se adjunta a nivel de todo el
        `RawProviderData`).

    Returns
    -------
    list[dict[str, Any]]
        Una copia de `points`, con `"source"`/`"queried_at"` agregados a
        cada elemento.
    """
    return [
        {**point, "source": metadata.source, "queried_at": metadata.queried_at.isoformat()}
        for point in points
    ]


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

    def fetch_historical(
        self,
        ticker: str,
        *,
        period: str = "annual",
        limit: int = 5,
    ) -> RawProviderData:
        """Obtiene series históricas de ingresos y beneficios para `ticker`.

        Consulta los mismos endpoints de estado de resultados y balance
        general ya usados por `fetch()`, pero conservando **todos** los
        periodos devueltos por FMP (no solo el más reciente), y enviando
        explícitamente `period`/`limit` como parámetros de consulta en
        vez de depender de los valores por defecto de FMP. Cada punto de
        la serie devuelta lleva además su propia procedencia (`"source"`,
        `"queried_at"`), ver "Procedencia por punto" en el docstring del
        módulo.

        Parameters
        ----------
        ticker:
            Identificador de la empresa a consultar (ej. ``"AAPL"``).
        period:
            Granularidad de los periodos a solicitar: ``"annual"`` o
            ``"quarter"``. Por defecto, ``"annual"``.
        limit:
            Número máximo de periodos históricos a solicitar. Por
            defecto, ``5``. Debe ser un entero mayor o igual a 1.

        Returns
        -------
        RawProviderData
            Datos crudos con `payload["income_statement"]` y
            `payload["balance_sheet_statement"]` conteniendo el arreglo
            completo de periodos devueltos por FMP (hasta `limit`
            elementos cada uno). Cada elemento de ambas listas incluye,
            además de los campos originales de FMP, las claves
            `"source"` y `"queried_at"` con la procedencia de ese punto
            (la misma para todos los puntos de esta consulta, ver
            docstring del módulo). `RawProviderData.metadata` sigue
            llevando, como hasta ahora, la procedencia de la consulta
            completa.

        Raises
        ------
        DataProviderError
            Si el ticker está vacío, si `period` no es `"annual"` ni
            `"quarter"`, si `limit` es menor a 1, si FMP no responde
            (error de red), si la API key es inválida, o si FMP no
            devuelve ningún periodo para el ticker.
        """
        if not ticker or not ticker.strip():
            raise DataProviderError("El ticker no puede estar vacío.")

        if period not in _VALID_PERIODS:
            raise DataProviderError(
                f"El parámetro 'period' debe ser uno de {_VALID_PERIODS}, "
                f"no {period!r}."
            )

        if limit < 1:
            raise DataProviderError(
                f"El parámetro 'limit' debe ser un entero mayor o igual a 1, "
                f"no {limit!r}."
            )

        ticker = ticker.strip().upper()
        extra_params = {"period": period, "limit": limit}

        raw_series: dict[str, Any] = {
            key: self._get(path_template.format(ticker=ticker), ticker, extra_params)
            for key, path_template in _HISTORICAL_ENDPOINTS.items()
        }

        if not raw_series["income_statement"]:
            raise DataProviderError(
                f"El ticker '{ticker}' no existe o FMP no devolvió datos "
                "históricos para él."
            )

        metadata = ProviderMetadata(
            source="fmp",
            queried_at=datetime.now(timezone.utc),
            reliability="alta",
        )

        payload: dict[str, Any] = {
            key: _attach_point_provenance(points, metadata)
            for key, points in raw_series.items()
        }

        return RawProviderData(ticker=ticker, payload=payload, metadata=metadata)

    def _get(
        self,
        path: str,
        ticker: str,
        extra_params: dict[str, Any] | None = None,
    ) -> Any:
        """Ejecuta una solicitud GET a un endpoint de FMP y devuelve su JSON.

        Traduce cualquier fallo (de red, de autenticación, de formato) a
        `DataProviderError`, conforme al contrato `DataProvider`: nunca
        deja escapar una excepción específica de `requests`.

        Parameters
        ----------
        path:
            Ruta del endpoint a consultar (ya con el ticker interpolado).
        ticker:
            El ticker consultado, usado solo para mensajes de error.
        extra_params:
            Parámetros de consulta adicionales a `apikey` (ej. `period`,
            `limit`, usados por `fetch_historical`). Si no se indica,
            solo se envía `apikey`, comportamiento idéntico al de
            `fetch()` desde la Fase 1.
        """
        url = f"{self._base_url}{path}"
        params: dict[str, Any] = {"apikey": self._api_key}
        if extra_params:
            params.update(extra_params)

        try:
            response = requests.get(url, params=params, timeout=self._timeout)
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
