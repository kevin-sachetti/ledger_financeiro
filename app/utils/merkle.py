"""
Implementação de Árvore Merkle para verificação de integridade de registros de auditoria.

Uma Árvore Merkle é uma árvore binária de hashes criptográficos onde:
- Nós folha contêm hashes HMAC-SHA256 de registros de auditoria individuais.
- Nós internos contêm hashes HMAC-SHA256 da concatenação de seus dois filhos.
- O hash raiz resume todo o conjunto de dados; qualquer registro adulterado altera a raiz.

Esta estrutura permite verificação eficiente e segura de grandes logs de auditoria,
e é o mesmo design utilizado no Bitcoin, Ethereum e em logs de transparência de certificados.
"""

import hashlib
import hmac
import math
from dataclasses import dataclass, field
from typing import List, Optional

from app.config import settings


def _hmac_sha256(data: str) -> str:
    """
    Calcula o HMAC-SHA256 de uma string usando o segredo da aplicação.

    Args:
        data: String UTF-8 para gerar o hash.

    Returns:
        Digest HMAC-SHA256 em hexadecimal.
    """
    chave = settings.HMAC_SECRET.encode("utf-8")
    mac = hmac.new(chave, data.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def _hmac_sha256_pair(left: str, right: str) -> str:
    """
    Combina dois digests hexadecimais e calcula seu HMAC-SHA256.

    Args:
        left: Digest hexadecimal do filho esquerdo.
        right: Digest hexadecimal do filho direito.

    Returns:
        Digest HMAC-SHA256 hexadecimal do par concatenado.
    """
    return _hmac_sha256(left + right)


@dataclass
class NodoMerkle:
    """
    Um único nó na Árvore Merkle.

    Attributes:
        hash: Digest hexadecimal HMAC-SHA256 armazenado neste nó.
        esquerda: Nó filho esquerdo (None para nós folha).
        direita: Nó filho direito (None para nós folha).
        dado: Dado original da folha (definido apenas em nós folha).
    """

    hash: str
    esquerda: Optional["NodoMerkle"] = field(default=None)
    direita: Optional["NodoMerkle"] = field(default=None)
    dado: Optional[str] = field(default=None)

    @property
    def eh_folha(self) -> bool:
        """Retorna True se este nó é uma folha (sem filhos)."""
        return self.esquerda is None and self.direita is None


@dataclass
class MerkleTree:
    """
    Árvore Merkle construída a partir de uma lista de valores de folha em string.

    Attributes:
        folhas: Lista de strings de hash das folhas (HMAC-SHA256 de cada registro).
        raiz: Nó raiz da árvore (None se não houver folhas).
        profundidade: Número de níveis na árvore.
    """

    folhas: List[str] = field(default_factory=list)
    raiz: Optional[NodoMerkle] = field(default=None, init=False)
    profundidade: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Constrói a árvore imediatamente após a inicialização."""
        if self.folhas:
            self._construir()

    def _construir(self) -> None:
        """Constrói a árvore Merkle completa a partir da lista de folhas."""
        # Cria os nós folha
        nos: List[NodoMerkle] = [
            NodoMerkle(hash=_hmac_sha256(folha), dado=folha)
            for folha in self.folhas
        ]

        # Se houver apenas uma folha, ela se torna a raiz diretamente
        if len(nos) == 1:
            self.raiz = nos[0]
            self.profundidade = 1
            return

        self.profundidade = 1
        while len(nos) > 1:
            proxima_camada: List[NodoMerkle] = []

            # Se o número de nós for ímpar, duplica o último (abordagem padrão)
            if len(nos) % 2 != 0:
                nos.append(nos[-1])

            for i in range(0, len(nos), 2):
                esquerda = nos[i]
                direita = nos[i + 1]
                hash_pai = _hmac_sha256_pair(esquerda.hash, direita.hash)
                pai = NodoMerkle(hash=hash_pai, esquerda=esquerda, direita=direita)
                proxima_camada.append(pai)

            nos = proxima_camada
            self.profundidade += 1

        self.raiz = nos[0]

    @property
    def hash_raiz(self) -> Optional[str]:
        """Retorna o hash raiz, ou None se a árvore estiver vazia."""
        return self.raiz.hash if self.raiz else None

    def obter_prova(self, indice: int) -> List[dict]:
        """
        Gera uma prova Merkle para a folha no índice fornecido.

        Uma prova Merkle é o conjunto mínimo de hashes irmãos necessários para
        recalcular o hash raiz a partir de uma única folha, permitindo verificação
        sem revelar o conjunto completo de dados.

        Args:
            indice: Índice base zero da folha alvo.

        Returns:
            Lista de dicts com 'hash' e 'posicao' ('esquerda' | 'direita').
            Retorna uma lista vazia se o índice estiver fora do intervalo.
        """
        if not self.folhas or indice < 0 or indice >= len(self.folhas):
            return []

        prova: List[dict] = []
        nos_nivel: List[NodoMerkle] = [
            NodoMerkle(hash=_hmac_sha256(folha), dado=folha)
            for folha in self.folhas
        ]

        idx = indice
        while len(nos_nivel) > 1:
            if len(nos_nivel) % 2 != 0:
                nos_nivel.append(nos_nivel[-1])

            if idx % 2 == 0:
                # Nó atual é filho esquerdo; irmão está à direita
                if idx + 1 < len(nos_nivel):
                    prova.append({"hash": nos_nivel[idx + 1].hash, "posicao": "direita"})
            else:
                # Nó atual é filho direito; irmão está à esquerda
                prova.append({"hash": nos_nivel[idx - 1].hash, "posicao": "esquerda"})

            # Sobe para o nível pai
            proxima_camada: List[NodoMerkle] = []
            for i in range(0, len(nos_nivel), 2):
                e = nos_nivel[i]
                d = nos_nivel[i + 1]
                proxima_camada.append(
                    NodoMerkle(hash=_hmac_sha256_pair(e.hash, d.hash), esquerda=e, direita=d)
                )
            nos_nivel = proxima_camada
            idx //= 2

        return prova

    @staticmethod
    def verificar_prova(
        hash_folha: str,
        prova: List[dict],
        hash_raiz_esperado: str,
    ) -> bool:
        """
        Verifica uma prova Merkle contra um hash raiz conhecido.

        Args:
            hash_folha: HMAC-SHA256 da folha sendo verificada.
            prova: Lista de hashes irmãos obtidos de obter_prova().
            hash_raiz_esperado: Hash raiz Merkle confiável para verificação.

        Returns:
            True se a prova reconstrói a raiz esperada, False caso contrário.
        """
        hash_atual = hash_folha
        for passo in prova:
            if passo["posicao"] == "direita":
                hash_atual = _hmac_sha256_pair(hash_atual, passo["hash"])
            else:
                hash_atual = _hmac_sha256_pair(passo["hash"], hash_atual)

        return hmac.compare_digest(hash_atual, hash_raiz_esperado)


def construir_arvore_auditoria(registros: List[dict]) -> MerkleTree:
    """
    Constrói uma Árvore Merkle a partir de uma lista de dicionários de registros de auditoria.

    Cada registro é serializado em uma string JSON canônica (chaves ordenadas)
    antes de ser hasheado como folha.

    Args:
        registros: Lista de dicts de registros de auditoria (cada um deve ter ao menos 'audit_id').

    Returns:
        MerkleTree construída a partir dos registros fornecidos.
    """
    import json

    folhas = [
        json.dumps(r, sort_keys=True, default=str)
        for r in registros
    ]
    return MerkleTree(folhas=folhas)
