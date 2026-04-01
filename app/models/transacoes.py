"""Modelo de transação para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional, Literal


@dataclass
class Transacao:
    """Modelo de transação representando uma transação financeira.

    Atributos:
        transacao_id: Identificador único da transação (string UUID).
        user_id: Proprietário da transação (string UUID).
        conta_id: Conta onde a transação ocorreu (string UUID).
        tipo: Tipo de transação (deposito, saque, transferencia).
        valor: Valor da transação.
        descricao: Descrição da transação.
        categoria_id: ID da categoria da transação (opcional).
        conta_destino_id: Conta de destino para transferências (opcional).
        data_transacao: Data em que a transação ocorreu.
        criado_em: Data/hora de criação da transação.
        hash_atual: Hash atual dos dados da transação.
        hash_anterior: Hash anterior para trilha de auditoria (opcional).
        status: Status da transação (criada, modificada, deletada).
    """

    transacao_id: str
    user_id: str
    conta_id: str
    tipo: Literal["deposito", "saque", "transferencia"]
    valor: Decimal
    descricao: str
    categoria_id: Optional[str]
    conta_destino_id: Optional[str]
    data_transacao: datetime
    criado_em: datetime
    hash_atual: str
    hash_anterior: Optional[str]
    status: Literal["criada", "modificada", "deletada"]

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Transacao para um dicionário.

        Retorna:
            Representação em dicionário do objeto Transacao com timestamps em formato ISO
            e valores decimais como strings.
        """
        data: Dict[str, Any] = asdict(self)
        data["data_transacao"] = self.data_transacao.isoformat()
        data["criado_em"] = self.criado_em.isoformat()
        data["valor"] = str(self.valor)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transacao":
        """Cria uma instância de Transacao a partir de um dicionário.

        Args:
            data: Dicionário contendo dados da transação.

        Retorna:
            Instância de Transacao criada a partir do dicionário fornecido.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("data_transacao"), str):
            data_copy["data_transacao"] = datetime.fromisoformat(data_copy["data_transacao"])
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        if isinstance(data_copy.get("valor"), str):
            data_copy["valor"] = Decimal(data_copy["valor"])
        return cls(**data_copy)
