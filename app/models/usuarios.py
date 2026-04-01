"""Modelo de usuário para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID


@dataclass
class Usuario:
    """Modelo de usuário representando um usuário no sistema de gestão financeira.

    Atributos:
        user_id: Identificador único do usuário (string UUID).
        nome: Nome completo do usuário.
        email: Endereço de e-mail do usuário.
        senha_hash: Hash da senha para segurança.
        criado_em: Data/hora de criação do usuário.
        atualizado_em: Data/hora da última atualização do usuário.
    """

    user_id: str
    nome: str
    email: str
    senha_hash: str
    criado_em: datetime
    atualizado_em: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Usuario para um dicionário.

        Retorna:
            Representação em dicionário do objeto Usuario com timestamps em formato ISO.
        """
        data: Dict[str, Any] = asdict(self)
        data["criado_em"] = self.criado_em.isoformat()
        data["atualizado_em"] = self.atualizado_em.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Usuario":
        """Cria uma instância de Usuario a partir de um dicionário.

        Args:
            data: Dicionário contendo dados do usuário com timestamps em formato ISO.

        Retorna:
            Instância de Usuario criada a partir do dicionário fornecido.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        if isinstance(data_copy.get("atualizado_em"), str):
            data_copy["atualizado_em"] = datetime.fromisoformat(data_copy["atualizado_em"])
        return cls(**data_copy)
