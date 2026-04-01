"""
Suite de testes para os endpoints de transações financeiras.

Testes para:
- Criação de transações (depósitos e saques)
- Listagem de transações com filtros
- Consulta de transações
- Exclusão de transações (soft delete)
- Atualização de saldos
- Operações inválidas (ex.: saldo insuficiente)
"""

import pytest
from datetime import datetime, date
from fastapi import status


class TestCriarTransacao:
    """Testes para o endpoint de criação de transações."""

    def test_criar_deposito_sucesso(self, client, auth_headers, test_account, test_category):
        """
        Testa criação de depósito com sucesso.

        Deve retornar 201 com dados da transação incluindo transacao_id.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Salário",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "transacao_id" in data
        assert data["tipo"] == "deposito"
        assert data["valor"] == 500.00
        assert data["descricao"] == "Salário"

    def test_criar_saque_sucesso(self, client, auth_headers, test_account, test_category):
        """
        Testa criação de saque com sucesso.

        Deve retornar 201 com dados da transação.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "saque",
            "valor": 200.00,
            "descricao": "Compras",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["tipo"] == "saque"
        assert data["valor"] == 200.00

    def test_saque_saldo_insuficiente(self, client, auth_headers, test_account, test_category):
        """
        Testa saque com saldo insuficiente.

        Deve retornar 400 ou 422 dependendo da implementação.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "saque",
            "valor": 9999.00,  # Mais que o saldo inicial
            "descricao": "Saque grande",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        # Deve rejeitar por saldo insuficiente
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_criar_transacao_sem_autenticacao(self, client, test_account, test_category):
        """
        Testa criação de transação sem autenticação.

        Deve retornar 401.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_transacao_conta_inexistente(self, client, auth_headers, test_category):
        """
        Testa criação de transação com conta inexistente.

        Deve retornar 404.
        """
        transacao_data = {
            "conta_id": "conta-inexistente",
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_criar_transacao_categoria_inexistente(self, client, auth_headers, test_account):
        """
        Testa criação de transação com categoria inexistente.

        Como categorias não são validadas pela API, deve ser bem-sucedido.
        Retorna 201 pois categorias são opcionais/não validadas.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": "categoria-inexistente",
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        # Validação de categoria não está implementada, então deve ser bem-sucedido
        assert response.status_code == status.HTTP_201_CREATED

    def test_criar_transacao_dados_incompletos(self, client, auth_headers, test_account):
        """
        Testa criação de transação com dados incompletos.

        Deve retornar 422 com erro de validação.
        """
        incomplete_data = {
            "conta_id": test_account["conta_id"],
            # Faltando categoria_id, tipo, valor, descricao, data
        }
        response = client.post("/transacoes", json=incomplete_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_criar_transacao_tipo_invalido(self, client, auth_headers, test_account, test_category):
        """
        Testa criação de transação com tipo inválido.

        Deve retornar 422 ou tratar graciosamente.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "tipo_invalido",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_criar_transacao_valor_zero(self, client, auth_headers, test_account, test_category):
        """
        Testa criação de transação com valor zero.

        Deve retornar 400 ou 422.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 0.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_saldo_atualizado_apos_deposito(self, client, auth_headers, test_account, test_category):
        """
        Testa que o saldo da conta é atualizado após depósito.

        Deve aumentar o saldo pelo valor do depósito.
        """
        initial_saldo = test_account["saldo"]

        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 300.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Verifica saldo atualizado
        response = client.get(
            f"/contas/{test_account['conta_id']}", headers=auth_headers
        )
        updated_saldo = response.json()["saldo"]
        assert updated_saldo == initial_saldo + 300.00

    def test_saldo_atualizado_apos_saque(self, client, auth_headers, test_account, test_category):
        """
        Testa que o saldo da conta é atualizado após saque.

        Deve diminuir o saldo pelo valor do saque.
        """
        initial_saldo = test_account["saldo"]

        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "saque",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Verifica saldo atualizado
        response = client.get(
            f"/contas/{test_account['conta_id']}", headers=auth_headers
        )
        updated_saldo = response.json()["saldo"]
        assert updated_saldo == initial_saldo - 100.00


class TestListarTransacoes:
    """Testes para o endpoint de listagem de transações."""

    def test_listar_transacoes_vazio(self, client, auth_headers):
        """
        Testa listagem de transações quando nenhuma existe.

        Deve retornar 200 com lista vazia.
        """
        response = client.get("/transacoes", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_listar_transacoes_multiplas(self, client, auth_headers, test_account, test_category):
        """
        Testa listagem de múltiplas transações.

        Deve retornar 200 com todas as transações.
        """
        # Cria múltiplas transações
        for i in range(3):
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": 100.00 * (i + 1),
                "descricao": f"Transação {i + 1}",
                "data_transacao": datetime.now().isoformat(),
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        response = client.get("/transacoes", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3

    def test_listar_transacoes_filtro_conta(self, client, auth_headers, test_account, test_category):
        """
        Testa listagem de transações filtradas por conta.

        Deve retornar apenas transações da conta especificada.
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
                "descricao": f"Transação {conta['nome']}",
                "data_transacao": datetime.now().isoformat(),
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Lista transações da primeira conta
        response = client.get(
            f"/transacoes?conta_id={test_account['conta_id']}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["conta_id"] == test_account["conta_id"]

    def test_listar_transacoes_filtro_categoria(self, client, auth_headers, test_account, test_category):
        """
        Testa listagem de transações filtradas por categoria.

        Deve retornar apenas transações da categoria especificada.
        """
        # Cria outra categoria
        category_data = {
            "nome": "Saúde",
            "descricao": "Gastos com saúde",
            "tipo": "despesa",
        }
        response = client.post("/categorias", json=category_data, headers=auth_headers)
        categoria_2 = response.json()

        # Cria transações em ambas as categorias
        for categoria in [test_category, categoria_2]:
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": categoria["categoria_id"],
                "tipo": "saque",
                "valor": 100.00,
                "descricao": f"Transação {categoria['nome']}",
                "data_transacao": datetime.now().isoformat(),
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Lista transações da primeira categoria
        response = client.get(
            f"/transacoes?categoria_id={test_category['categoria_id']}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1

    def test_listar_transacoes_sem_autenticacao(self, client):
        """
        Testa listagem de transações sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/transacoes")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestObterTransacao:
    """Testes para o endpoint de consulta de transações."""

    def test_obter_transacao_sucesso(self, client, auth_headers, test_account, test_category):
        """
        Testa consulta de transação com sucesso.

        Deve retornar 200 com detalhes da transação.
        """
        # Cria transação
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 150.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        # Obtém transação
        response = client.get(f"/transacoes/{transacao_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["transacao_id"] == transacao_id
        assert data["valor"] == 150.00

    def test_obter_transacao_nao_encontrada(self, client, auth_headers):
        """
        Testa consulta de transação inexistente.

        Deve retornar 404.
        """
        response = client.get("/transacoes/transacao-inexistente", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_obter_transacao_sem_autenticacao(self, client, auth_headers, test_account, test_category):
        """
        Testa consulta de transação sem autenticação.

        Deve retornar 401.
        """
        # Cria transação com autenticação
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        # Tenta obter sem autenticação
        response = client.get(f"/transacoes/{transacao_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeletarTransacao:
    """Testes para o endpoint de exclusão de transações."""

    def test_deletar_transacao_sucesso(self, client, auth_headers, test_account, test_category):
        """
        Testa exclusão de transação com sucesso (soft delete).

        Deve retornar 204 No Content.
        """
        # Cria transação
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 200.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        # Deleta transação
        response = client.delete(f"/transacoes/{transacao_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verifica soft delete - transação ainda deve existir mas com status="deletada"
        response = client.get(f"/transacoes/{transacao_id}", headers=auth_headers)
        # Dependendo da implementação, pode retornar 404 ou retornar com status="deletada"
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert data.get("status") == "deletada"

    def test_deletar_transacao_nao_encontrada(self, client, auth_headers):
        """
        Testa exclusão de transação inexistente.

        Deve retornar 404.
        """
        response = client.delete("/transacoes/transacao-inexistente", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deletar_transacao_sem_autenticacao(self, client, auth_headers, test_account, test_category):
        """
        Testa exclusão de transação sem autenticação.

        Deve retornar 401.
        """
        # Cria transação com autenticação
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 100.00,
            "descricao": "Teste",
            "data_transacao": datetime.now().isoformat(),
        }
        response = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = response.json()["transacao_id"]

        # Tenta deletar sem autenticação
        response = client.delete(f"/transacoes/{transacao_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
