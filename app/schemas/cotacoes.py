"""Schemas de cotação para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional


class CotacaoResposta(BaseModel):
    """Schema para resposta de cotação de câmbio.

    Atributos:
        moeda: Código da moeda (USD, EUR, etc.).
        compra: Taxa de compra.
        venda: Taxa de venda.
        data: Data/hora da cotação.
        fonte: Fonte dos dados (BCB PTAX, etc.).
    """

    moeda: str
    compra: float
    venda: float
    data: str
    fonte: str


class CotacaoHistoricoResposta(BaseModel):
    """Schema para resposta de cotação de câmbio histórica.

    Atributos:
        moeda: Código da moeda (USD, EUR, etc.).
        compra: Taxa de compra.
        venda: Taxa de venda.
        data: Data da cotação.
        fonte: Fonte dos dados.
    """

    moeda: str
    compra: float
    venda: float
    data: str
    fonte: str
