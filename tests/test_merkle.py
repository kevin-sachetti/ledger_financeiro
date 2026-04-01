"""
Testes unitários para a implementação da Merkle Tree.

Cobre:
- Construção da árvore com diferentes quantidades de folhas
- Cálculo correto do hash raiz
- Geração e verificação de provas de inclusão (Merkle proofs)
- Detecção de adulteração: qualquer modificação altera o hash raiz
- Casos de borda: árvore vazia, 1 folha, número ímpar de folhas
- Propriedades criptográficas do HMAC-SHA256 subjacente

Estes testes são puramente unitários (sem DynamoDB, sem FastAPI) e
validam o núcleo matemático do sistema de integridade.
"""

import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

# Patch de settings antes de importar o módulo
_mock_settings = MagicMock()
_mock_settings.HMAC_SECRET = "test-hmac-secret-key-for-testing"


# ---------------------------------------------------------------------------
# Utilitário auxiliar para recalcular HMAC nos testes sem depender do módulo
# ---------------------------------------------------------------------------

def _hmac_ref(data: str) -> str:
    """Referência independente de HMAC-SHA256 para comparações nos testes."""
    key = b"test-hmac-secret-key-for-testing"
    return hmac.new(key, data.encode("utf-8"), hashlib.sha256).hexdigest()


def _hmac_pair_ref(left: str, right: str) -> str:
    return _hmac_ref(left + right)


# ---------------------------------------------------------------------------
# Fixture que injeta o mock de settings no módulo merkle
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_merkle_settings():
    """
    Injeta settings mock no módulo merkle para todos os testes deste arquivo.
    Garante que a chave HMAC usada nos testes seja previsível e isolada.
    """
    with patch("app.utils.merkle.settings", _mock_settings):
        yield


# ---------------------------------------------------------------------------
# Testes de construção da árvore
# ---------------------------------------------------------------------------

class TestConstrucaoMerkleTree:
    """
    Testes que verificam a construção correta da árvore Merkle para
    diferentes quantidades de folhas.
    """

    def test_arvore_vazia_tem_raiz_nula(self):
        """
        O que faz: Cria uma árvore sem folhas e verifica que não há raiz.
        Por que importa: Uma árvore vazia não deve gerar um hash — isso
                         evitaria confundir "nenhum dado" com "dado vazio hashado".
        O que valida: hash_raiz é None quando não há folhas.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=[])
        assert tree.hash_raiz is None

    def test_arvore_com_uma_folha(self):
        """
        O que faz: Cria uma árvore com exatamente uma folha.
        Por que importa: Caso de borda clássico. A raiz deve ser o HMAC
                         da única folha, sem nenhuma combinação intermediária.
        O que valida: A raiz existe e é o HMAC direto da folha.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=["folha-unica"])
        assert tree.hash_raiz is not None
        assert tree.hash_raiz == _hmac_ref("folha-unica")

    def test_arvore_com_duas_folhas(self):
        """
        O que faz: Constrói árvore com 2 folhas e verifica o hash raiz
                   calculado manualmente.
        Por que importa: Com 2 folhas, a raiz é HMAC(H(A) || H(B)).
                         Verificar manualmente confirma que a implementação
                         segue o algoritmo correto.
        O que valida: O hash raiz bate com o cálculo manual esperado.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=["A", "B"])

        h_a = _hmac_ref("A")
        h_b = _hmac_ref("B")
        expected_root = _hmac_pair_ref(h_a, h_b)

        assert tree.hash_raiz == expected_root

    def test_arvore_com_numero_par_de_folhas(self):
        """
        O que faz: Constrói árvore com 4 folhas (2²) e verifica existência da raiz.
        Por que importa: Número par é o caso base do algoritmo de construção.
                         Garante que o loop de combinação termina corretamente.
        O que valida: A raiz é gerada e a profundidade é 3 (log₂(4) + 1).
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=["a", "b", "c", "d"])
        assert tree.hash_raiz is not None
        assert tree.profundidade == 3  # raiz + 2 níveis internos + folhas = 3

    def test_arvore_com_numero_impar_de_folhas(self):
        """
        O que faz: Constrói árvore com 5 folhas e verifica que não há erro.
        Por que importa: Número ímpar exige duplicar o último nó de cada nível.
                         Um bug nessa lógica causaria IndexError ou raiz incorreta.
        O que valida: A árvore é construída sem exceções e tem raiz válida.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=["a", "b", "c", "d", "e"])
        assert tree.hash_raiz is not None
        assert len(tree.hash_raiz) == 64

    def test_arvore_grande_tem_profundidade_esperada(self):
        """
        O que faz: Constrói árvore com 8 folhas e verifica profundidade = 4.
        Por que importa: A profundidade da árvore é log₂(n) + 1. Com 8 folhas,
                         esperamos 4 níveis. Profundidade errada indica bug
                         no loop de construção.
        O que valida: profundidade == 4 para 8 folhas.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=[str(i) for i in range(8)])
        assert tree.profundidade == 4

    def test_ordem_das_folhas_importa(self):
        """
        O que faz: Compara raízes de árvores com as mesmas folhas em ordens diferentes.
        Por que importa: A Merkle Tree não é um conjunto — é uma sequência ordenada.
                         Reordenar os registros de auditoria deve mudar o hash raiz,
                         detectando manipulações na ordem dos eventos.
        O que valida: Diferentes ordens produzem raízes diferentes.
        """
        from app.utils.merkle import MerkleTree

        tree_ab = MerkleTree(folhas=["A", "B"])
        tree_ba = MerkleTree(folhas=["B", "A"])

        assert tree_ab.hash_raiz != tree_ba.hash_raiz


# ---------------------------------------------------------------------------
# Testes de prova de inclusão (Merkle Proof)
# ---------------------------------------------------------------------------

class TestMerkleProof:
    """
    Testes que verificam a geração e validação de provas de inclusão.

    Uma prova de Merkle permite verificar que um registro específico faz
    parte do conjunto sem precisar acessar todos os outros registros —
    fundamental para auditoria eficiente de grandes conjuntos de dados.
    """

    def test_prova_do_primeiro_elemento(self):
        """
        O que faz: Gera e verifica a prova de inclusão para o índice 0.
        Por que importa: O primeiro elemento é o mais simples de verificar.
                         Se falhar aqui, a lógica de geração de provas está errada.
        O que valida: A prova reconstrói corretamente a raiz a partir da folha 0.
        """
        from app.utils.merkle import MerkleTree, _hmac_sha256

        tree = MerkleTree(folhas=["a", "b", "c", "d"])
        prova = tree.obter_prova(0)

        assert len(prova) > 0, "Prova não deve estar vazia"

        leaf_hash = _hmac_sha256("a")
        valido = MerkleTree.verificar_prova(leaf_hash, prova, tree.hash_raiz)
        assert valido is True

    def test_prova_do_ultimo_elemento(self):
        """
        O que faz: Gera e verifica a prova para o último índice da árvore.
        Por que importa: Elementos na posição direita de um par podem ter
                         a lógica de irmão invertida. Este teste garante que
                         provas para qualquer posição funcionam corretamente.
        O que valida: A prova do índice 3 (em 4 folhas) é válida.
        """
        from app.utils.merkle import MerkleTree, _hmac_sha256

        tree = MerkleTree(folhas=["a", "b", "c", "d"])
        prova = tree.obter_prova(3)

        leaf_hash = _hmac_sha256("d")
        valido = MerkleTree.verificar_prova(leaf_hash, prova, tree.hash_raiz)
        assert valido is True

    def test_prova_de_elemento_do_meio(self):
        """
        O que faz: Verifica a prova para um elemento que não é nem o primeiro
                   nem o último (índice 2 em 5 folhas).
        Por que importa: Elementos intermediários exigem a combinação correta de
                         irmãos da esquerda e da direita. É o caso mais complexo.
        O que valida: A prova é válida para qualquer posição intermediária.
        """
        from app.utils.merkle import MerkleTree, _hmac_sha256

        tree = MerkleTree(folhas=["a", "b", "c", "d", "e"])
        prova = tree.obter_prova(2)

        leaf_hash = _hmac_sha256("c")
        valido = MerkleTree.verificar_prova(leaf_hash, prova, tree.hash_raiz)
        assert valido is True

    def test_prova_com_folha_errada_e_invalida(self):
        """
        O que faz: Tenta verificar a prova do índice 0 usando o hash de outro elemento.
        Por que importa: Um atacante pode tentar usar uma prova legítima com um dado
                         falsificado. A verificação deve rejeitar a combinação incorreta.
        O que valida: verificar_prova retorna False quando o hash da folha não corresponde.
        """
        from app.utils.merkle import MerkleTree, _hmac_sha256

        tree = MerkleTree(folhas=["a", "b", "c", "d"])
        prova = tree.obter_prova(0)

        # Usa o hash de "b" (índice 1) com a prova de índice 0
        hash_errado = _hmac_sha256("b")
        invalido = MerkleTree.verificar_prova(hash_errado, prova, tree.hash_raiz)
        assert invalido is False

    def test_prova_com_raiz_errada_e_invalida(self):
        """
        O que faz: Verifica a prova correta contra uma raiz inválida.
        Por que importa: A raiz armazenada no snapshot é a âncora de confiança.
                         Se a raiz puder ser substituída, toda a segurança cai.
                         A verificação deve rejeitar qualquer raiz não confiável.
        O que valida: verificar_prova retorna False com raiz incorreta.
        """
        from app.utils.merkle import MerkleTree, _hmac_sha256

        tree = MerkleTree(folhas=["a", "b", "c", "d"])
        prova = tree.obter_prova(1)
        leaf_hash = _hmac_sha256("b")

        raiz_falsa = "f" * 64
        invalido = MerkleTree.verificar_prova(leaf_hash, prova, raiz_falsa)
        assert invalido is False

    def test_prova_indice_invalido_retorna_lista_vazia(self):
        """
        O que faz: Solicita prova para um índice fora do range.
        Por que importa: Índices inválidos não devem causar IndexError ou
                         retornar dados incorretos — devem ser tratados graciosamente.
        O que valida: obter_prova retorna lista vazia para índice inválido.
        """
        from app.utils.merkle import MerkleTree

        tree = MerkleTree(folhas=["a", "b"])

        assert tree.obter_prova(-1) == []
        assert tree.obter_prova(99) == []


# ---------------------------------------------------------------------------
# Testes de detecção de adulteração
# ---------------------------------------------------------------------------

class TestDeteccaoAdulteracao:
    """
    Testes que simulam cenários de adulteração e verificam que a Merkle Tree
    detecta as modificações corretamente.

    Este é o conjunto mais crítico: representa o valor de segurança real
    que a Merkle Tree agrega ao sistema de auditoria financeira.
    """

    def test_modificar_qualquer_folha_muda_raiz(self):
        """
        O que faz: Itera por todas as posições de uma árvore de 4 folhas,
                   substituindo cada uma por um valor adulterado, e verifica
                   que o hash raiz muda em todos os casos.
        Por que importa: A garantia mais fundamental da Merkle Tree é que qualquer
                         alteração em qualquer registro é detectável pela raiz.
                         Se uma posição escapar, o sistema tem uma vulnerabilidade.
        O que valida: Adulteração em qualquer posição (0, 1, 2, 3) altera o hash raiz.
        """
        from app.utils.merkle import MerkleTree

        folhas_originais = ["registro-0", "registro-1", "registro-2", "registro-3"]
        tree_original = MerkleTree(folhas=folhas_originais)
        raiz_original = tree_original.hash_raiz

        for i in range(len(folhas_originais)):
            folhas_adulteradas = folhas_originais.copy()
            folhas_adulteradas[i] = "ADULTERADO"

            tree_adulterada = MerkleTree(folhas=folhas_adulteradas)
            assert tree_adulterada.hash_raiz != raiz_original, \
                f"Adulteração na posição {i} não foi detectada pela raiz"

    def test_remover_registro_muda_raiz(self):
        """
        O que faz: Cria uma árvore com N registros, remove um, e verifica
                   que a raiz muda.
        Por que importa: Excluir um registro de auditoria é uma forma comum
                         de ocultar operações fraudulentas. A Merkle Tree deve
                         detectar essa ausência.
        O que valida: Remover um registro altera o hash raiz.
        """
        from app.utils.merkle import MerkleTree

        folhas = ["r1", "r2", "r3", "r4", "r5"]
        tree_completa = MerkleTree(folhas=folhas)

        # Remove o registro do meio
        folhas_sem_r3 = ["r1", "r2", "r4", "r5"]
        tree_incompleta = MerkleTree(folhas=folhas_sem_r3)

        assert tree_completa.hash_raiz != tree_incompleta.hash_raiz

    def test_inserir_registro_extra_muda_raiz(self):
        """
        O que faz: Adiciona um registro extra à lista e compara as raízes.
        Por que importa: Inserir uma transação falsa no histórico (ex: estornar
                         dinheiro para si mesmo) deve ser detectável.
        O que valida: Qualquer inserção de registro produz raiz diferente.
        """
        from app.utils.merkle import MerkleTree

        folhas = ["r1", "r2", "r3"]
        tree_original = MerkleTree(folhas=folhas)

        folhas_com_extra = ["r1", "r2", "r3", "r4-FALSO"]
        tree_com_extra = MerkleTree(folhas=folhas_com_extra)

        assert tree_original.hash_raiz != tree_com_extra.hash_raiz

    def test_reordenar_registros_muda_raiz(self):
        """
        O que faz: Inverte a ordem das folhas e compara as raízes.
        Por que importa: Reordenar eventos de auditoria pode ocultar a sequência
                         real das operações, por exemplo, movendo uma autorização
                         para depois de uma transferência. A árvore deve detectar isso.
        O que valida: A mesma lista em ordem diferente produz raiz diferente.
        """
        from app.utils.merkle import MerkleTree

        folhas = ["r1", "r2", "r3", "r4"]
        tree_original = MerkleTree(folhas=folhas)
        tree_invertida = MerkleTree(folhas=list(reversed(folhas)))

        assert tree_original.hash_raiz != tree_invertida.hash_raiz

    def test_alteracao_minima_no_valor_detectada(self):
        """
        O que faz: Simula adulteração de um registro de auditoria financeiro real —
                   muda o valor de R$100,00 para R$100,01 em um dos registros.
        Por que importa: Este é o ataque mais sutil possível: uma modificação de
                         1 centavo que poderia passar desapercebida em inspeção visual
                         mas representa fraude. A Merkle Tree deve detectá-la.
        O que valida: Alteração de 1 centavo em qualquer registro muda o hash raiz.
        """
        from app.utils.merkle import construir_arvore_auditoria

        registros_originais = [
            {"audit_id": "a1", "valor": 100.00, "acao": "criar"},
            {"audit_id": "a2", "valor": 200.00, "acao": "criar"},
            {"audit_id": "a3", "valor": 300.00, "acao": "criar"},
        ]
        tree_original = construir_arvore_auditoria(registros_originais)

        # Adultera 1 centavo no segundo registro
        registros_adulterados = [
            {"audit_id": "a1", "valor": 100.00, "acao": "criar"},
            {"audit_id": "a2", "valor": 200.01, "acao": "criar"},  # adulterado!
            {"audit_id": "a3", "valor": 300.00, "acao": "criar"},
        ]
        tree_adulterada = construir_arvore_auditoria(registros_adulterados)

        assert tree_original.hash_raiz != tree_adulterada.hash_raiz, \
            "Alteração de R$0,01 deve ser detectada pela Merkle Tree"

    def test_arvore_identica_produz_mesma_raiz(self):
        """
        O que faz: Constrói duas árvores a partir dos mesmos dados e compara raízes.
        Por que importa: Verifica que a função é determinística — sem aleatoriedade
                         nos hashes, o que garantiria reprodutibilidade da verificação.
        O que valida: Duas árvores com os mesmos dados têm a mesma raiz.
        """
        from app.utils.merkle import construir_arvore_auditoria

        registros = [
            {"audit_id": "a1", "valor": 100.0},
            {"audit_id": "a2", "valor": 200.0},
        ]

        tree1 = construir_arvore_auditoria(registros)
        tree2 = construir_arvore_auditoria(registros)

        assert tree1.hash_raiz == tree2.hash_raiz


# ---------------------------------------------------------------------------
# Testes das propriedades criptográficas do HMAC-SHA256
# ---------------------------------------------------------------------------

class TestPropriedadesCriptograficas:
    """
    Testes que verificam as propriedades matemáticas e criptográficas
    do HMAC-SHA256 utilizado internamente pela Merkle Tree.
    """

    def test_hmac_sha256_produz_digest_de_256_bits(self):
        """
        O que faz: Verifica o tamanho do digest HMAC-SHA256.
        Por que importa: 256 bits = 32 bytes = 64 chars hex. Um digest menor
                         indicaria uso de SHA-1 ou MD5, algoritmos fracos.
        O que valida: _hmac_sha256 retorna 64 caracteres hexadecimais.
        """
        from app.utils.merkle import _hmac_sha256

        resultado = _hmac_sha256("dados de teste")
        assert len(resultado) == 64

    def test_hmac_sha256_e_determinístico(self):
        """
        O que faz: Calcula o mesmo HMAC duas vezes e compara.
        Por que importa: Não-determinismo tornaria a verificação impossível.
        O que valida: Dois chamadas com o mesmo dado retornam o mesmo digest.
        """
        from app.utils.merkle import _hmac_sha256

        h1 = _hmac_sha256("dados")
        h2 = _hmac_sha256("dados")
        assert h1 == h2

    def test_hmac_sha256_sensivel_a_qualquer_mudanca(self):
        """
        O que faz: Calcula HMACs para strings que diferem em apenas 1 bit.
        Por que importa: O efeito avalanche garante que bits de saída mudem
                         drasticamente com qualquer bit de entrada diferente.
        O que valida: "dado" e "dado!" produzem digests completamente diferentes.
        """
        from app.utils.merkle import _hmac_sha256

        h1 = _hmac_sha256("dado")
        h2 = _hmac_sha256("dado!")

        assert h1 != h2

    def test_combinacao_de_pares_e_nao_comutativa(self):
        """
        O que faz: Verifica que _hmac_sha256_pair(A, B) ≠ _hmac_sha256_pair(B, A).
        Por que importa: A posição (esquerda/direita) importa na construção da árvore.
                         Se a operação fosse comutativa, trocar a ordem dos irmãos
                         não mudaria a raiz — seria uma vulnerabilidade.
        O que valida: A combinação de hashes não é comutativa.
        """
        from app.utils.merkle import _hmac_sha256_pair

        h_a = "a" * 64
        h_b = "b" * 64

        assert _hmac_sha256_pair(h_a, h_b) != _hmac_sha256_pair(h_b, h_a)
