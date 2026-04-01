"""
Camada de serviço para gerenciamento de transações financeiras.

Este módulo fornece funções para criar, recuperar, listar e deletar transações
na tabela DynamoDB Transacoes. Inclui validação de saldo, encadeamento de hash
e integração com trilha de auditoria.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.database.conexao import get_dynamodb_connection
from app.schemas.transacoes import TransacaoCreate
from app.services import auditoria_service, contas_service

logger = logging.getLogger(__name__)


def _generate_transaction_hash(dados: dict) -> str:
    """
    Gera hash SHA-256 dos dados da transação.

    Args:
        dados: Dicionário contendo os dados da transação para gerar o hash.

    Returns:
        str: Hash SHA-256 hexadecimal da representação JSON.
    """
    json_str = json.dumps(dados, sort_keys=True, default=str)
    return hashlib.sha256(json_str.encode()).hexdigest()


def _obter_ultima_transacao_hash(user_id: str) -> str | None:
    """
    Obtém o hash da última transação de um usuário.

    Consulta a tabela Transacoes para encontrar a transação mais recente
    e retorna seu hash para encadeamento.

    Args:
        user_id: O ID do usuário (chave primária).

    Returns:
        str: Hash da transação anterior, ou None se não houver transações anteriores.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Transacoes")

        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            Limit=1,
            ScanIndexForward=False,  # Obtém o mais recente (ordenação decrescente)
        )

        items = response.get("Items", [])
        if items:
            return items[0].get("hash")

        return None

    except ClientError as e:
        logger.error(f"Erro ao recuperar hash da última transação: {str(e)}")
        return None


def criar_transacao(user_id: str, dados: TransacaoCreate) -> dict:
    """
    Cria uma nova transação financeira.

    Valida que a conta existe e tem saldo suficiente para saques,
    atualiza o saldo da conta, gera hash da transação com encadeamento
    e cria registro na trilha de auditoria.

    Args:
        user_id: O ID do usuário (chave primária).
        dados: Schema TransacaoCreate contendo conta_id, categoria_id, tipo,
               valor, descricao e data.

    Returns:
        dict: O registro da transação criada com transacao_id, hash e metadados.

    Raises:
        ValueError: Se a conta não existir, saldo insuficiente ou validação falhar.
        Exception: Se a operação no DynamoDB falhar.
    """
    try:
        # Valida que a conta existe
        conta = contas_service.obter_conta(user_id, dados.conta_id)
        if not conta:
            logger.warning(f"Account not found: {dados.conta_id}")
            # Lança com marcador especial para distinguir de erros de validação
            error = ValueError(f"Account {dados.conta_id} not found")
            error.status_code = 404
            raise error

        # Valida que a conta está ativa
        if not conta.get("ativa", True):
            logger.warning(f"Account inactive: {dados.conta_id}")
            raise ValueError(f"Account {dados.conta_id} is inactive")

        # Converte valor para Decimal para precisão
        valor = Decimal(str(dados.valor))

        # Valida saldo para saque (tipo == "saque")
        if dados.tipo == "saque":
            saldo_atual = conta.get("saldo", Decimal("0"))
            if saldo_atual < valor:
                logger.warning(
                    f"Insufficient balance: {dados.conta_id}, "
                    f"current: {saldo_atual}, required: {valor}"
                )
                raise ValueError(
                    f"Insufficient balance. Current: {saldo_atual}, Required: {valor}"
                )

        db = get_dynamodb_connection()
        transacoes_table = db.Table("Transacoes")

        # Gera ID da transação e timestamps
        transacao_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Obtém hash da transação anterior para encadeamento
        hash_anterior = _obter_ultima_transacao_hash(user_id)

        # Converte data_transacao para string ISO se for datetime
        data_transacao_str = dados.data_transacao.isoformat() if hasattr(dados.data_transacao, 'isoformat') else str(dados.data_transacao)

        # Prepara dados para geração do hash (excluindo campos de hash)
        dados_para_hash = {
            "transacao_id": transacao_id,
            "user_id": user_id,
            "conta_id": dados.conta_id,
            "categoria_id": dados.categoria_id,
            "tipo": dados.tipo,
            "valor": str(valor),
            "descricao": dados.descricao,
            "data_transacao": data_transacao_str,
            "criado_em": now,
        }

        # Gera hash dos dados da transação
        hash_transacao = _generate_transaction_hash(dados_para_hash)

        # Prepara registro da transação
        transacao = {
            "user_id": user_id,
            "transacao_id": transacao_id,
            "conta_id": dados.conta_id,
            "tipo": dados.tipo,  # "deposito", "saque", "transferencia"
            "valor": valor,
            "descricao": dados.descricao,
            "data_transacao": data_transacao_str,
            "hash": hash_transacao,
            "hash_anterior": hash_anterior,
            "deletada": False,
            "criado_em": now,
            "atualizado_em": now,
        }
        # Inclui campos FK opcionais apenas quando não-nulos (GSI do DynamoDB rejeita valores nulos)
        if dados.categoria_id:
            transacao["categoria_id"] = dados.categoria_id
        if getattr(dados, "conta_destino_id", None):
            transacao["conta_destino_id"] = dados.conta_destino_id

        # Armazena transação no DynamoDB
        transacoes_table.put_item(Item=transacao)

        # Atualiza saldo da conta
        operacao = "credito" if dados.tipo == "deposito" else "debito"
        contas_service.atualizar_saldo(user_id, dados.conta_id, valor, operacao)

        # Cria registro na trilha de auditoria (apenas campos de negócio)
        dados_auditoria = {
            "transacao_id": transacao_id,
            "conta_id": dados.conta_id,
            "tipo": dados.tipo,
            "valor": str(valor),
            "descricao": dados.descricao,
            "data_transacao": data_transacao_str,
        }
        if dados.categoria_id:
            dados_auditoria["categoria_id"] = dados.categoria_id
        try:
            auditoria_service.criar_registro_auditoria(
                user_id=user_id,
                transacao_id=transacao_id,
                acao="criar",
                dados_anteriores=None,
                dados_novos=dados_auditoria,
            )
        except Exception as e:
            logger.warning(f"Falha ao criar registro de auditoria: {str(e)}")

        logger.info(
            f"Transaction created: {transacao_id} for user {user_id}, "
            f"account: {dados.conta_id}, type: {dados.tipo}, amount: {valor}"
        )

        # Transforma para resposta - mapeia campos internos para schema da API
        # Nota: Pydantic fará a conversão de string para datetime em criado_em e data_transacao
        return {
            "transacao_id": transacao["transacao_id"],
            "user_id": transacao["user_id"],
            "conta_id": transacao["conta_id"],
            "categoria_id": transacao.get("categoria_id"),
            "conta_destino_id": transacao.get("conta_destino_id"),
            "tipo": transacao["tipo"],
            "valor": float(transacao["valor"]),
            "descricao": transacao["descricao"],
            "data_transacao": str(transacao["data_transacao"]),
            "criado_em": str(transacao["criado_em"]),
            "hash_atual": transacao["hash"],
            "hash_anterior": transacao.get("hash_anterior"),
            "status": "deletada" if transacao.get("deletada") else "criada",
        }

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao criar transação: {str(e)}")
        raise
    except ValueError as e:
        logger.warning(f"Erro de validação ao criar transação: {str(e)}")
        raise


def listar_transacoes(
    user_id: str,
    conta_id: str | None = None,
    categoria_id: str | None = None,
    data_inicio: str | None = None,
    data_fim: str | None = None,
) -> list:
    """
    Lista transações financeiras com filtros opcionais.

    Consulta a tabela Transacoes para transações do usuário, opcionalmente filtradas
    por conta, categoria e intervalo de datas. Exclui transações soft-deleted.

    Args:
        user_id: O ID do usuário (chave primária).
        conta_id: ID da conta opcional para filtrar (usa GSI ContaIndex).
        categoria_id: ID da categoria opcional para filtrar (usa GSI CategoriaIndex).
        data_inicio: Data inicial opcional em formato ISO para filtragem.
        data_fim: Data final opcional em formato ISO para filtragem.

    Returns:
        list: Lista de registros de transações correspondentes aos critérios.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Transacoes")

        # Estratégia de consulta depende dos filtros fornecidos
        if conta_id:
            # Usa GSI conta_id-index
            response = table.query(
                IndexName="conta_id-index",
                KeyConditionExpression=Key("user_id").eq(user_id) & Key("conta_id").eq(conta_id),
            )
            transacoes = response.get("Items", [])

        elif categoria_id:
            # Usa GSI categoria_id-index
            response = table.query(
                IndexName="categoria_id-index",
                KeyConditionExpression=Key("user_id").eq(user_id) & Key("categoria_id").eq(categoria_id),
            )
            transacoes = response.get("Items", [])

        else:
            # Consulta tabela principal por user_id
            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id),
            )
            transacoes = response.get("Items", [])

        # Filtra transações soft-deleted
        transacoes = [t for t in transacoes if not t.get("deletada", False)]

        # Aplica filtros de intervalo de datas se fornecidos
        if data_inicio or data_fim:
            transacoes = [
                t for t in transacoes
                if (
                    (data_inicio is None or t.get("data_transacao", "") >= data_inicio)
                    and (data_fim is None or t.get("data_transacao", "") <= data_fim)
                )
            ]

        logger.info(
            f"Retrieved {len(transacoes)} transactions for user {user_id}"
            f"{f' (account: {conta_id})' if conta_id else ''}"
            f"{f', (category: {categoria_id})' if categoria_id else ''}"
        )

        # Transforma resposta para corresponder ao schema da API
        return [
            {
                "transacao_id": t["transacao_id"],
                "user_id": t["user_id"],
                "conta_id": t["conta_id"],
                "categoria_id": t.get("categoria_id"),
                "conta_destino_id": t.get("conta_destino_id"),
                "tipo": t["tipo"],
                "valor": float(t["valor"]),
                "descricao": t["descricao"],
                "data_transacao": str(t["data_transacao"]),
                "criado_em": str(t["criado_em"]),
                "hash_atual": t.get("hash", t.get("hash_atual", "")),
                "hash_anterior": t.get("hash_anterior"),
                "status": "deletada" if t.get("deletada") else "criada",
            }
            for t in transacoes
        ]

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao listar transações: {str(e)}")
        return []


def obter_transacao(user_id: str, transacao_id: str) -> dict | None:
    """
    Recupera uma transação específica pelo ID.

    Args:
        user_id: O ID do usuário (chave primária).
        transacao_id: O ID da transação (chave de ordenação).

    Returns:
        dict: O registro da transação se encontrado e não deletado, None caso contrário.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Transacoes")

        response = table.get_item(
            Key={"user_id": user_id, "transacao_id": transacao_id}
        )

        if "Item" not in response:
            logger.warning(f"Transaction not found: {transacao_id}")
            return None

        transacao = response["Item"]

        # Retorna None se a transação foi soft-deleted
        if transacao.get("deletada", False):
            logger.warning(f"Transaction is deleted: {transacao_id}")
            return None

        # Transforma resposta para corresponder ao schema da API
        return {
            "transacao_id": transacao["transacao_id"],
            "user_id": transacao["user_id"],
            "conta_id": transacao["conta_id"],
            "categoria_id": transacao.get("categoria_id"),
            "conta_destino_id": transacao.get("conta_destino_id"),
            "tipo": transacao["tipo"],
            "valor": float(transacao["valor"]),
            "descricao": transacao["descricao"],
            "data_transacao": str(transacao["data_transacao"]),
            "criado_em": str(transacao["criado_em"]),
            "hash_atual": transacao["hash"],
            "hash_anterior": transacao.get("hash_anterior"),
            "status": "deletada" if transacao.get("deletada") else "criada",
        }

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao recuperar transação: {str(e)}")
        return None


def deletar_transacao(user_id: str, transacao_id: str) -> bool:
    """
    Deleta uma transação (soft delete marcando como deletada).

    Marca a transação como deletada, reverte a alteração de saldo e cria
    registro de auditoria. Não remove o registro para preservar trilhas de auditoria.

    Args:
        user_id: O ID do usuário (chave primária).
        transacao_id: O ID da transação (chave de ordenação).

    Returns:
        bool: True se a deleção foi bem-sucedida, False se a transação não foi encontrada.

    Raises:
        Exception: Se a operação no DynamoDB falhar.
    """
    try:
        # Obtém transação para verificar que existe
        transacao = obter_transacao(user_id, transacao_id)
        if not transacao:
            logger.warning(f"Transaction not found for deletion: {transacao_id}")
            return False

        db = get_dynamodb_connection()
        transacoes_table = db.Table("Transacoes")
        now = datetime.now(timezone.utc).isoformat()

        # Armazena estado anterior para auditoria
        dados_anteriores = transacao.copy()

        # Marca como deletada
        transacoes_table.update_item(
            Key={"user_id": user_id, "transacao_id": transacao_id},
            UpdateExpression="SET deletada = :deletada, atualizado_em = :atualizado_em",
            ExpressionAttributeValues={
                ":deletada": True,
                ":atualizado_em": now,
            },
        )

        # Reverte a alteração de saldo
        conta_id = transacao.get("conta_id")
        valor = transacao.get("valor", Decimal("0"))
        tipo = transacao.get("tipo")

        # Reverte a operação (se foi depósito/crédito, debita; se saque/débito, credita)
        operacao_reversa = "debito" if tipo == "deposito" else "credito"
        contas_service.atualizar_saldo(user_id, conta_id, Decimal(str(valor)), operacao_reversa)

        # Cria registro na trilha de auditoria
        try:
            auditoria_service.criar_registro_auditoria(
                user_id=user_id,
                transacao_id=transacao_id,
                acao="deletar",
                dados_anteriores=dados_anteriores,
                dados_novos={"deletada": True},
            )
        except Exception as e:
            logger.warning(f"Falha ao criar registro de auditoria para deleção: {str(e)}")

        logger.info(
            f"Transaction deleted (soft): {transacao_id} for user {user_id}, "
            f"balance reversed for account {conta_id}"
        )

        return True

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao deletar transação: {str(e)}")
        raise
