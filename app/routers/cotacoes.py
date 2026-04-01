"""
Cotacoes router - gerencia cotações de câmbio (dados públicos).

Endpoints:
    GET /dolar - Obter cotação atual do USD
    GET /euro - Obter cotação atual do EUR
    GET /historico - Obter histórico de cotações
"""

from datetime import date
from fastapi import APIRouter, Query, status

from app.schemas.cotacoes import CotacaoResposta, CotacaoHistoricoResposta
from app.services import cotacoes_service as cotacoes_svc

router = APIRouter(prefix="/cotacoes", tags=["Cotações"])


@router.get("/dolar", response_model=CotacaoResposta)
def obter_cotacao_dolar() -> dict:
    """
    Obter cotação atual do USD (Dólar).

    Returns:
        CotacaoResposta: Cotação atual do USD
    """
    cotacao = cotacoes_svc.obter_cotacao_dolar()
    return cotacao


@router.get("/euro", response_model=CotacaoResposta)
def obter_cotacao_euro() -> dict:
    """
    Obter cotação atual do EUR (Euro).

    Returns:
        CotacaoResposta: Cotação atual do EUR
    """
    cotacao = cotacoes_svc.obter_cotacao_euro()
    return cotacao


@router.get("/historico", response_model=list[CotacaoHistoricoResposta])
def obter_historico_cotacoes(
    moeda: str = Query("USD", description="Currency code (USD, EUR, etc.)"),
    data_inicio: date | None = Query(None, description="Start date for historical data"),
    data_fim: date | None = Query(None, description="End date for historical data"),
) -> list:
    """
    Obter histórico de cotações para uma moeda específica.

    Args:
        moeda: Código da moeda (padrão: USD)
        data_inicio: Data de início opcional para o intervalo histórico
        data_fim: Data de fim opcional para o intervalo histórico

    Returns:
        list[CotacaoHistoricoResposta]: Lista de cotações históricas
    """
    historico = cotacoes_svc.obter_historico_cotacoes(
        moeda=moeda,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return historico
