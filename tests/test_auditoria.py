"""
Suíte de testes para a funcionalidade de trilha de auditoria.

Testes para:
- Criação de registro de auditoria em operações de transação
- Recuperação de registros de auditoria
- Verificação de integridade de hash HMAC-SHA256
- Completude da trilha de auditoria
- Detecção de adulteração via validação HMAC
"""

import hashlib
import hmac
import json
import os

import pytest
from datetime import date
from fastapi import status


class TestAuditoriaTransacao:
    """Testes para trilha de auditoria em operações de transação."""

    def test_auditoria_criacao_transacao(self, client, auth_headers, test_account, test_category):
        """Testa se o registro de auditoria é criado quando uma transação é criada."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Salário",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        transacao_id = response.json()["transacao_id"]

        # Obtém a trilha de auditoria da transação
        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert isinstance(auditoria, list)
        assert len(auditoria) > 0
        # A primeira entrada deve ser de criação
        assert any(entry.get("acao") == "criar" for entry in auditoria)

    def test_auditoria_delecao_transacao(self, client, auth_headers, test_account, test_category):
        """Testa se o registro de auditoria é criado quando uma transação é deletada."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 300.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        # Deleta a transação
        response = client.delete(f"/transacoes/{transacao_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Obtém a trilha de auditoria
        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert any(entry.get("acao") == "deletar" for entry in auditoria)

    def test_auditoria_contem_timestamp(self, client, auth_headers, test_account, test_category):
        """Testa se a entrada de auditoria inclui timestamp."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 200.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert len(auditoria) > 0
        entry = auditoria[0]
        assert "criado_em" in entry

    def test_auditoria_contem_usuario(self, client, auth_headers, test_account, test_category):
        """Testa se a entrada de auditoria inclui informações do usuário."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 150.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert len(auditoria) > 0
        entry = auditoria[0]
        assert "user_id" in entry

    def test_auditoria_contem_detalhes_alteracao(self, client, auth_headers, test_account, test_category):
        """Testa se a entrada de auditoria inclui detalhes da alteração."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert len(auditoria) > 0
        entry = auditoria[0]
        assert "dados_novos" in entry


class TestListarAuditoria:
    """Testes para o endpoint de listagem da trilha de auditoria."""

    def test_listar_auditoria_vazia(self, client, auth_headers):
        """Testa a listagem da trilha de auditoria quando nenhuma operação ocorreu."""
        response = client.get("/transacoes/auditoria/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    def test_listar_auditoria_multiplas_operacoes(self, client, auth_headers, test_account, test_category):
        """Testa a listagem da trilha de auditoria com múltiplas operações."""
        for i in range(3):
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 100.00 * (i + 1),
                "descricao": f"Transação {i + 1}",
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        response = client.get("/transacoes/auditoria/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 3

    def test_listar_auditoria_sem_autenticacao(self, client):
        """Testa se a listagem da trilha de auditoria sem autenticação retorna 401."""
        response = client.get("/transacoes/auditoria/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obter_auditoria_transacao_nao_encontrada(self, client, auth_headers):
        """Testa se obter a trilha de auditoria de uma transação inexistente retorna 404."""
        response = client.get(
            "/transacoes/auditoria/transacao-inexistente", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_obter_auditoria_sem_autenticacao(self, client, auth_headers, test_account, test_category):
        """Testa se obter a trilha de auditoria sem autenticação retorna 401."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(f"/transacoes/auditoria/{transacao_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestIntegridadeAuditoria:
    """Testes para integridade e consistência da trilha de auditoria."""

    def test_auditoria_completude(self, client, auth_headers, test_account, test_category):
        """Testa se a trilha de auditoria é completa e sequencial."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 250.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert len(auditoria) >= 1

    def test_auditoria_nao_pode_ser_alterada(self, client, auth_headers, test_account, test_category):
        """Testa se criar outra transação não altera a auditoria da primeira transação."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 175.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        initial_count = len(response.json())

        # Cria outra transação
        transacao_data2 = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 50.00,
            "descricao": "Teste 2",
        }
        client.post("/transacoes", json=transacao_data2, headers=auth_headers)

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        final_count = len(response.json())
        assert initial_count == final_count

    def test_auditoria_inclui_ids_corretos(self, client, auth_headers, test_account, test_category):
        """Testa se a trilha de auditoria inclui os IDs corretos de transação e usuário."""
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 120.00,
            "descricao": "Teste",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()

        for entry in auditoria:
            assert entry.get("transacao_id") == transacao_id
            assert "user_id" in entry


# ---------------------------------------------------------------------------
# Testes HMAC-SHA256 — validação da função de hashing com chave secreta
# ---------------------------------------------------------------------------

class TestHmacSha256Seguranca:
    """
    Testes unitários para a função gerar_hash_transacao usando HMAC-SHA256.

    O HMAC (Hash-based Message Authentication Code) combina o dado com uma
    chave secreta, garantindo que apenas quem conhece a chave pode gerar ou
    verificar o hash. Isso impede a falsificação de registros de auditoria
    mesmo que o banco de dados seja comprometido.
    """

    def test_hash_gerado_e_determinístico(self):
        """
        O que faz: Gera o mesmo HMAC duas vezes com dados idênticos.
        Por que importa: Sem determinismo, a verificação de integridade seria
                         impossível — o hash recalculado nunca bateria com o salvo.
        O que valida: A função retorna sempre o mesmo digest para a mesma entrada.
        """
        from app.utils.seguranca import gerar_hash_transacao

        dados = {"transacao_id": "abc-123", "valor": 100.0, "acao": "criar"}
        hash1 = gerar_hash_transacao(dados)
        hash2 = gerar_hash_transacao(dados)

        assert hash1 == hash2, "HMAC deve ser determinístico para a mesma entrada"

    def test_hash_e_hexadecimal_de_64_caracteres(self):
        """
        O que faz: Verifica o formato do digest gerado.
        Por que importa: O SHA-256 produz 256 bits = 32 bytes = 64 hex chars.
                         Um digest com tamanho diferente indica implementação errada.
        O que valida: O hash retornado tem exatamente 64 caracteres hexadecimais.
        """
        from app.utils.seguranca import gerar_hash_transacao

        dados = {"transacao_id": "xyz-789", "valor": 50.0}
        hash_val = gerar_hash_transacao(dados)

        assert len(hash_val) == 64, f"HMAC-SHA256 deve ter 64 chars, obteve {len(hash_val)}"
        assert all(c in "0123456789abcdef" for c in hash_val), \
            "Hash deve conter apenas caracteres hexadecimais"

    def test_dados_diferentes_produzem_hashes_diferentes(self):
        """
        O que faz: Gera hashes para duas transações distintas e compara.
        Por que importa: Se dados diferentes gerassem o mesmo hash (colisão),
                         uma transação adulterada pareceria íntegra.
        O que valida: A função é sensível a qualquer variação nos dados de entrada.
        """
        from app.utils.seguranca import gerar_hash_transacao

        dados_a = {"transacao_id": "aaa", "valor": 100.0}
        dados_b = {"transacao_id": "bbb", "valor": 200.0}

        assert gerar_hash_transacao(dados_a) != gerar_hash_transacao(dados_b), \
            "Dados distintos devem produzir HMACs distintos"

    def test_alteracao_minima_muda_hash_completamente(self):
        """
        O que faz: Modifica um único campo numérico e compara os hashes.
        Por que importa: O efeito avalanche do HMAC garante que pequenas mudanças
                         nos dados produzem digests completamente diferentes,
                         tornando ataques de modificação detectáveis.
        O que valida: Alterar 1 centavo no valor muda o hash inteiramente.
        """
        from app.utils.seguranca import gerar_hash_transacao

        dados_original = {"transacao_id": "t-001", "valor": 500.00, "acao": "criar"}
        dados_adulterado = {"transacao_id": "t-001", "valor": 500.01, "acao": "criar"}

        hash_original = gerar_hash_transacao(dados_original)
        hash_adulterado = gerar_hash_transacao(dados_adulterado)

        assert hash_original != hash_adulterado, \
            "Qualquer alteração nos dados deve mudar o HMAC"

    def test_chave_diferente_produz_hash_diferente(self):
        """
        O que faz: Gera HMACs com chaves secretas distintas para o mesmo dado.
        Por que importa: A chave secreta é o que diferencia HMAC de SHA-256 puro.
                         Se a chave não influenciasse o resultado, qualquer atacante
                         poderia recalcular hashes válidos sem conhecer o segredo.
        O que valida: Mudar o HMAC_SECRET altera o digest final.
        """
        import os
        from unittest.mock import patch, MagicMock
        import importlib

        dados = {"transacao_id": "t-001", "valor": 100.0}

        # Hash com chave A
        mock_settings_a = MagicMock()
        mock_settings_a.HMAC_SECRET = "chave-secreta-A"
        with patch("app.utils.seguranca.settings", mock_settings_a):
            import app.utils.seguranca as seg
            hash_a = seg.gerar_hash_transacao(dados)

        # Hash com chave B
        mock_settings_b = MagicMock()
        mock_settings_b.HMAC_SECRET = "chave-secreta-B"
        with patch("app.utils.seguranca.settings", mock_settings_b):
            hash_b = seg.gerar_hash_transacao(dados)

        assert hash_a != hash_b, \
            "Chaves secretas distintas devem produzir HMACs distintos para o mesmo dado"

    def test_verificar_hmac_aceita_hash_correto(self):
        """
        O que faz: Gera um hash e depois verifica com a mesma função de validação.
        Por que importa: O ciclo gerar → verificar é o núcleo da auditoria.
                         Se verificar_hmac_transacao não reconhecesse seu próprio hash,
                         todos os registros seriam marcados como corrompidos.
        O que valida: verificar_hmac_transacao retorna True para um hash legítimo.
        """
        from app.utils.seguranca import gerar_hash_transacao, verificar_hmac_transacao

        dados = {"transacao_id": "t-check", "valor": 250.0, "acao": "criar"}
        hash_gerado = gerar_hash_transacao(dados)

        assert verificar_hmac_transacao(dados, hash_gerado) is True, \
            "verificar_hmac_transacao deve aceitar um hash gerado pela própria função"

    def test_verificar_hmac_rejeita_hash_falsificado(self):
        """
        O que faz: Tenta verificar com um hash inválido (simulando adulteração).
        Por que importa: Um atacante que modifica um registro no banco precisaria
                         também gerar um HMAC válido — impossível sem a chave secreta.
        O que valida: verificar_hmac_transacao retorna False para hash forjado.
        """
        from app.utils.seguranca import verificar_hmac_transacao

        dados = {"transacao_id": "t-forge", "valor": 999.0}
        hash_falso = "a" * 64  # Hash hex válido em formato, mas conteúdo forjado

        assert verificar_hmac_transacao(dados, hash_falso) is False, \
            "verificar_hmac_transacao deve rejeitar um hash falsificado"

    def test_verificar_hmac_rejeita_dados_adulterados(self):
        """
        O que faz: Gera o hash para dados originais e depois verifica com dados alterados.
        Por que importa: Este é o cenário real de ataque: o hash ficou intacto, mas
                         o registro foi modificado. A verificação deve detectar a divergência.
        O que valida: verificar_hmac_transacao retorna False quando os dados não batem.
        """
        from app.utils.seguranca import gerar_hash_transacao, verificar_hmac_transacao

        dados_originais = {"transacao_id": "t-tamper", "valor": 100.0}
        dados_adulterados = {"transacao_id": "t-tamper", "valor": 9999.0}  # adulterado

        hash_original = gerar_hash_transacao(dados_originais)

        # Verifica o hash original contra os dados adulterados → deve falhar
        assert verificar_hmac_transacao(dados_adulterados, hash_original) is False, \
            "HMAC deve detectar adulteração nos dados"

    def test_comparacao_timing_safe(self):
        """
        O que faz: Verifica que a comparação usa hmac.compare_digest (tempo constante).
        Por que importa: Comparações byte-a-byte convencionais permitem ataques de timing:
                         o atacante mede o tempo de resposta para adivinhar o hash
                         caractere por caractere. hmac.compare_digest elimina esse vetor.
        O que valida: O código de verificar_hmac_transacao usa compare_digest internamente.
        """
        import inspect
        from app.utils import seguranca

        # Inspeciona o código-fonte da função de verificação
        source = inspect.getsource(seguranca.verificar_hmac_transacao)
        assert "compare_digest" in source, \
            "verificar_hmac_transacao deve usar hmac.compare_digest para comparação segura"


class TestIntegridadeHmacAuditoria:
    """
    Testes de integração que verificam o HMAC nos registros de auditoria
    salvos no DynamoDB (via moto), cobrindo o ciclo completo da API.
    """

    def test_registro_auditoria_contem_campo_hash(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria uma transação e verifica se o registro de auditoria
                   resultante possui o campo 'hash'.
        Por que importa: Se o campo hash estiver ausente, a verificação de
                         integridade futura não tem base de comparação.
        O que valida: Cada entrada de auditoria inclui o campo 'hash' preenchido.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Salário teste HMAC",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        transacao_id = response.json()["transacao_id"]

        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        auditoria = response.json()
        assert len(auditoria) > 0

        for entrada in auditoria:
            # O campo 'hash' deve existir e ser uma string não vazia
            assert "hash" in entrada, "Entrada de auditoria deve conter campo 'hash'"
            assert isinstance(entrada["hash"], str), "Hash deve ser string"
            assert len(entrada["hash"]) == 64, \
                f"HMAC-SHA256 deve ter 64 chars, obteve {len(entrada['hash'])}"

    def test_verificacao_integridade_cadeia_sem_adulteracao(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria múltiplas transações e chama o endpoint de verificação
                   de integridade da cadeia de auditoria.
        Por que importa: A verificação periódica é a principal defesa contra
                         adulterações retroativas. Deve sempre passar quando
                         nenhuma manipulação ocorreu.
        O que valida: O endpoint reporta que a cadeia está íntegra (integra=True).
        """
        # Cria 3 transações para popular a auditoria
        for i in range(3):
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": float(100 * (i + 1)),
                "descricao": f"Transação HMAC {i + 1}",
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Chama o endpoint de verificação de integridade
        response = client.get(
            "/transacoes/auditoria/verificar-integridade", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        resultado = response.json()

        # A cadeia deve estar íntegra
        assert resultado.get("integra") is True, \
            "A cadeia de auditoria deve estar íntegra antes de qualquer adulteração"
        assert resultado.get("total_registros") >= 3

    def test_adulteracao_direta_no_banco_detectada_via_hmac(
        self, dynamodb_mock, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria uma transação, depois adultera diretamente o registro
                   de auditoria no DynamoDB (bypass da API), e verifica que
                   o endpoint de integridade detecta a adulteração.
        Por que importa: Simula o cenário mais crítico de ataque: um invasor
                         com acesso direto ao banco tenta modificar um registro
                         sem saber a chave HMAC. Como o hash fica inconsistente,
                         a verificação deve falhar.
        O que valida: integra=False quando um hash armazenado é adulterado.
        """
        # Cria uma transação para ter ao menos um registro de auditoria
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 777.00,
            "descricao": "Transação para adulteração",
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        transacao_id = response.json()["transacao_id"]

        # Obtém o registro de auditoria para saber o audit_id
        response = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        auditoria = response.json()
        assert len(auditoria) > 0
        audit_id = auditoria[0]["audit_id"]
        user_id = auditoria[0]["user_id"]

        # --- Adultera diretamente o hash no DynamoDB ---
        # Isso simula um invasor com acesso ao banco, sem a chave HMAC
        table = dynamodb_mock.Table("Auditoria")
        table.update_item(
            Key={"user_id": user_id, "audit_id": audit_id},
            UpdateExpression="SET #h = :h",
            ExpressionAttributeNames={"#h": "hash"},
            ExpressionAttributeValues={":h": "0" * 64},  # hash inválido forjado
        )

        # A verificação de integridade deve detectar a adulteração
        response = client.get(
            "/transacoes/auditoria/verificar-integridade", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        resultado = response.json()

        assert resultado.get("integra") is False, \
            "A verificação deve detectar o hash adulterado como inválido"
        assert len(resultado.get("registros_com_erro", [])) > 0, \
            "Deve listar os registros com hash inválido"
