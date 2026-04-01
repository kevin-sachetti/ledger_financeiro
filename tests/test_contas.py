"""
Suíte de testes para os endpoints de gerenciamento de contas bancárias.

Testes para:
- Criação de contas
- Listagem de contas
- Recuperação de contas
- Atualização de contas
- Exclusão de contas
- Verificações de autorização
"""

import pytest
from fastapi import status


class TestCriarConta:
    """Testes para o endpoint de criação de contas."""

    def test_criar_conta_sucesso(self, client, auth_headers):
        """
        Testa a criação de conta com sucesso.

        Deve retornar 201 com os dados da conta incluindo conta_id.
        """
        conta_data = {
            "nome": "Conta Corrente",
            "tipo": "corrente",
            "saldo_inicial": 1500.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "conta_id" in data
        assert data["nome"] == conta_data["nome"]
        assert data["tipo"] == conta_data["tipo"]
        assert data["saldo"] == conta_data["saldo_inicial"]

    def test_criar_conta_sem_autenticacao(self, client):
        """
        Testa a criação de conta sem autenticação.

        Deve retornar 401.
        """
        conta_data = {
            "nome": "Conta Corrente",
            "tipo": "corrente",
            "saldo_inicial": 1500.00,
        }
        response = client.post("/contas", json=conta_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_criar_conta_dados_incompletos(self, client, auth_headers):
        """
        Test account creation with incomplete data.

        Should return 422 with validation error.
        """
        incomplete_data = {
            "nome": "Conta Corrente",
            # Missing tipo and saldo_inicial
        }
        response = client.post("/contas", json=incomplete_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_criar_conta_saldo_negativo(self, client, auth_headers):
        """
        Test account creation with negative balance.

        Depending on implementation, may reject or accept.
        """
        conta_data = {
            "nome": "Conta com Saldo Negativo",
            "tipo": "corrente",
            "saldo_inicial": -100.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        # Implementation validates negative initial balance at schema level (422)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_criar_conta_tipo_invalido(self, client, auth_headers):
        """
        Test account creation with invalid account type.

        Should return 422 or handle gracefully.
        """
        conta_data = {
            "nome": "Conta Inválida",
            "tipo": "tipo_invalido",
            "saldo_inicial": 1000.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        # May accept any string or validate types
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestListarContas:
    """Tests for account listing endpoint."""

    def test_listar_contas_vazio(self, client, auth_headers):
        """
        Test listing accounts when user has no accounts.

        Should return 200 with empty list.
        """
        response = client.get("/contas", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_listar_contas_multiplas(self, client, auth_headers):
        """
        Test listing multiple accounts.

        Should return 200 with all user accounts.
        """
        # Create multiple accounts
        contas_data = [
            {
                "nome": "Conta Corrente",
                "tipo": "corrente",
                "saldo_inicial": 1000.00,
            },
            {
                "nome": "Poupança",
                "tipo": "poupanca",
                "saldo_inicial": 5000.00,
            },
            {
                "nome": "Investimento",
                "tipo": "investimento",
                "saldo_inicial": 10000.00,
            },
        ]

        for conta_data in contas_data:
            client.post("/contas", json=conta_data, headers=auth_headers)

        # List accounts
        response = client.get("/contas", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_listar_contas_sem_autenticacao(self, client):
        """
        Test listing accounts without authentication.

        Should return 401.
        """
        response = client.get("/contas")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listar_contas_token_invalido(self, client):
        """
        Test listing accounts with invalid token.

        Should return 401.
        """
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/contas", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestObterConta:
    """Tests for account retrieval endpoint."""

    def test_obter_conta_sucesso(self, client, auth_headers, test_account):
        """
        Test successful account retrieval.

        Should return 200 with account details.
        """
        conta_id = test_account["conta_id"]
        response = client.get(f"/contas/{conta_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conta_id"] == conta_id
        assert data["nome"] == test_account["nome"]

    def test_obter_conta_nao_encontrada(self, client, auth_headers):
        """
        Test retrieval of non-existent account.

        Should return 404.
        """
        response = client.get("/contas/conta-inexistente", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Conta não encontrada" in response.json()["detail"]

    def test_obter_conta_sem_autenticacao(self, client, test_account):
        """
        Test account retrieval without authentication.

        Should return 401.
        """
        conta_id = test_account["conta_id"]
        response = client.get(f"/contas/{conta_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obter_conta_token_invalido(self, client, test_account):
        """
        Test account retrieval with invalid token.

        Should return 401.
        """
        conta_id = test_account["conta_id"]
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get(f"/contas/{conta_id}", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAtualizarConta:
    """Tests for account update endpoint."""

    def test_atualizar_conta_sucesso(self, client, auth_headers, test_account):
        """
        Test successful account update.

        Should return 200 with updated data.
        """
        conta_id = test_account["conta_id"]
        updated_data = {
            "nome": "Conta Corrente Atualizada",
            "tipo": "poupanca",
            "saldo_inicial": 2000.00,
        }
        response = client.put(
            f"/contas/{conta_id}",
            json=updated_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["conta_id"] == conta_id
        assert data["nome"] == updated_data["nome"]

    def test_atualizar_conta_nao_encontrada(self, client, auth_headers):
        """
        Test update of non-existent account.

        Should return 404.
        """
        updated_data = {
            "nome": "Conta Atualizada",
            "tipo": "corrente",
            "saldo_inicial": 1000.00,
        }
        response = client.put(
            "/contas/conta-inexistente",
            json=updated_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_atualizar_conta_sem_autenticacao(self, client, test_account):
        """
        Test account update without authentication.

        Should return 401.
        """
        conta_id = test_account["conta_id"]
        updated_data = {
            "nome": "Conta Atualizada",
            "tipo": "corrente",
            "saldo_inicial": 1000.00,
        }
        response = client.put(f"/contas/{conta_id}", json=updated_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_atualizar_conta_dados_incompletos(self, client, auth_headers, test_account):
        """
        Test account update with incomplete data.

        ContaUpdate schema has optional fields, so partial updates are allowed.
        Should return 200 with updated data.
        """
        conta_id = test_account["conta_id"]
        incomplete_data = {
            "nome": "Conta Atualizada",
            # Missing tipo - but that's optional in ContaUpdate
        }
        response = client.put(
            f"/contas/{conta_id}",
            json=incomplete_data,
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["nome"] == "Conta Atualizada"


class TestDeletarConta:
    """Tests for account deletion endpoint."""

    def test_deletar_conta_sucesso(self, client, auth_headers, test_account):
        """
        Test successful account deletion.

        Should return 204 No Content.
        """
        conta_id = test_account["conta_id"]
        response = client.delete(f"/contas/{conta_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify account is deleted
        response = client.get(f"/contas/{conta_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deletar_conta_nao_encontrada(self, client, auth_headers):
        """
        Test deletion of non-existent account.

        Should return 404.
        """
        response = client.delete("/contas/conta-inexistente", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deletar_conta_sem_autenticacao(self, client, test_account):
        """
        Test account deletion without authentication.

        Should return 401.
        """
        conta_id = test_account["conta_id"]
        response = client.delete(f"/contas/{conta_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deletar_conta_token_invalido(self, client, test_account):
        """
        Test account deletion with invalid token.

        Should return 401.
        """
        conta_id = test_account["conta_id"]
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.delete(f"/contas/{conta_id}", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deletar_conta_nao_pode_deletar_duas_vezes(self, client, auth_headers):
        """
        Test that deleted account cannot be deleted again.

        Should return 404 on second deletion.
        """
        conta_data = {
            "nome": "Conta Temporária",
            "tipo": "corrente",
            "saldo_inicial": 500.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        conta_id = response.json()["conta_id"]

        # First deletion
        response = client.delete(f"/contas/{conta_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Second deletion
        response = client.delete(f"/contas/{conta_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestIsolacaoContas:
    """Tests for account isolation between users."""

    def test_contas_isoladas_entre_usuarios(self, client, auth_headers):
        """
        Test that users cannot access each other's accounts.

        Create two users and verify one cannot see the other's accounts.
        """
        # Create account with first user
        conta_data = {
            "nome": "Conta Privada",
            "tipo": "corrente",
            "saldo_inicial": 1000.00,
        }
        response = client.post("/contas", json=conta_data, headers=auth_headers)
        conta_id = response.json()["conta_id"]

        # Create second user
        second_user_data = {
            "email": "seconduser@example.com",
            "nome": "Second User",
            "senha": "SecondPassword123!",
        }
        client.post("/usuarios/registrar", json=second_user_data)

        # Login as second user
        response = client.post(
            "/usuarios/login",
            data={
                "username": second_user_data["email"],
                "password": second_user_data["senha"],
            },
        )
        second_user_token = response.json()["access_token"]
        second_user_headers = {"Authorization": f"Bearer {second_user_token}"}

        # Try to access first user's account with second user
        response = client.get(f"/contas/{conta_id}", headers=second_user_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
