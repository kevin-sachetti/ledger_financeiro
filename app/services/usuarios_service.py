"""
Camada de serviço para operações de gerenciamento de usuários.

Este módulo fornece funções para criar, autenticar, recuperar e atualizar registros de usuários
na tabela DynamoDB Usuarios.
"""

import logging
from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
from botocore.exceptions import ClientError

from app.database.conexao import get_dynamodb_connection
from app.schemas.usuarios import UsuarioCreate, UsuarioUpdate

logger = logging.getLogger(__name__)


def criar_usuario(dados: UsuarioCreate) -> dict:
    """
    Cria um novo usuário na tabela Usuarios.

    Valida unicidade do email via GSI antes da criação, faz hash da senha
    e armazena o registro do usuário com timestamps.

    Args:
        dados: Schema UsuarioCreate contendo email, senha, nome.

    Returns:
        dict: O registro do usuário criado com user_id, timestamps e metadados.

    Raises:
        ValueError: Se o email já existir ou a validação falhar.
        Exception: Se a operação no DynamoDB falhar.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Usuarios")

        # Verifica se o email já existe via GSI
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :email",
            ExpressionAttributeValues={":email": dados.email},
        )

        if response.get("Items"):
            logger.warning(f"Email already registered: {dados.email}")
            raise ValueError(f"Email {dados.email} already exists")

        # Gera ID do usuário e timestamps
        user_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Faz hash da senha
        salt = bcrypt.gensalt()
        senha_hash = bcrypt.hashpw(dados.senha.encode("utf-8"), salt).decode("utf-8")

        # Prepara registro do usuário
        usuario = {
            "user_id": user_id,
            "email": dados.email,
            "nome": dados.nome,
            "senha_hash": senha_hash,
            "criado_em": now,
            "atualizado_em": now,
            "ativo": True,
        }

        # Armazena no DynamoDB
        table.put_item(Item=usuario)
        logger.info(f"User created successfully: {user_id}")

        # Retorna sem o hash da senha
        usuario.pop("senha_hash")
        return usuario

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao criar usuário: {str(e)}")
        raise
    except ValueError as e:
        logger.warning(f"Erro de validação ao criar usuário: {str(e)}")
        raise


def autenticar_usuario(email: str, senha: str) -> dict | None:
    """
    Autentica um usuário por email e senha.

    Consulta a tabela Usuarios via EmailIndex, verifica o hash da senha
    e retorna os dados do usuário se a autenticação for bem-sucedida.

    Args:
        email: Endereço de email do usuário.
        senha: Senha do usuário (texto plano).

    Returns:
        dict: Registro do usuário sem o hash da senha se autenticado, None caso contrário.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Usuarios")

        # Consulta por email
        response = table.query(
            IndexName="email-index",
            KeyConditionExpression="email = :email",
            ExpressionAttributeValues={":email": email},
        )

        if not response.get("Items"):
            logger.warning(f"Authentication failed: email not found ({email})")
            return None

        usuario = response["Items"][0]

        # Verifica senha
        if not usuario.get("ativo", True):
            logger.warning(f"Authentication failed: user inactive ({email})")
            return None

        senha_hash = usuario.get("senha_hash", "")
        if not bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8")):
            logger.warning(f"Authentication failed: invalid password ({email})")
            return None

        logger.info(f"User authenticated successfully: {usuario.get('user_id')}")

        # Retorna sem o hash da senha
        usuario.pop("senha_hash", None)
        return usuario

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao autenticar usuário: {str(e)}")
        return None


def obter_usuario_por_id(user_id: str) -> dict | None:
    """
    Recupera um registro de usuário pelo user_id.

    Args:
        user_id: A chave primária do usuário.

    Returns:
        dict: Registro do usuário sem o hash da senha se encontrado, None caso contrário.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Usuarios")

        response = table.get_item(Key={"user_id": user_id})

        if "Item" not in response:
            logger.warning(f"User not found: {user_id}")
            return None

        usuario = response["Item"]
        usuario.pop("senha_hash", None)
        return usuario

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao recuperar usuário: {str(e)}")
        return None


def atualizar_usuario(user_id: str, dados: UsuarioUpdate) -> dict | None:
    """
    Atualiza informações do usuário.

    Atualiza os campos nome e/ou email se fornecidos. Valida unicidade do email
    para atualizações de email. Atualiza o timestamp atualizado_em.

    Args:
        user_id: O ID do usuário a ser atualizado.
        dados: Schema UsuarioUpdate com campos opcionais nome e email.

    Returns:
        dict: Registro do usuário atualizado sem o hash da senha, ou None se não encontrado.

    Raises:
        ValueError: Se o novo email já existir.
        Exception: Se a operação no DynamoDB falhar.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Usuarios")

        # Obtém usuário atual
        usuario_atual = obter_usuario_por_id(user_id)
        if not usuario_atual:
            logger.warning(f"User not found for update: {user_id}")
            return None

        # Verifica unicidade do email se estiver atualizando
        if dados.email and dados.email != usuario_atual.get("email"):
            response = table.query(
                IndexName="email-index",
                KeyConditionExpression="email = :email",
                ExpressionAttributeValues={":email": dados.email},
            )
            if response.get("Items"):
                logger.warning(f"Email already exists: {dados.email}")
                raise ValueError(f"Email {dados.email} already exists")

        # Constrói expressão de atualização
        update_parts = []
        expression_values = {}

        if dados.nome:
            update_parts.append("nome = :nome")
            expression_values[":nome"] = dados.nome

        if dados.email:
            update_parts.append("email = :email")
            expression_values[":email"] = dados.email

        update_parts.append("atualizado_em = :atualizado_em")
        expression_values[":atualizado_em"] = datetime.now(timezone.utc).isoformat()

        if not update_parts:
            return usuario_atual

        # Atualiza no DynamoDB
        response = table.update_item(
            Key={"user_id": user_id},
            UpdateExpression=f"SET {', '.join(update_parts)}",
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        updated_usuario = response.get("Attributes", {})
        updated_usuario.pop("senha_hash", None)

        logger.info(f"User updated successfully: {user_id}")
        return updated_usuario

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao atualizar usuário: {str(e)}")
        raise
    except ValueError as e:
        logger.warning(f"Erro de validação ao atualizar usuário: {str(e)}")
        raise
