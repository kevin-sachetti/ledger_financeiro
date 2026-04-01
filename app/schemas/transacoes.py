"""Schemas de transação para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from typing import Any, Optional, Literal


class TransacaoCreate(BaseModel):
    """Schema para criação de uma nova transação.

    Atributos:
        conta_id: Conta onde a transação ocorreu.
        tipo: Tipo de transação (deposito, saque, transferencia).
        valor: Valor da transação.
        descricao: Descrição da transação.
        categoria_id: ID da categoria da transação (opcional).
        conta_destino_id: Conta de destino para transferências (opcional).
        data_transacao: Data em que a transação ocorreu (opcional).
    """

    conta_id: str
    tipo: Literal["deposito", "saque", "transferencia"]
    valor: float = Field(..., gt=0)
    descricao: str = Field(..., min_length=1, max_length=500)
    categoria_id: Optional[str] = None
    conta_destino_id: Optional[str] = None
    data_transacao: Optional[str] = None


class TransacaoResponse(BaseModel):
    """Schema para resposta de transação."""

    model_config = {"extra": "allow"}

    transacao_id: str
    user_id: str
    conta_id: str
    tipo: str
    valor: Any
    descricao: str
    categoria_id: Optional[str] = None
    conta_destino_id: Optional[str] = None
    data_transacao: Optional[str] = None
    criado_em: Optional[str] = None
    hash_atual: Optional[str] = None
    hash_anterior: Optional[str] = None
    status: Optional[str] = None


class AuditoriaResposta(BaseModel):
    """Schema para resposta de registro de auditoria."""

    model_config = {"extra": "allow"}

    user_id: str
    audit_id: str
    transacao_id: str
    acao: str
    dados_anteriores: Any = None
    dados_novos: Any = None
    hash: Optional[str] = None
    criado_em: Optional[str] = None
