"""Schemas de orçamento para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class OrcamentoCreate(BaseModel):
    """Schema para criação de um novo orçamento.

    Atributos:
        categoria_id: Categoria à qual o orçamento se aplica.
        valor_limite: Valor limite do orçamento.
        mes: Mês do orçamento (1-12).
        ano: Ano do orçamento.
    """

    categoria_id: str
    valor_limite: float = Field(..., gt=0)
    mes: int = Field(..., ge=1, le=12)
    ano: int = Field(..., ge=2000, le=2100)


class OrcamentoResponse(BaseModel):
    """Schema para resposta de orçamento.

    Atributos:
        orcamento_id: Identificador único do orçamento.
        user_id: Proprietário do orçamento.
        categoria_id: Categoria à qual o orçamento se aplica.
        valor_limite: Valor limite do orçamento.
        mes: Mês do orçamento.
        ano: Ano do orçamento.
        criado_em: Data/hora de criação do orçamento.
        atualizado_em: Data/hora da última atualização do orçamento.
    """

    orcamento_id: str
    user_id: str
    categoria_id: str
    valor_limite: float
    mes: int
    ano: int
    criado_em: datetime
    atualizado_em: datetime


class OrcamentoStatus(BaseModel):
    """Schema para status do orçamento com informações de gastos.

    Atributos:
        orcamento: Detalhes do orçamento.
        valor_gasto: Valor gasto no período do orçamento.
        percentual_utilizado: Percentual do orçamento utilizado (0-100).
    """

    orcamento: OrcamentoResponse
    valor_gasto: float
    percentual_utilizado: float = Field(..., ge=0, le=100)
