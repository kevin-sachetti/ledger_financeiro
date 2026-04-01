"""
Módulo de configuração para a aplicação de gestão financeira com FastAPI.

Carrega variáveis de ambiente usando pydantic-settings e fornece
acesso centralizado à configuração da aplicação.
"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configurações da aplicação carregadas a partir de variáveis de ambiente.

    Attributes:
        DYNAMODB_ENDPOINT: URL do endpoint do DynamoDB
        DYNAMODB_REGION: Região AWS para o DynamoDB
        AWS_ACCESS_KEY_ID: Identificador da chave de acesso AWS
        AWS_SECRET_ACCESS_KEY: Chave de acesso secreta AWS
        JWT_SECRET: Chave secreta para assinatura de tokens JWT
        JWT_ALGORITHM: Algoritmo utilizado para codificação/decodificação JWT
        TOKEN_EXPIRE_MINUTES: Tempo de expiração do token JWT em minutos
        BC_API_URL: URL base da API do Banco Central do Brasil
    """

    # Configuração do DynamoDB
    DYNAMODB_ENDPOINT: str = "http://localhost:8000"
    DYNAMODB_REGION: str = "us-east-1"

    # Credenciais AWS
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"

    # Configuração JWT
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 30

    # API do Banco Central do Brasil
    BC_API_URL: str = "https://www.bcb.gov.br/api"

    # Chave secreta HMAC para assinatura de registros de auditoria
    HMAC_SECRET: str = "your-hmac-secret-change-in-production"

    # Configuração de Snapshots
    SNAPSHOT_INTERVAL_HOURS: int = 24

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


# Instância global de configurações
settings = Settings()


def get_settings() -> Settings:
    """Retorna a instância global de configurações."""
    return settings
