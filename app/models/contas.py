"""Modelo de conta para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Literal


@dataclass
class Conta:
    """Modelo de conta representando uma conta financeira.

    Atributos:
        conta_id: Identificador único da conta (string UUID).
        user_id: Proprietário da conta (string UUID).
        nome: Nome/rótulo da conta.
        tipo: Tipo de conta (corrente, poupanca, investimento, carteira).
        saldo: Saldo atual da conta.
        moeda: Código da moeda (ex.: BRL, USD, EUR).
        criado_em: Data/hora de criação da conta.
        atualizado_em: Data/hora da última atualização da conta.
        ativa: Se a conta está ativa.
    """

    conta_id: str
    user_id: str
    nome: str
    tipo: Literal["corrente", "poupanca", "investimento", "carteira"]
    saldo: Decimal
    moeda: str
    criado_em: datetime
    atualizado_em: datetime
    ativa: bool

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Conta para um dicionário.

        Retorna:
            Representação em dicionário do objeto Conta com timestamps em formato ISO
            e valores decimais como strings.
        """
        data: Dict[str, Any] = asdict(self)
        data["criado_em"] = self.criado_em.isoformat()
        data["atualizado_em"] = self.atualizado_em.isoformat()
        data["saldo"] = str(self.saldo)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Conta":
        """Cria uma instância de Conta a partir de um dicionário.

        Args:
            data: Dicionário contendo dados da conta.

        Retorna:
            Instância de Conta criada a partir do dicionário fornecido.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        if isinstance(data_copy.get("atualizado_em"), str):
            data_copy["atualizado_em"] = datetime.fromisoformat(data_copy["atualizado_em"])
        if isinstance(data_copy.get("saldo"), str):
            data_copy["saldo"] = Decimal(data_copy["saldo"])
        return cls(**data_copy)
