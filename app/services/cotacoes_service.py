"""
Camada de serviço para gerenciamento de cotações de câmbio.

Este módulo fornece funções para buscar e armazenar em cache cotações de câmbio
atuais e históricas da API PTAX do Banco Central do Brasil (BCB).
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Inicializa caches com TTL de 1 hora
_cache_cotacoes_dolar = TTLCache(maxsize=10, ttl=3600)
_cache_cotacoes_euro = TTLCache(maxsize=10, ttl=3600)
_cache_historico = TTLCache(maxsize=100, ttl=3600)

# URL base da API PTAX do BCB
BCB_PTAX_API_BASE = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"

# Taxas de câmbio de fallback para falhas na API
_FALLBACK_RATES = {
    "USD": {"compra": Decimal("5.20"), "venda": Decimal("5.25")},
    "EUR": {"compra": Decimal("5.70"), "venda": Decimal("5.75")},
}


def _fazer_requisicao_api(url: str) -> dict | None:
    """
    Faz requisição HTTP à API PTAX do BCB com tratamento de erros.

    Args:
        url: URL completa do endpoint da API.

    Returns:
        dict: Resposta JSON da API, ou None se a requisição falhar.
    """
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            return data
    except httpx.RequestError as e:
        logger.error(f"HTTP request error to BCB PTAX API: {str(e)}")
        return None
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP status error from BCB PTAX API: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"JSON decode error from BCB PTAX API: {str(e)}")
        return None


def obter_cotacao_dolar() -> dict:
    """
    Obtém a cotação atual USD para BRL da API PTAX do BCB.

    Busca a cotação mais recente do dólar (preços de compra e venda)
    do Banco Central do Brasil. Resultados são cacheados por 1 hora.

    Returns:
        dict: Cotação com formato:
            {
                "moeda": "USD",
                "compra": Decimal,
                "venda": Decimal,
                "data": str (formato ISO),
                "fonte": "BCB PTAX" ou "fallback"
            }
    """
    # Verifica cache primeiro
    if "USD" in _cache_cotacoes_dolar:
        logger.debug("Returning cached USD exchange rate")
        return _cache_cotacoes_dolar["USD"]

    try:
        # Constrói URL da API para USD na data de hoje
        hoje = datetime.utcnow().date()
        data_str = hoje.strftime("%m-%d-%Y")

        url = (
            f"{BCB_PTAX_API_BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)?"
            f"@dataCotacao='{data_str}'&$format=json"
        )

        data = _fazer_requisicao_api(url)

        if data and "value" in data and len(data["value"]) > 0:
            cotacao = data["value"][0]

            resultado = {
                "moeda": "USD",
                "compra": Decimal(str(cotacao.get("cotacaoCompra", 0))),
                "venda": Decimal(str(cotacao.get("cotacaoVenda", 0))),
                "data": cotacao.get("dataHoraCotacao", datetime.utcnow().isoformat()),
                "fonte": "BCB PTAX",
            }

            # Cacheia o resultado
            _cache_cotacoes_dolar["USD"] = resultado
            logger.info(f"USD exchange rate retrieved: {resultado}")

            return resultado

        else:
            logger.warning("BCB PTAX API returned empty response for USD")
            raise ValueError("Empty API response")

    except Exception as e:
        logger.warning(f"Error fetching USD exchange rate from API: {str(e)}")

        # Retorna taxa de fallback
        resultado = {
            "moeda": "USD",
            "compra": _FALLBACK_RATES["USD"]["compra"],
            "venda": _FALLBACK_RATES["USD"]["venda"],
            "data": datetime.utcnow().isoformat(),
            "fonte": "fallback",
        }

        logger.info(f"Using fallback USD exchange rate: {resultado}")
        return resultado


def obter_cotacao_euro() -> dict:
    """
    Obtém a cotação atual EUR para BRL da API PTAX do BCB.

    Busca a cotação mais recente do euro (preços de compra e venda)
    do Banco Central do Brasil. Resultados são cacheados por 1 hora.

    Returns:
        dict: Cotação com formato:
            {
                "moeda": "EUR",
                "compra": Decimal,
                "venda": Decimal,
                "data": str (formato ISO),
                "fonte": "BCB PTAX" ou "fallback"
            }
    """
    # Verifica cache primeiro
    if "EUR" in _cache_cotacoes_euro:
        logger.debug("Returning cached EUR exchange rate")
        return _cache_cotacoes_euro["EUR"]

    try:
        # Constrói URL da API para EUR na data de hoje
        hoje = datetime.utcnow().date()
        data_str = hoje.strftime("%m-%d-%Y")

        url = (
            f"{BCB_PTAX_API_BASE}/CotacaoMoedaDia(dataCotacao=@dataCotacao,"
            f"moeda=@moeda)?@dataCotacao='{data_str}'&moeda='EUR'&$format=json"
        )

        data = _fazer_requisicao_api(url)

        if data and "value" in data and len(data["value"]) > 0:
            cotacao = data["value"][0]

            resultado = {
                "moeda": "EUR",
                "compra": Decimal(str(cotacao.get("cotacaoCompra", 0))),
                "venda": Decimal(str(cotacao.get("cotacaoVenda", 0))),
                "data": cotacao.get("dataHoraCotacao", datetime.utcnow().isoformat()),
                "fonte": "BCB PTAX",
            }

            # Cacheia o resultado
            _cache_cotacoes_euro["EUR"] = resultado
            logger.info(f"EUR exchange rate retrieved: {resultado}")

            return resultado

        else:
            logger.warning("BCB PTAX API returned empty response for EUR")
            raise ValueError("Empty API response")

    except Exception as e:
        logger.warning(f"Error fetching EUR exchange rate from API: {str(e)}")

        # Retorna taxa de fallback
        resultado = {
            "moeda": "EUR",
            "compra": _FALLBACK_RATES["EUR"]["compra"],
            "venda": _FALLBACK_RATES["EUR"]["venda"],
            "data": datetime.utcnow().isoformat(),
            "fonte": "fallback",
        }

        logger.info(f"Using fallback EUR exchange rate: {resultado}")
        return resultado


def obter_historico_cotacoes(
    moeda: str, data_inicio: str, data_fim: str
) -> list:
    """
    Obtém cotações históricas de uma moeda em um intervalo de datas.

    Busca histórico de cotações da API PTAX do BCB para uma moeda
    e intervalo de datas. Resultados são cacheados por 1 hora.

    Args:
        moeda: Código da moeda ("USD" ou "EUR").
        data_inicio: Data inicial em formato ISO (AAAA-MM-DD).
        data_fim: Data final em formato ISO (AAAA-MM-DD).

    Returns:
        list: Lista de cotações históricas com formato:
            [{
                "moeda": str,
                "compra": Decimal,
                "venda": Decimal,
                "data": str (formato ISO),
                "fonte": "BCB PTAX" ou "fallback"
            }, ...]
            Lista vazia se a consulta falhar.
    """
    cache_key = f"{moeda}_{data_inicio}_{data_fim}"

    # Verifica cache primeiro
    if cache_key in _cache_historico:
        logger.debug(f"Returning cached historical rates for {cache_key}")
        return _cache_historico[cache_key]

    try:
        # Valida entradas
        if moeda not in ("USD", "EUR"):
            logger.warning(f"Unsupported currency for historical query: {moeda}")
            return []

        # Faz parse das datas
        try:
            inicio = datetime.fromisoformat(data_inicio)
            fim = datetime.fromisoformat(data_fim)
        except ValueError as e:
            logger.warning(f"Invalid date format: {str(e)}")
            return []

        # Busca dados históricos da API
        resultado = []
        data_atual = inicio

        while data_atual <= fim:
            # Pula finais de semana (mercado brasileiro fechado)
            if data_atual.weekday() < 5:  # 0-4 are Mon-Fri
                data_str = data_atual.strftime("%m-%d-%Y")

                if moeda == "USD":
                    url = (
                        f"{BCB_PTAX_API_BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)?"
                        f"@dataCotacao='{data_str}'&$format=json"
                    )
                else:  # EUR
                    url = (
                        f"{BCB_PTAX_API_BASE}/CotacaoMoedaDia(dataCotacao=@dataCotacao,"
                        f"moeda=@moeda)?@dataCotacao='{data_str}'&moeda='EUR'&$format=json"
                    )

                data_resposta = _fazer_requisicao_api(url)

                if data_resposta and "value" in data_resposta:
                    for item in data_resposta["value"]:
                        resultado.append(
                            {
                                "moeda": moeda,
                                "compra": Decimal(
                                    str(item.get("cotacaoCompra", 0))
                                ),
                                "venda": Decimal(str(item.get("cotacaoVenda", 0))),
                                "data": item.get(
                                    "dataHoraCotacao",
                                    data_atual.isoformat(),
                                ),
                                "fonte": "BCB PTAX",
                            }
                        )

            data_atual += timedelta(days=1)

        # Cacheia o resultado
        _cache_historico[cache_key] = resultado
        logger.info(
            f"Historical exchange rates retrieved for {moeda} "
            f"({data_inicio} to {data_fim}): {len(resultado)} records"
        )

        return resultado

    except Exception as e:
        logger.error(
            f"Error fetching historical exchange rates: {str(e)}"
        )
        return []


def limpar_cache() -> None:
    """
    Limpa todos os caches de cotações de câmbio.

    Útil para testes ou para forçar atualização das cotações sem esperar
    a expiração do TTL.
    """
    _cache_cotacoes_dolar.clear()
    _cache_cotacoes_euro.clear()
    _cache_historico.clear()
    logger.info("Exchange rate cache cleared")
