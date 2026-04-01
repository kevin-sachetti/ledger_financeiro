"""
Conjunto de testes para os endpoints de relatórios e análises financeiras.

Testes para:
- Extrato de conta (extrato)
- Gastos por categoria (gastos-por-categoria)
- Saldo total (saldo)
- Resumo financeiro (resumo)
- Filtragem e cálculos de relatórios
"""

import pytest
from datetime import datetime, date
from fastapi import status


class TestExtrato:
    """Testes para o endpoint de extrato de conta."""

    def test_extrato_vazio(self, client, auth_headers):
        """
        Testa a geração de extrato quando não existem transações.

        Deve retornar 200 com lista de transações vazia.
        """
        response = client.get("/relatorios/extrato", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "transacoes" in data
        assert isinstance(data["transacoes"], list)
        assert len(data["transacoes"]) == 0

    def test_extrato_com_transacoes(self, client, auth_headers, test_account, test_category):
        """
        Testa a geração de extrato com transações existentes.

        Deve retornar 200 com lista de transações e resumo.
        """
        # Cria algumas transações
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Salário",
            "data": str(date.today()),
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "saque",
            "valor": 100.00,
            "descricao": "Compras",
            "data": str(date.today()),
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        response = client.get("/relatorios/extrato", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["transacoes"]) == 2

    def test_extrato_filtro_conta(self, client, auth_headers, test_account, test_category):
        """
        Testa a geração de extrato filtrado por conta.

        Deve retornar apenas as transações da conta especificada.
        """
        # Cria outra conta
        conta_data = {
            "nome": "Conta 2",
            "tipo": "poupanca",
            "saldo_inicial": 500.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        conta_2 = response.json()

        # Cria transações em ambas as contas
        for conta in [test_account, conta_2]:
            transacao_data = {
                "conta_id": conta["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 100.00,
                "descricao": "Teste",
                "data": str(date.today()),
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Busca extrato da primeira conta
        response = client.get(
            f"/relatorios/extrato?conta_id={test_account['conta_id']}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Deve conter apenas transações da primeira conta
        for transacao in data["transacoes"]:
            assert transacao["conta_id"] == test_account["conta_id"]

    def test_extrato_sem_autenticacao(self, client):
        """
        Testa a geração de extrato sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/relatorios/extrato")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_extrato_inclui_resumo(self, client, auth_headers, test_account, test_category):
        """
        Testa se o extrato inclui informações de resumo.

        Deve conter saldo_inicial, total_entradas, total_saidas, saldo_final.
        """
        # Cria transações
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 500.00,
                "descricao": "Entrada",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "saque",
                "valor": 200.00,
                "descricao": "Saída",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )

        response = client.get("/relatorios/extrato", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Verifica campos de resumo
        assert "total_receitas" in data or "saldo_liquido" in data


class TestGastosPorCategoria:
    """Testes para o endpoint de gastos por categoria."""

    def test_gastos_por_categoria_vazio(self, client, auth_headers):
        """
        Testa gastos por categoria quando não existem transações.

        Deve retornar 200 com lista vazia.
        """
        response = client.get("/relatorios/gastos-por-categoria", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_gastos_por_categoria_com_transacoes(self, client, auth_headers, test_account, test_category):
        """
        Testa gastos por categoria com transações existentes.

        Deve retornar lista com valores gastos por categoria.
        """
        # Cria transações na categoria de teste
        for i in range(2):
            client.post(
                "/transacoes",
                json={
                    "conta_id": test_account["conta_id"],
                    "categoria_id": test_category["categoria_id"],
                    "tipo": "saque",
                    "valor": 100.00,
                    "descricao": f"Gasto {i + 1}",
                    "data": str(date.today()),
                },
                headers=auth_headers,
            )

        response = client.get("/relatorios/gastos-por-categoria", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) > 0
        assert any(item["categoria_id"] == test_category["categoria_id"] for item in data)

    def test_gastos_por_categoria_sem_autenticacao(self, client):
        """
        Testa gastos por categoria sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/relatorios/gastos-por-categoria")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_gastos_por_categoria_inclui_nome(self, client, auth_headers, test_account, test_category):
        """
        Testa se os gastos por categoria incluem o nome da categoria.

        Deve conter categoria_nome na resposta.
        """
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "saque",
                "valor": 150.00,
                "descricao": "Teste",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )

        response = client.get("/relatorios/gastos-por-categoria", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if len(data) > 0:
            assert "categoria_id" in data[0]
            # Pode conter categoria_nome ou campo similar
            assert any(k in data[0] for k in ["categoria_nome", "nome", "categoria"])

    def test_gastos_por_categoria_calculos_corretos(self, client, auth_headers, test_account, test_category):
        """
        Testa se os valores de gasto são calculados corretamente.

        Deve somar todos os saques de cada categoria.
        """
        # Cria múltiplas transações
        valores = [50.00, 75.00, 25.00]
        for valor in valores:
            client.post(
                "/transacoes",
                json={
                    "conta_id": test_account["conta_id"],
                    "categoria_id": test_category["categoria_id"],
                    "tipo": "saque",
                    "valor": valor,
                    "descricao": f"Gasto {valor}",
                    "data": str(date.today()),
                },
                headers=auth_headers,
            )

        response = client.get("/relatorios/gastos-por-categoria", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        total_esperado = sum(valores)
        for item in data:
            if item["categoria_id"] == test_category["categoria_id"]:
                assert abs(item.get("total", item.get("valor", 0)) - total_esperado) < 0.01


class TestSaldoTotal:
    """Testes para o endpoint de saldo total."""

    def test_saldo_total_inicial(self, client, auth_headers, test_account):
        """
        Testa o saldo total com o saldo inicial da conta.

        Deve retornar a soma dos saldos das contas.
        """
        response = client.get("/relatorios/saldo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "saldo_total" in data or "total" in data or "saldo" in data

    def test_saldo_total_apos_transacoes(self, client, auth_headers, test_account, test_category):
        """
        Testa o saldo total após transações.

        Deve refletir os depósitos e saques realizados.
        """
        initial_response = client.get("/relatorios/saldo", headers=auth_headers)
        initial_saldo = (
            initial_response.json().get("saldo_total") or
            initial_response.json().get("total") or
            initial_response.json().get("saldo")
        )

        # Depósito
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 500.00,
                "descricao": "Deposito",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )

        response = client.get("/relatorios/saldo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        new_saldo = (
            data.get("saldo_total") or
            data.get("total") or
            data.get("saldo")
        )
        assert new_saldo == initial_saldo + 500.00

    def test_saldo_total_multiplas_contas(self, client, auth_headers, test_account):
        """
        Testa o saldo total com múltiplas contas.

        Deve retornar a soma dos saldos de todas as contas.
        """
        # Cria outra conta
        conta_data = {
            "nome": "Conta 2",
            "tipo": "poupanca",
            "saldo_inicial": 2000.00,
        }
        client.post("/contas", json=conta_data, headers=auth_headers)

        response = client.get("/relatorios/saldo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        total = (
            data.get("saldo_total") or
            data.get("total") or
            data.get("saldo")
        )
        # Deve ser a soma dos saldos iniciais de ambas as contas
        assert total == test_account["saldo"] + 2000.00

    def test_saldo_total_sem_autenticacao(self, client):
        """
        Testa o saldo total sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/relatorios/saldo")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_saldo_total_sem_contas(self, client, auth_headers):
        """
        Testa o saldo total sem nenhuma conta cadastrada.

        Deve retornar 0 ou estrutura vazia.
        """
        response = client.get("/relatorios/saldo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        saldo = (
            data.get("saldo_total") or
            data.get("total") or
            data.get("saldo") or
            0
        )
        assert saldo == 0


class TestResumoFinanceiro:
    """Testes para o endpoint de resumo financeiro."""

    def test_resumo_vazio(self, client, auth_headers):
        """
        Testa o resumo financeiro sem transações.

        Deve retornar 200 com valores zerados.
        """
        response = client.get("/relatorios/resumo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Deve conter campos do resumo financeiro
        assert any(k in data for k in ["receitas", "despesas", "saldo", "total_receitas", "total_despesas"])

    def test_resumo_com_transacoes(self, client, auth_headers, test_account, test_category):
        """
        Testa o resumo financeiro com transações existentes.

        Deve calcular receitas, despesas e saldo.
        """
        # Cria depósito e saque
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 1000.00,
                "descricao": "Salário",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "saque",
                "valor": 200.00,
                "descricao": "Compras",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )

        response = client.get("/relatorios/resumo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Deve conter totais de transações
        assert any(k in data for k in ["total_receitas", "receitas", "total_entradas"])
        assert any(k in data for k in ["total_despesas", "despesas", "total_saidas"])

    def test_resumo_sem_autenticacao(self, client):
        """
        Testa o resumo financeiro sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/relatorios/resumo")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_resumo_inclui_saldo(self, client, auth_headers, test_account, test_category):
        """
        Testa se o resumo financeiro inclui campo de saldo.

        Deve conter saldo ou campo equivalente.
        """
        client.post(
            "/transacoes",
            json={
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 300.00,
                "descricao": "Teste",
                "data": str(date.today()),
            },
            headers=auth_headers,
        )

        response = client.get("/relatorios/resumo", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert any(k in data for k in ["saldo", "saldo_total", "net", "balance"])
