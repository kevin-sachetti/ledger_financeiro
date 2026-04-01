"""Schemas de conta para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from decimal import Decimal


class ContaCreate(BaseModel):
    """Schema para criação de uma nova conta.

    Atributos:
        nome: Nome/rótulo da conta.
        tipo: Tipo de conta (corrente, poupanca, investimento, carteira).
        saldo_inicial: Saldo inicial da conta.
        moeda: Código da moeda (padrão: BRL).
    """

    nome: str = Field(..., min_length=1, max_length=255)
    tipo: Literal["corrente", "poupanca", "investimento", "carteira"]
    saldo_inicial: float = Field(..., ge=0)
    moeda: str = Field(default="BRL", min_length=3, max_length=3)


class ContaUpdate(BaseModel):
    """Schema para atualização de informações da conta.

    Atributos:
        nome: Nome/rótulo da conta (opcional).
        tipo: Tipo de conta (opcional).
    """

    nome: Optional[str] = Field(None, min_length=1, max_length=255)
    tipo: Optional[Literal["corrente", "poupanca", "investimento", "carteira"]] = None


class ContaResponse(BaseModel):
    """Schema para resposta de conta.

    Atributos:
        conta_id: Identificador único da conta.
        user_id: Proprietário da conta.
        nome: Nome/rótulo da conta.
        tipo: Tipo de conta.
        saldo: Saldo atual da conta.
        moeda: Código da moeda.
        criado_em: Data/hora de criação da conta.
        atualizado_em: Data/hora da última atualização da conta.
        ativa: Se a conta está ativa.
    """

    conta_id: str
    user_id: str
    nome: str
    tipo: Literal["corrente", "poupanca", "investimento", "carteira"]
    saldo: float
    moeda: str
    criado_em: datetime
    atualizado_em: datetime
    ativa: bool
