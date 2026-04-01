"""
Modelo de snapshot para snapshots da cadeia de auditoria baseados em Árvore de Merkle.

Um snapshot captura o estado de todo o log de auditoria de um usuário em um ponto no tempo,
construindo uma Árvore de Merkle sobre todos os registros de auditoria atuais e armazenando
o hash raiz. Isso fornece um resumo compacto e à prova de adulteração que pode ser usado
posteriormente para detectar qualquer modificação retroativa do histórico de auditoria.
"""

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class Snapshot:
    """
    Representa um snapshot periódico da Árvore de Merkle da cadeia de auditoria.

    Atributos:
        snapshot_id: Identificador único deste snapshot (string UUID).
        user_id: Usuário cujos registros de auditoria foram capturados no snapshot.
        merkle_root: Hash raiz da Árvore de Merkle construída sobre todos os registros de auditoria.
        total_registros: Número de registros de auditoria incluídos no snapshot.
        audit_ids: Lista ordenada de audit_ids incluídos (define a ordem das folhas na árvore).
        criado_em: Timestamp ISO de quando o snapshot foi criado.
        intervalo_horas: Intervalo agendado (horas) que disparou este snapshot.
        status: 'ok' se a cadeia estava íntegra no momento do snapshot, 'corrompido' caso contrário.
        detalhes: Metadados extras opcionais (ex.: profundidade da árvore, erros).
    """

    snapshot_id: str
    user_id: str
    merkle_root: str
    total_registros: int
    audit_ids: List[str]
    criado_em: datetime
    intervalo_horas: int
    status: str = "ok"
    detalhes: Optional[Dict[str, Any]] = field(default=None)

    def to_dict(self) -> Dict[str, Any]:
        """Converte a instância de Snapshot para um dicionário compatível com DynamoDB."""
        data: Dict[str, Any] = asdict(self)
        data["criado_em"] = self.criado_em.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Snapshot":
        """
        Cria uma instância de Snapshot a partir de um dicionário (ex.: do DynamoDB).

        Args:
            data: Dicionário contendo campos do snapshot.

        Retorna:
            Instância de Snapshot.
        """
        data_copy = data.copy()
        if isinstance(data_copy.get("criado_em"), str):
            data_copy["criado_em"] = datetime.fromisoformat(data_copy["criado_em"])
        # DynamoDB pode retornar listas como listas Python comuns; garantir o tipo
        if not isinstance(data_copy.get("audit_ids"), list):
            data_copy["audit_ids"] = []
        return cls(**data_copy)
