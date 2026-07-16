"""Orquestador mínimo — disparo de la consulta al proveedor de datos, paso
de esos datos crudos a la capa de normalización, invocación secuencial de
los agentes de análisis, y ensamblado del "Resultado de investigación"
final.

Cubre cuatro tareas de TASKS.md, Fase 1, "Orquestador mínimo":

- "Implementar la función que recibe un ticker y dispara la consulta al
  proveedor de Fase 1." (`fetch_raw_data`, ya completada en una
  conversación anterior, ver PROGRESS.md).
- "Implementar el paso de datos crudos a la capa de normalización."
  (`fetch_and_normalize`, ya completada en una conversación anterior, ver
  PROGRESS.md).
- "Implementar la invocación secuencial de los dos agentes de análisis
  (salud financiera, valoración) sobre el modelo normalizado."
  (`run_analysis_engines`, ya completada en una conversación anterior, ver
  PROGRESS.md).
- "Implementar el ensamblado de ambos resultados en un 'Resultado de
  investigación' único." (`assemble_research_result`, esta tarea).

Las cuatro funciones viven en el mismo módulo porque son piezas
consecutivas del mismo pipeline descrito en ARCHITECTURE.md ("Resumen
del flujo de una investigación", pasos 3-6): el orquestador consulta la
fuente de datos, pasa esos datos crudos a la capa de normalización, pasa
el modelo normalizado a los motores de análisis, y finalmente ensambla
los resultados de todos los análisis en un único "Resultado de
investigación".

## Ensamblado del "Resultado de investigación"

`assemble_research_result` traduce la lista de `AnalysisResult` que
produce `run_analysis_engines` (más el `ticker` investigado) a un
`ResearchResult` (ver `investmentops.core.research_result`), el tipo que
consumirán los generadores de reportes en la Fase 2.

### La `Company` de este `ResearchResult`

`ResearchResult.company` exige un `investmentops.data_layer.Company`
completo (`ticker`, `name`, `sector`, `market`), pero **ningún** dato
normalizado disponible hoy (`NormalizedCompanyData`, es decir
`FinancialStatement`/`MarketData`) expone nombre, sector o mercado de la
empresa: ni el payload crudo de `FMPFundamentalsProvider` (estado de
resultados, balance, cotización) ni la capa de normalización
(`investmentops.data_layer.normalization`) capturan esos campos, porque
no forman parte de los modelos "Estados financieros normalizados" ni
"Datos de mercado" definidos en la Fase 1 (ver ARCHITECTURE.md, "Modelo
de datos interno").

Ante esta ausencia, se decide construir una `Company` **mínima**, con
solo el `ticker` recibido (normalizado a mayúsculas, mismo criterio ya
usado por `FMPFundamentalsProvider.fetch` y por la caché local), dejando
`name`, `sector` y `market` como cadenas vacías (`""`). `Company` no
impone que estos campos sean no vacíos (son `str` de texto libre, ver
`investmentops/data_layer/domain.py`), por lo que esto es válido
estructuralmente. Se prefiere esto a:

- **Inventar valores** (ej. buscar el nombre en otra fuente no
  contemplada en el MVP): violaría el principio de
  `ARCHITECTURE.md`/`GOALS.md` de no inventar datos que no se tienen.
- **Hacer `name`/`sector`/`market` opcionales (`str | None`)** en el
  modelo de dominio `Company`: cambiaría un contrato ya definido y usado
  en otras partes del sistema (`investmentops/data_layer/domain.py`, ya
  probado en `test_data_layer_domain.py`) por una razón que no aplica a
  ese módulo en sí (el modelo de dominio es correcto; lo que falta es la
  *fuente* de esos datos), lo cual sería un rediseño no justificado por
  esta tarea puntual.

Completar `name`/`sector`/`market` con datos reales (ej. sumando un
endpoint de perfil de empresa al proveedor de datos fundamentales) queda
fuera de esta tarea — ver "Fuera de alcance" más abajo.

### Fallos parciales

`assemble_research_result` acepta un parámetro `failures` opcional
(por defecto una lista vacía). Esta tarea **no** implementa la lógica
que detecta y captura fallos parciales de la fuente de datos o de los
agentes de análisis (eso es, de forma explícita, la tarea siguiente de
esta misma sección de TASKS.md: "Implementar el manejo de fallo del
proveedor de datos o del proveedor de IA sin detener el resto del
flujo..."); solo deja el parámetro listo para que esa tarea futura
pueda pasarle la lista de `ResearchFailure` que detecte, sin tener que
modificar la firma de esta función.

### Fecha de ensamblado

`generated_at` es opcional; si no se indica, se usa
`datetime.now(timezone.utc)` en el momento de la llamada. Es distinta de
`AnalysisProvenance.generated_at` de cada análisis individual (que
registra cuándo se generó esa interpretación puntual): `generated_at`
aquí es la fecha en que el orquestador ensambló el resultado final,
conforme a `investmentops.core.research_result.ResearchResult`.

Fuera de alcance de este módulo (aún):
- Detectar/capturar fallos parciales de `fetch_and_normalize` o
  `run_analysis_engines` y traducirlos a `ResearchFailure`: tarea
  siguiente de esta misma sección de TASKS.md.
- Completar `Company.name`/`sector`/`market` con datos reales: no hay
  hoy una fuente de datos que los provea (ver más arriba).
- Una función que encadene `fetch_and_normalize` → `run_analysis_engines`
  → `assemble_research_result` en una sola llamada de punta a punta: no
  es parte del texto de esta tarea ("ensamblar ambos resultados"), y
  además el manejo de fallos parciales (tarea siguiente) probablemente
  necesite envolver justo esa cadena; introducirla ahora se adelantaría
  a esa tarea.
- Leer o escribir la caché de datos normalizados
  (investmentops.data_layer.cache): fuera de alcance, igual que ya se
  documentó para `fetch_raw_data`/`fetch_and_normalize`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Sequence

from investmentops.analysis_engines.contracts import AnalysisResult
from investmentops.analysis_engines.financial_health import analyze_financial_health
from investmentops.analysis_engines.valuation import analyze_valuation
from investmentops.core.research_result import ResearchFailure, ResearchResult
from investmentops.data_layer.domain import Company
from investmentops.data_layer.financial_statements import FinancialStatement
from investmentops.data_layer.market_data import MarketData
from investmentops.data_layer.normalization import (
    financial_statement_from_raw,
    market_data_from_raw,
)
from investmentops.data_providers.contracts import DataProvider, RawProviderData
from investmentops.data_providers.fundamentals import FMPFundamentalsProvider


def fetch_raw_data(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> RawProviderData:
    """Consulta al proveedor de datos fundamentales de Fase 1 para `ticker`.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se pasa
        tal cual al proveedor, que es quien valida/normaliza su formato
        (ver `FMPFundamentalsProvider.fetch`).
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), usada para construir el
        proveedor por defecto si no se indica `provider` explícitamente.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco. Se ignora si `provider` ya se indica.
    provider:
        Proveedor de datos ya construido a usar en vez del proveedor por
        defecto. Cumple el contrato `DataProvider`
        (investmentops.data_providers.contracts). Pensado sobre todo para
        pruebas (inyectar un proveedor mínimo de prueba, ver
        `investmentops/tests/test_data_providers_contracts.py`), pero
        también deja la puerta abierta a que una tarea futura del
        orquestador elija entre varios proveedores sin modificar esta
        función. Si no se indica, se usa `FMPFundamentalsProvider`, el
        proveedor concreto ya elegido para el MVP.

    Returns
    -------
    RawProviderData
        Los datos crudos obtenidos, junto con sus metadatos de
        procedencia (ver `investmentops.data_providers.contracts`).

    Raises
    ------
    DataProviderError
        Si el proveedor no responde, el ticker no existe, o la respuesta
        no se puede interpretar (ver `DataProvider.fetch`). Esta función
        no captura ni traduce esa excepción: el manejo de fallos sin
        detener el resto del flujo es una tarea separada y posterior
        (ver TASKS.md, "Orquestador mínimo").
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml` (ver
        `investmentops.config.load_config`, invocado internamente por
        `FMPFundamentalsProvider` cuando no se le pasan credenciales
        explícitas).
    """
    data_provider = provider if provider is not None else FMPFundamentalsProvider(config=config)
    return data_provider.fetch(ticker)


@dataclass(frozen=True)
class NormalizedCompanyData:
    """Datos normalizados de una empresa, listos para los agentes de análisis.

    Es el tipo de salida de `fetch_and_normalize`: agrupa los dos modelos
    de dominio normalizados que hoy consumen los agentes de análisis ya
    implementados (`investmentops.analysis_engines.financial_health.
    analyze_financial_health` y `...valuation.analyze_valuation`), para
    que quien invoque el orquestador no tenga que manejar dos valores
    sueltos.

    Attributes
    ----------
    financial_statement:
        Estados financieros normalizados de la empresa (ver
        `investmentops.data_layer.FinancialStatement`).
    market_data:
        Datos de mercado normalizados de la misma empresa (ver
        `investmentops.data_layer.MarketData`).
    """

    financial_statement: FinancialStatement
    market_data: MarketData


def fetch_and_normalize(
    ticker: str,
    *,
    config: dict[str, Any] | None = None,
    provider: DataProvider | None = None,
) -> NormalizedCompanyData:
    """Consulta al proveedor de datos y normaliza el resultado para `ticker`.

    Encadena `fetch_raw_data(ticker, ...)` con
    `investmentops.data_layer.normalization.financial_statement_from_raw`
    y `...market_data_from_raw`, de forma que quien invoque esta función
    reciba directamente los modelos de dominio normalizados, sin tener
    que conocer la forma del `payload` crudo que entrega el proveedor de
    datos fundamentales.

    Parameters
    ----------
    ticker:
        Identificador de la empresa a consultar (ej. ``"AAPL"``). Se
        propaga tal cual a `fetch_raw_data`.
    config:
        Configuración ya cargada, propagada a `fetch_raw_data` para
        construir el proveedor por defecto si no se indica `provider`.
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco.
    provider:
        Proveedor de datos ya construido, propagado a `fetch_raw_data`.
        Pensado sobre todo para pruebas (inyectar un proveedor mínimo de
        prueba), sin depender de una llamada de red real.

    Returns
    -------
    NormalizedCompanyData
        Los `FinancialStatement` y `MarketData` normalizados de la
        empresa, listos para pasarse a los agentes de análisis ya
        implementados (`analyze_financial_health`, `analyze_valuation`).

    Raises
    ------
    DataProviderError
        Si `fetch_raw_data` no puede obtener los datos crudos (proveedor
        caído, ticker inexistente, respuesta no interpretable). Ver
        `fetch_raw_data`.
    NormalizationError
        Si los datos crudos obtenidos no traen los campos imprescindibles
        para construir `FinancialStatement` o `MarketData` (ver
        `investmentops.data_layer.normalization`). Esta función no
        captura ni traduce esa excepción: el manejo de fallos sin
        detener el resto del flujo es una tarea separada y posterior
        (ver TASKS.md, "Orquestador mínimo").
    ConfigError
        Si `provider` no se indica, `config` tampoco, y no se puede
        cargar `config.local.toml` (propagado desde `fetch_raw_data`).
    """
    raw = fetch_raw_data(ticker, config=config, provider=provider)
    financial_statement = financial_statement_from_raw(raw)
    market_data = market_data_from_raw(raw)

    return NormalizedCompanyData(
        financial_statement=financial_statement,
        market_data=market_data,
    )


def run_analysis_engines(
    company_data: NormalizedCompanyData,
    *,
    config: dict[str, Any] | None = None,
) -> list[AnalysisResult]:
    """Invoca secuencialmente los agentes de salud financiera y valoración.

    Encadena, en este orden, `analyze_financial_health` (sobre
    `company_data.financial_statement`) y `analyze_valuation` (sobre
    `company_data.market_data` y `company_data.financial_statement`),
    devolviendo los dos `AnalysisResult` obtenidos. Cada agente calcula
    sus propias métricas deterministas internamente (no se le pasan
    precalculadas): esta función no duplica ese cálculo, solo encadena la
    invocación de ambos agentes ya completos.

    Parameters
    ----------
    company_data:
        El `NormalizedCompanyData` de la empresa a analizar (típicamente
        el resultado de `fetch_and_normalize(ticker, ...)`), con el
        `FinancialStatement` y el `MarketData` ya normalizados.
    config:
        Configuración ya cargada (como la que devuelve
        `investmentops.config.load_config`), propagada tal cual a ambos
        agentes para resolver su proveedor de IA configurado (ver
        `investmentops.ai_providers.selection.resolve_agent_provider`).
        Útil para pruebas, para no depender de un `config.local.toml`
        real en disco. Si no se indica, cada agente llama internamente a
        `load_config()`.

    Returns
    -------
    list[AnalysisResult]
        Una lista con exactamente dos elementos, en este orden: el
        resultado del agente de salud financiera
        (`analysis_id="financial_health"`) y el resultado del agente de
        valoración (`analysis_id="valuation"`).

    Raises
    ------
    PromptError
        Si no se puede cargar el archivo de prompt de alguno de los dos
        agentes (ver `investmentops.analysis_engines.prompts.load_prompt`).
    AgentProviderSelectionError
        Si no se puede resolver ningún proveedor de IA para alguno de los
        dos agentes según la configuración.
    AIProviderError
        Si el proveedor de IA resuelto para alguno de los dos agentes no
        tiene una integración concreta implementada, faltan credenciales
        imprescindibles, o la invocación al modelo de lenguaje falla.
    ConfigError
        Si `config` no se indica y no se puede cargar
        `config.local.toml`.

    Notes
    -----
    Esta función no captura ninguna de las excepciones anteriores: si el
    agente de salud financiera falla, el agente de valoración no llega a
    invocarse. Detener el flujo ante un fallo parcial de uno de los dos
    agentes (en vez de continuar con el otro y dejarlo explícito) es, de
    forma deliberada, el comportamiento de esta tarea; capturar esos
    fallos para no detener el resto del flujo es la tarea siguiente de
    esta misma sección de TASKS.md ("Orquestador mínimo").
    """
    financial_health_result = analyze_financial_health(
        company_data.financial_statement, config=config
    )
    valuation_result = analyze_valuation(
        company_data.market_data,
        company_data.financial_statement,
        config=config,
    )

    return [financial_health_result, valuation_result]


def assemble_research_result(
    ticker: str,
    analysis_results: Sequence[AnalysisResult],
    *,
    failures: Sequence[ResearchFailure] = (),
    generated_at: datetime | None = None,
) -> ResearchResult:
    """Ensambla los resultados de análisis de una empresa en un `ResearchResult`.

    Traduce el `ticker` investigado y la lista de `AnalysisResult` ya
    producidos (típicamente el resultado de
    `run_analysis_engines(company_data, ...)`) al tipo "Resultado de
    investigación" (ver `investmentops.core.research_result.ResearchResult`
    y ARCHITECTURE.md, "Modelo de datos interno"), que consumirán los
    generadores de reportes en la Fase 2.

    La `Company` incluida en el resultado es **mínima**: solo lleva el
    `ticker` recibido (normalizado a mayúsculas), con `name`, `sector` y
    `market` vacíos, porque ningún dato normalizado disponible en la Fase
    1 (`FinancialStatement`, `MarketData`) expone esos campos (ver
    docstring del módulo, sección "La `Company` de este
    `ResearchResult`", para la justificación completa de esta decisión).

    Parameters
    ----------
    ticker:
        Identificador de la empresa investigada (ej. ``"AAPL"``). Se
        normaliza a mayúsculas para construir la `Company` del
        resultado, mismo criterio ya usado en
        `FMPFundamentalsProvider.fetch` y en la caché local
        (`investmentops.data_layer.cache`).
    analysis_results:
        Los `AnalysisResult` ya producidos para esta empresa (ej. el
        resultado de `run_analysis_engines(...)`). Se incluyen tal cual,
        sin recalcular ni reinterpretar ningún hallazgo o métrica.
    failures:
        Fallos parciales ya detectados durante la investigación (ver
        `investmentops.core.research_result.ResearchFailure`). Por
        defecto, una lista vacía: esta tarea no implementa la detección
        de fallos parciales (ver "Fuera de alcance" en el docstring del
        módulo); este parámetro solo deja el ensamblado listo para
        recibirlos cuando esa tarea futura los produzca.
    generated_at:
        Fecha y hora de ensamblado de este `ResearchResult`. Si no se
        indica, se usa `datetime.now(timezone.utc)` en el momento de la
        llamada.

    Returns
    -------
    ResearchResult
        El resultado de investigación ensamblado: `company` (mínima, solo
        con `ticker`), `analysis_results` (tal cual se recibieron),
        `failures` (tal cual se recibieron, vacío por defecto) y
        `generated_at`.
    """
    company = Company(ticker=ticker.strip().upper(), name="", sector="", market="")

    return ResearchResult(
        company=company,
        analysis_results=list(analysis_results),
        failures=list(failures),
        generated_at=generated_at if generated_at is not None else datetime.now(timezone.utc),
    )
