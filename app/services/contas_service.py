"""
Camada de serviço para operações de gerenciamento de contas bancárias.

Este módulo fornece funções para criar, ler, atualizar e deletar contas bancárias
na tabela DynamoDB Contas. Todos os valores monetários usam Decimal para precisão.
"""

import logging
from decimal import Decimal
from datetime import datetime, timezone
from uuid import uuid4

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.database.conexao import get_dynamodb_connection
from app.schemas.contas import ContaCreate, ContaUpdate

logger = logging.getLogger(__name__)


def criar_conta(user_id: str, dados: ContaCreate) -> dict:
    """
    Criar uma nova conta bancária para um usuário.

    Valida a entrada e armazena o registro da conta na tabela Contas com
    saldo inicial como Decimal e timestamps de criação.

    Args:
        user_id: O ID do usuário (chave primária).
        dados: Schema ContaCreate contendo nome, tipo, saldo_inicial, moeda.

    Returns:
        dict: O registro da conta criada com conta_id e metadados.

    Raises:
        Exception: Se a operação do DynamoDB falhar.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Contas")

        # Gerar ID da conta e timestamps
        conta_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Converter saldo para Decimal para precisão
        saldo = Decimal(str(dados.saldo_inicial))

        # Preparar registro da conta
        conta = {
            "user_id": user_id,
            "conta_id": conta_id,
            "nome": dados.nome,
            "tipo": dados.tipo,  # "corrente", "poupanca", "investimento", etc
            "saldo": saldo,
            "moeda": dados.moeda,  # "BRL", "USD", "EUR", etc
            "ativa": True,
            "criado_em": now,
            "atualizado_em": now,
        }

        # Armazenar no DynamoDB
        table.put_item(Item=conta)
        logger.info(f"Conta criada: {conta_id} para o usuário {user_id}")

        return conta

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao criar conta: {str(e)}")
        raise


def listar_contas(user_id: str) -> list:
    """
    Listar todas as contas bancárias ativas de um usuário.

    Consulta a tabela Contas por todas as contas ativas pertencentes ao usuário especificado.
    Filtra contas excluídas por soft delete (inativas).

    Args:
        user_id: O ID do usuário (chave primária).

    Returns:
        list: Lista de registros de contas ativas do usuário, lista vazia se não existirem.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Contas")

        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )

        contas = response.get("Items", [])
        # Filtrar contas inativas (soft delete)
        contas = [conta for conta in contas if conta.get("ativa", True)]
        logger.info(f"Recuperadas {len(contas)} contas ativas para o usuário {user_id}")

        return contas

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao listar contas: {str(e)}")
        return []


def obter_conta(user_id: str, conta_id: str) -> dict | None:
    """
    Recuperar uma conta bancária específica por ID.

    Args:
        user_id: O ID do usuário (chave primária).
        conta_id: O ID da conta (chave de ordenação).

    Returns:
        dict: O registro da conta se encontrada e ativa, None caso contrário.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Contas")

        response = table.get_item(
            Key={"user_id": user_id, "conta_id": conta_id}
        )

        if "Item" not in response:
            logger.warning(f"Conta não encontrada: {conta_id} para o usuário {user_id}")
            return None

        conta = response["Item"]

        # Filtrar contas inativas (soft delete)
        if not conta.get("ativa", True):
            logger.warning(f"Conta está inativa: {conta_id} para o usuário {user_id}")
            return None

        return conta

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao recuperar conta: {str(e)}")
        return None


def atualizar_conta(
    user_id: str, conta_id: str, dados: ContaUpdate
) -> dict | None:
    """
    Atualizar informações da conta bancária.

    Atualiza nome e/ou tipo se fornecidos. Atualiza o timestamp atualizado_em.

    Args:
        user_id: O ID do usuário (chave primária).
        conta_id: O ID da conta (chave de ordenação).
        dados: Schema ContaUpdate com campos opcionais nome e tipo.

    Returns:
        dict: Registro da conta atualizada, ou None se a conta não for encontrada.

    Raises:
        Exception: Se a operação do DynamoDB falhar.
    """
    try:
        # Verificar se a conta existe
        conta = obter_conta(user_id, conta_id)
        if not conta:
            logger.warning(f"Conta não encontrada para atualização: {conta_id}")
            return None

        db = get_dynamodb_connection()
        table = db.Table("Contas")

        # Construir expressão de atualização
        update_parts = []
        expression_values = {}

        if dados.nome:
            update_parts.append("nome = :nome")
            expression_values[":nome"] = dados.nome

        if dados.tipo:
            update_parts.append("tipo = :tipo")
            expression_values[":tipo"] = dados.tipo

        update_parts.append("atualizado_em = :atualizado_em")
        expression_values[":atualizado_em"] = datetime.now(timezone.utc).isoformat()

        if len(update_parts) == 1:  # Apenas atualizado_em
            return conta

        # Atualizar no DynamoDB
        response = table.update_item(
            Key={"user_id": user_id, "conta_id": conta_id},
            UpdateExpression=f"SET {', '.join(update_parts)}",
            ExpressionAttributeValues=expression_values,
            ReturnValues="ALL_NEW",
        )

        updated_conta = response.get("Attributes", {})
        logger.info(f"Conta atualizada: {conta_id} para o usuário {user_id}")

        return updated_conta

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao atualizar conta: {str(e)}")
        raise


def deletar_conta(user_id: str, conta_id: str) -> bool:
    """
    Deletar uma conta bancária (soft delete marcando como inativa).

    Marca a conta como inativa em vez de removê-la do banco de dados
    para preservar o histórico de transações e trilhas de auditoria.

    Args:
        user_id: O ID do usuário (chave primária).
        conta_id: O ID da conta (chave de ordenação).

    Returns:
        bool: True se a exclusão foi bem-sucedida, False se a conta não foi encontrada.

    Raises:
        Exception: Se a operação do DynamoDB falhar.
    """
    try:
        # Verificar se a conta existe
        conta = obter_conta(user_id, conta_id)
        if not conta:
            logger.warning(f"Conta não encontrada para exclusão: {conta_id}")
            return False

        db = get_dynamodb_connection()
        table = db.Table("Contas")

        # Soft delete - marcar como inativa
        table.update_item(
            Key={"user_id": user_id, "conta_id": conta_id},
            UpdateExpression="SET ativa = :ativa, atualizado_em = :atualizado_em",
            ExpressionAttributeValues={
                ":ativa": False,
                ":atualizado_em": datetime.now(timezone.utc).isoformat(),
            },
        )

        logger.info(f"Conta deletada (soft): {conta_id} para o usuário {user_id}")
        return True

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao deletar conta: {str(e)}")
        raise


def atualizar_saldo(
    user_id: str, conta_id: str, valor: Decimal, operacao: str
) -> dict | None:
    """
    Atualizar saldo da conta com operação de crédito ou débito.

    Aplica operações monetárias ao saldo da conta. Usa SET para garantir
    atualizações atômicas. Valida o parâmetro de operação.

    Args:
        user_id: O ID do usuário (chave primária).
        conta_id: O ID da conta (chave de ordenação).
        valor: Valor como Decimal a aplicar.
        operacao: "credito" (aumentar) ou "debito" (diminuir).

    Returns:
        dict: Registro da conta atualizada com novo saldo, ou None se a conta não for encontrada.

    Raises:
        ValueError: Se operacao não for "credito" ou "debito" ou valor for negativo.
        Exception: Se a operação do DynamoDB falhar.
    """
    try:
        # Validar entradas
        if operacao not in ("credito", "debito"):
            raise ValueError(f"operacao must be 'credito' or 'debito', got {operacao}")

        if valor < 0:
            raise ValueError(f"valor must be positive, got {valor}")

        # Verificar se a conta existe
        conta = obter_conta(user_id, conta_id)
        if not conta:
            logger.warning(f"Conta não encontrada para atualização de saldo: {conta_id}")
            return None

        db = get_dynamodb_connection()
        table = db.Table("Contas")

        valor = Decimal(str(valor))

        # Atualizar saldo com base na operação
        if operacao == "credito":
            novo_saldo = conta.get("saldo", Decimal("0")) + valor
        else:  # debito
            novo_saldo = conta.get("saldo", Decimal("0")) - valor

            # Validar saldo suficiente para débito
            if novo_saldo < 0:
                logger.warning(
                    f"Saldo insuficiente para débito: {conta_id}, "
                    f"atual: {conta.get('saldo')}, valor: {valor}"
                )
                raise ValueError(
                    f"Insufficient balance. Current: {conta.get('saldo')}, "
                    f"Required: {valor}"
                )

        # Atualizar no DynamoDB
        response = table.update_item(
            Key={"user_id": user_id, "conta_id": conta_id},
            UpdateExpression="SET saldo = :novo_saldo, atualizado_em = :atualizado_em",
            ExpressionAttributeValues={
                ":novo_saldo": novo_saldo,
                ":atualizado_em": datetime.now(timezone.utc).isoformat(),
            },
            ReturnValues="ALL_NEW",
        )

        updated_conta = response.get("Attributes", {})
        logger.info(
            f"Saldo da conta atualizado: {conta_id} para o usuário {user_id}, "
            f"operação: {operacao}, valor: {valor}, novo saldo: {novo_saldo}"
        )

        return updated_conta

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao atualizar saldo da conta: {str(e)}")
        raise
    except ValueError as e:
        logger.warning(f"Erro de validação ao atualizar saldo da conta: {str(e)}")
        raise
