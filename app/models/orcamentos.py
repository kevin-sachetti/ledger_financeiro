"""Modelo de orçamento para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any


@dataclass
class Orcamento:
    """Modelo de orçamento representando um orçamento de gastos.

    Atributos:
        orcamento_id: Identificador único do orçamento (string UUID).
        user_id: Proprietário do orçamento (string UUID).
        categoria_id: Categoria à qual o orçamento se aplica (string UUID).
        valor_limite: Valor limite do orçamento.
        mes: Mês do orçamento (1-12).
        ano: Ano do orçamento.
        criado_em: Data/hora de criação do orçamento.
        atualizado_em: Data/hora da última atualização do orçamento.
    """

    orcamento_id: str
    user_id: str
    categoria_id: str
    valor_limite: Decimal
    mes: int
    ano: int
    criado_em: datetime
    atualizado_em: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Orcamento para um dicionário.

        Retorna:
            Representação em dicionário do objeto Orcamento com timestamps em formato ISO
            e valores decimais como strings.
        """
        data: Dict[str, Any] = asdict(self)
        data["criado_em"] = self.criado_em.isoformat()
        data["atualizado_em"] = self.atualizado_em.isoformat()
        data["valor_limite"] = str(self.valor_limite)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Orcamento":
        """Cria uma instância de Orcamento a partir de um dicionário.

        Args:
            data: Dicionário contendo dados do orçamento.

        Retorna:
            Instância de Orcamento criada a partir do dicionário fornecido.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        if isinstance(data_copy.get("atualizado_em"), str):
            data_copy["atualizado_em"] = datetime.fromisoformat(data_copy["atualizado_em"])
        if isinstance(data_copy.get("valor_limite"), str):
            data_copy["valor_limite"] = Decimal(data_copy["valor_limite"])
        return cls(**data_copy)
