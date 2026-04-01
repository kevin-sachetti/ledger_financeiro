"""
Módulo de conexão com o banco de dados DynamoDB.

Fornece acesso singleton ao recurso DynamoDB usando boto3.
Gerencia a inicialização da conexão e mantém uma única instância
durante todo o ciclo de vida da aplicação.
"""

import logging
from typing import Any, Optional

import boto3

from app.config import settings

logger = logging.getLogger(__name__)


class DynamoDBConnection:
    """
    Classe singleton para gerenciamento da conexão com o DynamoDB.

    Garante que apenas uma instância do recurso DynamoDB seja criada e
    reutilizada durante todo o ciclo de vida da aplicação.

    Attributes:
        _instance: Instância singleton da classe
        _dynamodb: Instância do recurso DynamoDB
    """

    _instance: Optional["DynamoDBConnection"] = None
    _dynamodb: Optional[Any] = None

    def __new__(cls) -> "DynamoDBConnection":
        """
        Cria ou retorna a instância singleton existente.

        Returns:
            DynamoDBConnection: Instância singleton
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Inicializa a conexão com o DynamoDB se ainda não estiver inicializada."""
        if self._dynamodb is None:
            self._dynamodb = self._create_dynamodb_resource()

    @staticmethod
    def _create_dynamodb_resource() -> Any:
        """
        Cria e configura o recurso DynamoDB.

        Cria um recurso DynamoDB via boto3 com credenciais e
        configuração de endpoint a partir das configurações da aplicação.

        Returns:
            Instância do recurso DynamoDB.
        """
        logger.info(
            "Conectando ao DynamoDB em %s", settings.DYNAMODB_ENDPOINT
        )
        dynamodb = boto3.resource(
            "dynamodb",
            endpoint_url=settings.DYNAMODB_ENDPOINT,
            region_name=settings.DYNAMODB_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
        return dynamodb

    def get_dynamodb(self) -> Any:
        """
        Obtém a instância do recurso DynamoDB.

        Returns:
            Recurso DynamoDB para operações em tabelas.
        """
        if self._dynamodb is None:
            self._dynamodb = self._create_dynamodb_resource()
        return self._dynamodb

    @classmethod
    def reset(cls) -> None:
        """Reseta a instância singleton. Útil para testes."""
        cls._instance = None
        cls._dynamodb = None


def get_dynamodb_connection() -> Any:
    """
    Obtém a conexão singleton do DynamoDB.

    Fornece uma função conveniente para acessar o recurso DynamoDB
    em toda a aplicação.

    Returns:
        Instância do recurso DynamoDB.
    """
    connection = DynamoDBConnection()
    return connection.get_dynamodb()
