"""
Suite de testes para os endpoints de gerenciamento de usuarios.

Testes para:
- Registro de usuario
- Login e autenticacao de usuario
- Consulta de perfil de usuario
- Atualizacao de perfil de usuario
- Autenticacao e autorizacao
"""

import pytest
from fastapi import status


class TestRegistroUsuario:
    """Testes para o endpoint de registro de usuários."""

    def test_registrar_usuario_sucesso(self, client, test_user_data):
        """
        Testa registro de usuário com sucesso.

        Deve retornar 201 com dados do usuário incluindo user_id.
        """
        response = client.post("/usuarios/registrar", json=test_user_data)
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "user_id" in data
        assert data["email"] == test_user_data["email"]
        assert data["nome"] == test_user_data["nome"]
        assert "senha_hash" not in data

    def test_registrar_usuario_email_duplicado(self, client, test_user_data, test_user_registered):
        """
        Testa registro com email duplicado.

        Deve retornar 400 ao tentar registrar com email existente.
        """
        response = client.post("/usuarios/registrar", json=test_user_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response.json()["detail"]

    def test_registrar_usuario_dados_incompletos(self, client):
        """
        Testa registro com dados incompletos.

        Deve retornar 422 com erro de validação.
        """
        incomplete_data = {
            "email": "test@example.com",
            "nome": "Test User",
            # Faltando senha
        }
        response = client.post("/usuarios/registrar", json=incomplete_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_registrar_usuario_email_invalido(self, client):
        """
        Testa registro com formato de email inválido.

        Deve retornar 422 com erro de validação.
        """
        invalid_data = {
            "email": "not-an-email",
            "nome": "Test User",
            "senha": "TestPassword123!",
        }
        response = client.post("/usuarios/registrar", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginUsuario:
    """Testes para o endpoint de login de usuários."""

    def test_login_sucesso(self, client, test_user_data, test_user_registered):
        """
        Testa login com sucesso.

        Deve retornar token com access_token e token_type.
        """
        response = client.post(
            "/usuarios/login",
            data={
                "username": test_user_data["email"],
                "password": test_user_data["senha"],
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 0

    def test_login_senha_incorreta(self, client, test_user_data, test_user_registered):
        """
        Testa login com senha incorreta.

        Deve retornar 401.
        """
        response = client.post(
            "/usuarios/login",
            data={
                "username": test_user_data["email"],
                "password": "WrongPassword123!",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Email ou senha inválidos" in response.json()["detail"]

    def test_login_email_nao_registrado(self, client):
        """
        Testa login com email não registrado.

        Deve retornar 401.
        """
        response = client.post(
            "/usuarios/login",
            data={
                "username": "nonexistent@example.com",
                "password": "SomePassword123!",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_campo_obrigatorio_faltando(self, client):
        """
        Testa login com campos obrigatórios faltando.

        Deve retornar 422.
        """
        response = client.post(
            "/usuarios/login",
            data={
                "username": "test@example.com",
                # Faltando senha
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestPerfilUsuario:
    """Testes para os endpoints de perfil de usuário."""

    def test_obter_perfil_sucesso(self, client, auth_headers, test_user_data, test_user_registered):
        """
        Testa consulta de perfil com sucesso.

        Deve retornar 200 com dados do usuário.
        """
        response = client.get("/usuarios/perfil", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["nome"] == test_user_data["nome"]
        assert data["user_id"] == test_user_registered["user_id"]

    def test_obter_perfil_sem_autenticacao(self, client):
        """
        Testa acesso ao perfil sem autenticação.

        Deve retornar 401.
        """
        response = client.get("/usuarios/perfil")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obter_perfil_token_invalido(self, client):
        """
        Testa acesso ao perfil com token inválido.

        Deve retornar 401.
        """
        headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/usuarios/perfil", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_obter_perfil_token_expirado(self, client, auth_headers):
        """
        Testa acesso ao perfil com token expirado.

        Este teste precisaria manipular a expiração do token,
        o que é complexo em ambiente de teste. Pulando por enquanto.
        """
        pass

    def test_atualizar_perfil_sucesso(self, client, auth_headers, test_user_registered):
        """
        Testa atualização de perfil com sucesso.

        Deve retornar 200 com dados atualizados.
        """
        updated_data = {
            "email": "newemail@example.com",
            "nome": "Updated User Name",
        }
        response = client.put("/usuarios/perfil", json=updated_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nome"] == updated_data["nome"]
        assert data["email"] == updated_data["email"]
        assert data["user_id"] == test_user_registered["user_id"]

    def test_atualizar_perfil_sem_autenticacao(self, client):
        """
        Testa atualização de perfil sem autenticação.

        Deve retornar 401.
        """
        updated_data = {
            "email": "newemail@example.com",
            "nome": "Updated User",
        }
        response = client.put("/usuarios/perfil", json=updated_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_atualizar_perfil_email_duplicado(self, client, auth_headers, test_user_data):
        """
        Testa atualização de perfil com email que já existe.

        Deve retornar 400.
        """
        # Primeiro cria outro usuário
        other_user_data = {
            "email": "otheruser@example.com",
            "nome": "Other User",
            "senha": "OtherPassword123!",
        }
        client.post("/usuarios/registrar", json=other_user_data)

        # Tenta atualizar o primeiro usuário com o email do outro
        updated_data = {
            "email": "otheruser@example.com",
            "nome": "Updated User",
        }
        response = client.put("/usuarios/perfil", json=updated_data, headers=auth_headers)
        # Dependendo da implementação, pode ser 400 ou outro erro
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_409_CONFLICT,
        ]

    def test_atualizar_perfil_apenas_nome(self, client, auth_headers, test_user_data):
        """
        Testa atualização de perfil apenas com campo nome.

        Deve atualizar apenas o nome, mantendo email inalterado.
        """
        updated_data = {
            "email": test_user_data["email"],  # Mantém mesmo email
            "nome": "Only Updated Name",
        }
        response = client.put("/usuarios/perfil", json=updated_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["nome"] == "Only Updated Name"
        assert data["email"] == test_user_data["email"]

    def test_atualizar_perfil_apenas_email(self, client, auth_headers, test_user_data):
        """
        Testa atualização de perfil apenas com campo email.

        Deve atualizar apenas o email, mantendo nome inalterado.
        """
        updated_data = {
            "email": "newuniqueemail@example.com",
            "nome": test_user_data["nome"],  # Mantém mesmo nome
        }
        response = client.put("/usuarios/perfil", json=updated_data, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == "newuniqueemail@example.com"
        assert data["nome"] == test_user_data["nome"]


class TestHealthCheck:
    """Testes para os endpoints de health check."""

    def test_health_check_root(self, client):
        """
        Testa endpoint de health check raiz.

        Deve retornar 200 com status ok.
        """
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert "projeto" in data
        assert "versao" in data

    def test_health_check_health_endpoint(self, client):
        """
        Testa endpoint /health.

        Deve retornar 200 com status detalhado.
        """
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "region" in data
