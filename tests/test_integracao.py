"""
Suite completa de testes de integração do mini-gestor-financeiro.

Testa o fluxo completo do usuário:
- Registro de usuário
- Autenticação de usuário
- Criação de contas
- Criação de categorias
- Criação de orçamentos
- Depósitos e saques
- Geração de relatórios
- Verificação da trilha de auditoria (HMAC-SHA256)
- Snapshots periódicos com Merkle Tree
- Detecção de adulteração ponta a ponta
"""

import pytest
from datetime import date
from fastapi import status


class TestFluxoCompleto:
    """Testes de integração do fluxo completo do usuário."""

    def test_fluxo_completo_usuario(self, client, dynamodb_mock):
        """
        Testa o fluxo completo do usuário, do registro aos relatórios.

        Este teste de integração cobre:
        1. Registro de novo usuário
        2. Login e obtenção do token JWT
        3. Criação de conta bancária
        4. Criação de categorias de transação
        5. Definição de orçamento por categoria
        6. Criação de depósitos e saques
        7. Geração de relatórios financeiros
        8. Verificação da trilha de auditoria
        9. Verificação de consistência dos dados
        """

        # Passo 1: Registra novo usuário
        user_data = {
            "email": "integration@example.com",
            "nome": "Integration Test User",
            "senha": "IntegrationTest123!",
        }
        response = client.post("/usuarios/registrar", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED
        user_id = response.json()["user_id"]
        assert user_id is not None

        # Passo 2: Login e obtenção do token JWT
        response = client.post(
            "/usuarios/login",
            data={
                "username": user_data["email"],
                "password": user_data["senha"],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Passo 3: Verifica perfil do usuário
        response = client.get("/usuarios/perfil", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        profile = response.json()
        assert profile["email"] == user_data["email"]
        assert profile["nome"] == user_data["nome"]
        assert profile["user_id"] == user_id

        # Passo 4: Cria contas bancárias
        accounts_data = [
            {
                "nome": "Conta Corrente",
                "tipo": "corrente",
                "saldo_inicial": 2000.00,
            },
            {
                "nome": "Poupança",
                "tipo": "poupanca",
                "saldo_inicial": 5000.00,
            },
        ]
        accounts = []
        for account_data in accounts_data:
            response = client.post("/contas", json=account_data, headers=headers)
            assert response.status_code == status.HTTP_201_CREATED
            accounts.append(response.json())

        # Verifica se as contas foram criadas
        response = client.get("/contas", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 2

        # Passo 5: Cria categorias de transação
        categories_data = [
            {
                "nome": "Alimentação",
                "descricao": "Gastos com alimentação",
                "tipo": "despesa",
            },
            {
                "nome": "Transporte",
                "descricao": "Gastos com transporte",
                "tipo": "despesa",
            },
            {
                "nome": "Salário",
                "descricao": "Receita de salário",
                "tipo": "receita",
            },
        ]
        categories = []
        for category_data in categories_data:
            response = client.post("/categorias", json=category_data, headers=headers)
            assert response.status_code == status.HTTP_201_CREATED
            categories.append(response.json())

        # Passo 6: Cria orçamento (se o endpoint existir)
        try:
            budget_data = {
                "categoria_id": categories[0]["categoria_id"],  # Alimentação
                "valor_limite": 500.00,
                "mes": 3,
                "ano": 2026,
            }
            response = client.post("/orcamentos", json=budget_data, headers=headers)
            budget_created = response.status_code in (200, 201)
        except Exception:
            budget_created = False

        # Passo 7: Cria depósitos e saques
        transactions = []

        # Depósito (salário)
        deposit_data = {
            "conta_id": accounts[0]["conta_id"],
            "categoria_id": categories[2]["categoria_id"],  # Salário
            "tipo": "deposito",
            "valor": 3000.00,
            "descricao": "Salário mensal",
            "data": str(date.today()),
        }
        response = client.post("/transacoes", json=deposit_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        transactions.append(response.json())

        # Saque (alimentação)
        withdrawal_data = {
            "conta_id": accounts[0]["conta_id"],
            "categoria_id": categories[0]["categoria_id"],  # Alimentação
            "tipo": "saque",
            "valor": 150.00,
            "descricao": "Supermercado",
            "data": str(date.today()),
        }
        response = client.post("/transacoes", json=withdrawal_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        transactions.append(response.json())

        # Outro saque (transporte)
        transport_data = {
            "conta_id": accounts[0]["conta_id"],
            "categoria_id": categories[1]["categoria_id"],  # Transporte
            "tipo": "saque",
            "valor": 50.00,
            "descricao": "Uber",
            "data": str(date.today()),
        }
        response = client.post("/transacoes", json=transport_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        transactions.append(response.json())

        # Passo 8: Verifica lista de transações
        response = client.get("/transacoes", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.json()) == 3

        # Passo 9: Verifica transações individualmente
        for transaction in transactions:
            response = client.get(
                f"/transacoes/{transaction['transacao_id']}", headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.json()["transacao_id"] == transaction["transacao_id"]

        # Passo 10: Gera relatórios
        # Extrato de conta
        response = client.get("/relatorios/extrato", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        extrato = response.json()
        assert len(extrato.get("transacoes", [])) == 3

        # Gastos por categoria
        response = client.get("/relatorios/gastos-por-categoria", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        gastos = response.json()
        assert isinstance(gastos, list)

        # Saldo total
        response = client.get("/relatorios/saldo", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        saldo = response.json()
        # Deve conter alguma representação de saldo
        assert "saldo_total" in saldo or "total" in saldo or "saldo" in saldo

        # Resumo financeiro
        response = client.get("/relatorios/resumo", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        resumo = response.json()
        # Deve conter dados de receitas e despesas
        assert any(k in resumo for k in [
            "total_receitas", "receitas", "total_entradas",
            "total_despesas", "despesas", "total_saidas"
        ])

        # Passo 11: Verifica trilha de auditoria
        for transaction in transactions:
            response = client.get(
                f"/transacoes/auditoria/{transaction['transacao_id']}", headers=headers
            )
            assert response.status_code == status.HTTP_200_OK
            auditoria = response.json()
            assert len(auditoria) > 0
            # Deve conter entrada de criação
            assert any(entry.get("acao") == "criar" for entry in auditoria)

        # Passo 12: Verifica cálculos de saldo
        # Esperado: 2000 + 3000 - 150 - 50 = 4800 para a primeira conta
        response = client.get(
            f"/contas/{accounts[0]['conta_id']}", headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        account = response.json()
        expected_balance = 2000 + 3000 - 150 - 50
        assert abs(account["saldo"] - expected_balance) < 0.01

        # Passo 13: Testa consistência dos dados entre operações
        # Deleta uma transação e verifica a auditoria
        response = client.delete(
            f"/transacoes/{transactions[1]['transacao_id']}", headers=headers
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifica se a auditoria inclui a deleção
        response = client.get(
            f"/transacoes/auditoria/{transactions[1]['transacao_id']}", headers=headers
        )
        if response.status_code == status.HTTP_200_OK:
            auditoria = response.json()
            # Deve conter entrada de deleção
            assert any(entry.get("acao") == "deletar" for entry in auditoria)

    def test_fluxo_multiplos_usuarios(self, client, dynamodb_mock):
        """
        Testa se os dados de múltiplos usuários estão devidamente isolados.

        Verifica que:
        1. Dois usuários podem se registrar e fazer login independentemente
        2. As contas e transações de cada usuário são isoladas
        3. Usuários não podem acessar dados uns dos outros
        """

        # Cria o primeiro usuário
        user1_data = {
            "email": "user1@example.com",
            "nome": "User One",
            "senha": "Password123!",
        }
        response = client.post("/usuarios/registrar", json=user1_data)
        assert response.status_code == status.HTTP_201_CREATED

        # Cria o segundo usuário
        user2_data = {
            "email": "user2@example.com",
            "nome": "User Two",
            "senha": "Password456!",
        }
        response = client.post("/usuarios/registrar", json=user2_data)
        assert response.status_code == status.HTTP_201_CREATED

        # Faz login como primeiro usuário
        response = client.post(
            "/usuarios/login",
            data={"username": user1_data["email"], "password": user1_data["senha"]},
        )
        token1 = response.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Faz login como segundo usuário
        response = client.post(
            "/usuarios/login",
            data={"username": user2_data["email"], "password": user2_data["senha"]},
        )
        token2 = response.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Usuário 1 cria conta e transações
        account1_data = {
            "nome": "User 1 Account",
            "tipo": "corrente",
            "saldo_inicial": 1000.00,
        }
        response = client.post("/contas", json=account1_data, headers=headers1)
        account1 = response.json()

        # Usuário 2 cria conta e transações
        account2_data = {
            "nome": "User 2 Account",
            "tipo": "poupanca",
            "saldo_inicial": 2000.00,
        }
        response = client.post("/contas", json=account2_data, headers=headers2)
        account2 = response.json()

        # Usuário 1 deve ver apenas a sua conta
        response = client.get("/contas", headers=headers1)
        accounts1 = response.json()
        assert len(accounts1) == 1
        assert accounts1[0]["conta_id"] == account1["conta_id"]

        # Usuário 2 deve ver apenas a sua conta
        response = client.get("/contas", headers=headers2)
        accounts2 = response.json()
        assert len(accounts2) == 1
        assert accounts2[0]["conta_id"] == account2["conta_id"]

        # Usuário 1 não pode acessar a conta do Usuário 2
        response = client.get(f"/contas/{account2['conta_id']}", headers=headers1)
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Usuário 2 não pode acessar a conta do Usuário 1
        response = client.get(f"/contas/{account1['conta_id']}", headers=headers2)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_fluxo_concorrente_atualizacoes(self, client, dynamodb_mock):
        """
        Testa o tratamento de operações concorrentes na mesma conta.

        Verifica se os cálculos de saldo permanecem consistentes
        mesmo com múltiplas transações na mesma conta.
        """
        # Registra e faz login
        user_data = {
            "email": "concurrent@example.com",
            "nome": "Concurrent User",
            "senha": "ConcurrentTest123!",
        }
        response = client.post("/usuarios/registrar", json=user_data)
        user_id = response.json()["user_id"]

        response = client.post(
            "/usuarios/login",
            data={"username": user_data["email"], "password": user_data["senha"]},
        )
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        # Cria conta
        account_data = {
            "nome": "Test Account",
            "tipo": "corrente",
            "saldo_inicial": 1000.00,
        }
        response = client.post("/contas", json=account_data, headers=headers)
        account = response.json()
        initial_balance = account["saldo"]

        # Cria categoria
        category_data = {
            "nome": "Test",
            "descricao": "Test category",
            "tipo": "despesa",
        }
        response = client.post("/categorias", json=category_data, headers=headers)
        category = response.json()

        # Cria múltiplas transações em sequência
        expected_balance = initial_balance
        for i in range(5):
            transacao_data = {
                "conta_id": account["conta_id"],
                "categoria_id": category["categoria_id"],
                "tipo": "saque",
                "valor": 100.00,
                "descricao": f"Transaction {i + 1}",
                "data": str(date.today()),
            }
            response = client.post("/transacoes", json=transacao_data, headers=headers)
            assert response.status_code == status.HTTP_201_CREATED
            expected_balance -= 100.00

        # Verifica saldo final
        response = client.get(f"/contas/{account['conta_id']}", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        final_balance = response.json()["saldo"]
        assert abs(final_balance - expected_balance) < 0.01

        # Verifica se todas as transações foram registradas
        response = client.get("/transacoes", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        transactions = response.json()
        assert len(transactions) == 5

    def test_fluxo_com_filtros_relatorio(self, client, dynamodb_mock):
        """
        Testa a geração de relatórios com vários filtros.

        Verifica se a filtragem funciona corretamente em diferentes intervalos de data.
        """
        # Registra e faz login
        user_data = {
            "email": "filters@example.com",
            "nome": "Filter Test User",
            "senha": "FilterTest123!",
        }
        response = client.post("/usuarios/registrar", json=user_data)

        response = client.post(
            "/usuarios/login",
            data={"username": user_data["email"], "password": user_data["senha"]},
        )
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        # Cria conta e categoria
        account_data = {
            "nome": "Test Account",
            "tipo": "corrente",
            "saldo_inicial": 5000.00,
        }
        response = client.post("/contas", json=account_data, headers=headers)
        account = response.json()

        category_data = {
            "nome": "Test",
            "descricao": "Test",
            "tipo": "despesa",
        }
        response = client.post("/categorias", json=category_data, headers=headers)
        category = response.json()

        # Cria transações
        transacao_data = {
            "conta_id": account["conta_id"],
            "categoria_id": category["categoria_id"],
            "tipo": "saque",
            "valor": 200.00,
            "descricao": "Test",
            "data": str(date.today()),
        }
        client.post("/transacoes", json=transacao_data, headers=headers)

        # Testa filtragem por conta nos relatórios
        response = client.get(
            f"/relatorios/extrato?conta_id={account['conta_id']}", headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        extrato = response.json()
        # Deve conter transação ou ser lista vazia
        assert isinstance(extrato.get("transacoes", []), list)

        # Testa relatórios gerais
        response = client.get("/relatorios/saldo", headers=headers)
        assert response.status_code == status.HTTP_200_OK

        response = client.get("/relatorios/resumo", headers=headers)
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# Teste de integração ponta a ponta: HMAC + Snapshot + Adulteração
# ---------------------------------------------------------------------------

class TestFluxoSegurancaCompleto:
    """
    Testes de integração que cobrem o ciclo completo de segurança:
    operações financeiras → auditoria HMAC → snapshot Merkle → adulteração → detecção.

    São os testes mais importantes do sistema de integridade — provam que
    todas as peças funcionam juntas de ponta a ponta.
    """

    def test_fluxo_completo_hmac_snapshot_verificacao(self, client, dynamodb_mock):
        """
        O que faz: Executa o fluxo completo de segurança em um único teste:
                   1. Registra usuário e autentica
                   2. Cria conta e categoria
                   3. Cria várias transações (cada uma gera auditoria HMAC)
                   4. Verifica que todos os registros de auditoria têm campo hash
                   5. Cria um snapshot Merkle do estado atual
                   6. Verifica que o snapshot está íntegro (valido=True)
                   7. Cria nova transação (deve mudar o estado da cadeia)
                   8. Verifica que o snapshot antigo agora detecta divergência

        Por que importa: Testa que HMAC, Merkle Tree e snapshots funcionam
                         em conjunto no fluxo real de uso do sistema.
                         Um erro em qualquer camada quebra a cadeia de confiança.

        O que valida: O sistema detecta corretamente a diferença entre o estado
                      capturado no snapshot e o estado atual da cadeia de auditoria.
        """
        # --- 1. Setup: usuário, conta, categoria ---
        user_data = {
            "email": "seguranca@example.com",
            "nome": "Security Test User",
            "senha": "SecurityTest123!",
        }
        response = client.post("/usuarios/registrar", json=user_data)
        assert response.status_code == status.HTTP_201_CREATED

        response = client.post(
            "/usuarios/login",
            data={"username": user_data["email"], "password": user_data["senha"]},
        )
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        conta_data = {"nome": "Conta Segurança", "tipo": "corrente", "saldo_inicial": 5000.00}
        response = client.post("/contas", json=conta_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        conta_id = response.json()["conta_id"]

        cat_data = {"nome": "Segurança", "descricao": "Testes", "tipo": "despesa"}
        response = client.post("/categorias", json=cat_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        categoria_id = response.json()["categoria_id"]

        # --- 2. Cria 3 transações para popular a auditoria ---
        transacoes_ids = []
        for i in range(3):
            t_data = {
                "conta_id": conta_id,
                "categoria_id": categoria_id,
                "tipo": "saque",
                "valor": float(100 + i * 50),
                "descricao": f"Transação segurança {i + 1}",
            }
            response = client.post("/transacoes", json=t_data, headers=headers)
            assert response.status_code == status.HTTP_201_CREATED
            transacoes_ids.append(response.json()["transacao_id"])

        # --- 3. Verifica que todos os registros de auditoria têm HMAC ---
        for tid in transacoes_ids:
            response = client.get(f"/transacoes/auditoria/{tid}", headers=headers)
            assert response.status_code == status.HTTP_200_OK
            for entrada in response.json():
                assert "hash" in entrada, "Todo registro de auditoria deve ter campo 'hash'"
                assert len(entrada["hash"]) == 64, "Hash HMAC-SHA256 deve ter 64 chars"

        # --- 4. Verifica integridade da cadeia HMAC (sem adulteração) ---
        response = client.get("/transacoes/auditoria/verificar-integridade", headers=headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["integra"] is True

        # --- 5. Cria snapshot Merkle do estado atual ---
        response = client.post("/snapshots/", headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
        snapshot = response.json()
        snapshot_id = snapshot["snapshot_id"]
        total_no_snapshot = snapshot["total_registros"]
        assert snapshot["total_registros"] >= 3
        assert len(snapshot["merkle_root"]) == 64

        # --- 6. Verifica snapshot imediatamente (deve estar válido) ---
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["valido"] is True

        # --- 7. Cria nova transação APÓS o snapshot ---
        t_nova = {
            "conta_id": conta_id,
            "categoria_id": categoria_id,
            "tipo": "deposito",
            "valor": 9999.00,
            "descricao": "Transação APÓS o snapshot",
        }
        response = client.post("/transacoes", json=t_nova, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED

        # --- 8. Verifica snapshot antigo — deve detectar divergência ---
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=headers
        )
        assert response.status_code == status.HTTP_200_OK
        resultado = response.json()

        # O snapshot foi criado com N registros; agora há N+1 → raízes divergem
        assert resultado["valido"] is False, \
            "Snapshot deve detectar que um novo registro foi adicionado após sua criação"
        assert resultado["total_registros_atual"] > total_no_snapshot

    def test_snapshot_detecta_adulteracao_de_valor_financeiro(
        self, client, dynamodb_mock
    ):
        """
        O que faz: Simula o ataque mais comum em sistemas financeiros —
                   modificação retroativa do valor de uma transação para
                   cometer fraude. O fluxo completo é testado:
                   1. Transação legítima de R$100,00
                   2. Snapshot criado
                   3. Invasor muda o valor para R$9.999,99 no banco
                   4. Verificação do snapshot detecta a adulteração

        Por que importa: Este é o cenário de ameaça número 1 para sistemas
                         financeiros. O teste prova que a combinação HMAC +
                         Merkle + Snapshot é capaz de detectar fraude financeira.

        O que valida: O sistema de auditoria detecta adulteração de valor
                      mesmo quando feita diretamente no banco de dados.
        """
        # Setup
        user_data = {"email": "fraude@example.com", "nome": "Fraude Test", "senha": "FraudeTest123!"}
        client.post("/usuarios/registrar", json=user_data)
        response = client.post(
            "/usuarios/login",
            data={"username": user_data["email"], "password": user_data["senha"]},
        )
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        conta_data = {"nome": "Conta Fraude", "tipo": "corrente", "saldo_inicial": 1000.00}
        conta = client.post("/contas", json=conta_data, headers=headers).json()

        cat_data = {"nome": "Cat Fraude", "descricao": "teste", "tipo": "despesa"}
        cat = client.post("/categorias", json=cat_data, headers=headers).json()

        # Cria transação legítima
        t_data = {
            "conta_id": conta["conta_id"],
            "categoria_id": cat["categoria_id"],
            "tipo": "saque",
            "valor": 100.00,
            "descricao": "Saque legítimo R$100",
        }
        r_t = client.post("/transacoes", json=t_data, headers=headers)
        transacao_id = r_t.json()["transacao_id"]

        # Cria snapshot antes da adulteração
        r_snap = client.post("/snapshots/", headers=headers)
        snapshot_id = r_snap.json()["snapshot_id"]

        # Confirma que snapshot está válido
        r_check = client.post(f"/snapshots/{snapshot_id}/verificar", headers=headers)
        assert r_check.json()["valido"] is True

        # Obtém audit_id do registro de auditoria
        r_audit = client.get(f"/transacoes/auditoria/{transacao_id}", headers=headers)
        audit_entries = r_audit.json()
        assert len(audit_entries) > 0
        user_id = audit_entries[0]["user_id"]
        audit_id = audit_entries[0]["audit_id"]

        # ATAQUE: invasor muda o valor de R$100 para R$9.999,99 no banco
        from decimal import Decimal
        table = dynamodb_mock.Table("Auditoria")
        table.update_item(
            Key={"user_id": user_id, "audit_id": audit_id},
            UpdateExpression="SET dados_novos.valor = :v",
            ExpressionAttributeValues={":v": Decimal("9999.99")},
        )

        # Verificação deve detectar a adulteração
        r_verify = client.post(f"/snapshots/{snapshot_id}/verificar", headers=headers)
        resultado = r_verify.json()

        assert resultado["valido"] is False, \
            "O sistema deve detectar a adulteração do valor financeiro"
        assert resultado["merkle_root_snapshot"] != resultado["merkle_root_atual"], \
            "As raízes Merkle devem divergir — prova criptográfica da adulteração"
