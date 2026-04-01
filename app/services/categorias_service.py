"""
Serviço de categorias - lida com a lógica de negócios para categorias de transações.

Funções:
    criar_categoria - Criar uma nova categoria
    listar_categorias - Listar todas as categorias de um usuário
    obter_categoria - Obter uma categoria específica por ID
    deletar_categoria - Deletar uma categoria
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.database.conexao import get_dynamodb_connection

logger = logging.getLogger(__name__)


class CategoriasService:
    """Serviço para gerenciamento de categorias de transações."""

    def criar_categoria(self, user_id: str, dados: dict) -> dict:
        """
        Criar uma nova categoria.

        Args:
            user_id: ID do usuário.
            dados: Dados da categoria com 'nome', 'tipo' e opcionais 'cor', 'descricao', 'icone'.

        Returns:
            dict: Categoria criada com categoria_id.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Categorias")

            categoria_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()

            categoria = {
                "user_id": user_id,
                "categoria_id": categoria_id,
                "nome": dados.get("nome"),
                "tipo": dados.get("tipo"),
                "cor": dados.get("cor"),
                "descricao": dados.get("descricao"),
                "icone": dados.get("icone"),
                "criado_em": now,
            }

            table.put_item(Item=categoria)
            logger.info(f"Categoria criada: {categoria_id} para usuário {user_id}")
            return categoria

        except ClientError as e:
            logger.error(f"Erro DynamoDB ao criar categoria: {e}")
            raise

    def listar_categorias(self, user_id: str) -> list:
        """
        Listar todas as categorias de um usuário.

        Args:
            user_id: ID do usuário.

        Returns:
            list: Lista de categorias pertencentes ao usuário.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Categorias")

            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
            )
            return response.get("Items", [])

        except ClientError as e:
            logger.error(f"Erro DynamoDB ao listar categorias: {e}")
            return []

    def obter_categoria(self, user_id: str, categoria_id: str) -> dict | None:
        """
        Obter uma categoria específica por ID.

        Args:
            user_id: ID do usuário (para autorização).
            categoria_id: ID da categoria.

        Returns:
            dict | None: Dados da categoria se encontrada e pertencer ao usuário, None caso contrário.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Categorias")

            response = table.get_item(
                Key={"user_id": user_id, "categoria_id": categoria_id}
            )
            return response.get("Item")

        except ClientError as e:
            logger.error(f"Erro DynamoDB ao obter categoria: {e}")
            return None

    def deletar_categoria(self, user_id: str, categoria_id: str) -> bool:
        """
        Deletar uma categoria.

        Args:
            user_id: ID do usuário (para autorização).
            categoria_id: ID da categoria.

        Returns:
            bool: True se deletada com sucesso, False se não encontrada.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Categorias")

            response = table.get_item(
                Key={"user_id": user_id, "categoria_id": categoria_id}
            )

            if "Item" not in response:
                logger.warning(f"Categoria não encontrada: {categoria_id}")
                return False

            table.delete_item(
                Key={"user_id": user_id, "categoria_id": categoria_id}
            )

            logger.info(f"Categoria deletada: {categoria_id} para usuário {user_id}")
            return True

        except ClientError as e:
            logger.error(f"Erro DynamoDB ao deletar categoria: {e}")
            raise
