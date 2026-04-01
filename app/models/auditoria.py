"""Modelo de auditoria para aplicação de gestão financeira."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, Literal


@dataclass
class Auditoria:
    """Modelo de auditoria representando um registro de log de auditoria.

    Atributos:
        audit_id: Identificador único do registro de auditoria (string UUID).
        user_id: Usuário que realizou a ação (string UUID).
        transacao_id: Transação afetada pela ação (string UUID).
        acao: Tipo de ação (criacao, modificacao, delecao).
        dados_anteriores: Dados anteriores antes da ação (opcional).
        dados_novos: Novos dados após a ação.
        hash_registro: Hash do registro de auditoria para integridade.
        criado_em: Data/hora de criação do registro de auditoria.
        ip_address: Endereço IP do usuário que realizou a ação (opcional).
    """

    audit_id: str
    user_id: str
    transacao_id: str
    acao: Literal["criacao", "modificacao", "delecao"]
    dados_anteriores: Optional[Dict[str, Any]]
    dados_novos: Dict[str, Any]
    hash_registro: str
    criado_em: datetime
    ip_address: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Auditoria para um dicionário.

        Retorna:
            Representação em dicionário do objeto Auditoria com timestamps em formato ISO.
        """
        data: Dict[str, Any] = asdict(self)
        data["criado_em"] = self.criado_em.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Auditoria":
        """Cria uma instância de Auditoria a partir de um dicionário.

        Args:
            data: Dicionário contendo dados de auditoria.

        Retorna:
            Instância de Auditoria criada a partir do dicionário fornecido.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        return cls(**data_copy)
