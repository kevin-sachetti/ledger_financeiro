"""
Configuração do Pytest e fixtures compartilhadas para os testes do mini-gestor-financeiro.

Fornece DynamoDB mockado via moto, TestClient do FastAPI e fixtures auxiliares.
"""

import os

# Define variáveis de ambiente ANTES de qualquer import da aplicação
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:5555"
os.environ["DYNAMODB_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
# Chave HMAC usada nos testes; deve ser diferente de qualquer valor de produção
os.environ["HMAC_SECRET"] = "test-hmac-secret-key-for-testing"
os.environ["SNAPSHOT_INTERVAL_HOURS"] = "24"

import boto3
import pytest
from moto import mock_dynamodb
from fastapi.testclient import TestClient

from app.database.conexao import DynamoDBConnection


def _create_all_tables(dynamodb) -> None:
    """Cria todas as tabelas DynamoDB no recurso mockado."""
    # Usuarios
    dynamodb.create_table(
        TableName="Usuarios",
        KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email-index",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Contas
    dynamodb.create_table(
        TableName="Contas",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "conta_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "conta_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Transacoes
    dynamodb.create_table(
        TableName="Transacoes",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "transacao_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "transacao_id", "AttributeType": "S"},
            {"AttributeName": "conta_id", "AttributeType": "S"},
            {"AttributeName": "categoria_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "conta_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "conta_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            },
            {
                "IndexName": "categoria_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "categoria_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            },
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Categorias
    dynamodb.create_table(
        TableName="Categorias",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "categoria_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "categoria_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Orcamentos
    dynamodb.create_table(
        TableName="Orcamentos",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "orcamento_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "orcamento_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Auditoria
    dynamodb.create_table(
        TableName="Auditoria",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "audit_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "audit_id", "AttributeType": "S"},
            {"AttributeName": "transacao_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "transacao_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "transacao_id", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5,
                },
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Snapshots — tabela para snapshots periódicos de Merkle Tree
    dynamodb.create_table(
        TableName="Snapshots",
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "snapshot_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "snapshot_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )


@pytest.fixture(autouse=True)
def dynamodb_mock():
    """
    Fixture auto-use: mocka o DynamoDB para cada teste.

    Usa moto para interceptar todas as chamadas boto3 ao DynamoDB. Injeta
    no singleton DynamoDBConnection para que todo o código da aplicação use o mock.
    """
    with mock_dynamodb():
        # Cria um recurso com backend moto (não precisa de endpoint_url com moto)
        dynamodb = boto3.resource(
            "dynamodb",
            region_name="us-east-1",
        )

        # Injeta no singleton para que todo o código da aplicação use este recurso
        DynamoDBConnection._instance = None
        DynamoDBConnection._dynamodb = dynamodb

        # Força o singleton a estar "inicializado"
        conn = DynamoDBConnection.__new__(DynamoDBConnection)
        conn._dynamodb = dynamodb
        DynamoDBConnection._instance = conn

        _create_all_tables(dynamodb)

        yield dynamodb

        # Reseta o singleton após o teste
        DynamoDBConnection._instance = None
        DynamoDBConnection._dynamodb = None


@pytest.fixture
def client():
    """Fixture do TestClient do FastAPI."""
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def test_user_data():
    """Dados de registro do usuário de teste."""
    return {
        "email": "testuser@example.com",
        "nome": "Test User",
        "senha": "TestPassword123!",
    }


@pytest.fixture
def test_user_registered(client, test_user_data):
    """Registra um usuário de teste e retorna os dados da resposta."""
    response = client.post("/usuarios/registrar", json=test_user_data)
    assert response.status_code in (200, 201), f"Registration failed: {response.text}"
    return response.json()


@pytest.fixture
def auth_headers(client, test_user_data, test_user_registered):
    """Faz login e retorna os headers de Authorization com Bearer token."""
    response = client.post(
        "/usuarios/login",
        data={
            "username": test_user_data["email"],
            "password": test_user_data["senha"],
        },
    )
    assert response.status_code == 200, f"Login failed: {response.text}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_account(client, auth_headers):
    """Cria e retorna uma conta bancária de teste."""
    account_data = {
        "nome": "Conta de Testes",
        "tipo": "corrente",
        "saldo_inicial": 1000.00,
    }
    response = client.post("/contas", json=account_data, headers=auth_headers)
    assert response.status_code in (200, 201), f"Account creation failed: {response.text}"
    return response.json()


@pytest.fixture
def test_category(client, auth_headers):
    """Cria e retorna uma categoria de teste."""
    category_data = {
        "nome": "Alimentação",
        "descricao": "Gastos com alimentação",
        "tipo": "despesa",
    }
    response = client.post("/categorias", json=category_data, headers=auth_headers)
    assert response.status_code in (200, 201), f"Category creation failed: {response.text}"
    return response.json()
