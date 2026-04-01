"""
Camada de serviço para gerenciamento de trilha de auditoria.

Este módulo fornece funções para criar e recuperar registros de auditoria que rastreiam
alterações em transações financeiras para fins de integridade e conformidade.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.config import settings
from app.database.conexao import get_dynamodb_connection

logger = logging.getLogger(__name__)


def _sanitize_for_dynamodb(obj):
    """Converter recursivamente floats para Decimal e garantir compatibilidade com DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _sanitize_for_dynamodb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_dynamodb(i) for i in obj]
    return obj


def _generate_audit_hash(dados: dict) -> str:
    """
    Gerar hash HMAC-SHA256 dos dados de auditoria.

    Usa HMAC com SHA-256 para criar um hash com chave que fornece tanto integridade
    quanto autenticidade dos dados. A chave secreta HMAC das configurações impede que
    um atacante forje hashes válidos mesmo que consiga ler os registros de auditoria armazenados.

    Decimal é serializado como float para garantir que o hash seja idêntico tanto na
    criação (onde os dados podem vir com float) quanto na verificação (onde o DynamoDB
    devolve Decimal), evitando falsos positivos de adulteração.

    Args:
        dados: Dicionário contendo os dados de auditoria para gerar o hash.

    Returns:
        str: Digest hexadecimal HMAC-SHA256 da representação JSON.
    """
    def _serializer(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)

    json_str = json.dumps(dados, sort_keys=True, default=_serializer)
    chave_secreta = settings.HMAC_SECRET.encode("utf-8")
    mac = hmac.new(chave_secreta, json_str.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def _verify_audit_hash(dados: dict, hash_armazenado: str) -> bool:
    """
    Verificar um hash HMAC-SHA256 dos dados de auditoria usando comparação em tempo constante.

    Args:
        dados: Dicionário contendo os dados de auditoria para verificar.
        hash_armazenado: Digest hexadecimal HMAC-SHA256 armazenado para comparação.

    Returns:
        bool: True se o hash corresponder (dados são autênticos), False caso contrário.
    """
    hash_calculado = _generate_audit_hash(dados)
    return hmac.compare_digest(hash_calculado, hash_armazenado)


def criar_registro_auditoria(
    user_id: str,
    transacao_id: str,
    acao: str,
    dados_anteriores: dict | None = None,
    dados_novos: dict | None = None,
) -> dict:
    """
    Criar um registro de auditoria para uma alteração de transação.

    Registra a ação, estados dos dados antes/depois, e gera um hash para
    verificação de integridade. Armazena na tabela Auditoria.

    Args:
        user_id: O ID do usuário (chave primária).
        transacao_id: O ID da transação sendo auditada (para vinculação).
        acao: Descrição da ação (ex.: "criar", "atualizar", "deletar").
        dados_anteriores: Estado anterior dos dados, se aplicável.
        dados_novos: Novo estado dos dados, se aplicável.

    Returns:
        dict: O registro de auditoria com audit_id, hash e metadados.

    Raises:
        Exception: Se a operação do DynamoDB falhar.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Auditoria")

        # Gerar ID de auditoria e timestamps
        audit_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Normalizar None → {} para que a entrada do hash corresponda exatamente ao que
        # é armazenado no DynamoDB (que não pode armazenar None em campos de dict).
        # Usar os valores normalizados aqui garante que recalcular o hash
        # durante a verificação de integridade sempre corresponda ao hash armazenado.
        dados_anteriores_norm = dados_anteriores or {}
        dados_novos_norm = dados_novos or {}

        # Preparar dados de auditoria para hashing
        dados_hash_input = {
            "transacao_id": transacao_id,
            "acao": acao,
            "dados_anteriores": dados_anteriores_norm,
            "dados_novos": dados_novos_norm,
            "timestamp": now,
        }

        # Gerar hash dos dados de auditoria
        dados_hash = _generate_audit_hash(dados_hash_input)

        # Preparar registro de auditoria (sanitizar floats para DynamoDB)
        registro = _sanitize_for_dynamodb({
            "user_id": user_id,
            "audit_id": audit_id,
            "transacao_id": transacao_id,
            "acao": acao,
            "dados_anteriores": dados_anteriores or {},
            "dados_novos": dados_novos or {},
            "hash": dados_hash,
            "criado_em": now,
        })

        # Armazenar no DynamoDB
        table.put_item(Item=registro)
        logger.info(
            f"Registro de auditoria criado: {audit_id} para transação {transacao_id} "
            f"(usuário: {user_id}, ação: {acao})"
        )

        return registro

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao criar registro de auditoria: {str(e)}")
        raise


def listar_auditoria(user_id: str, limit: int = 50) -> list:
    """
    Listar registros de auditoria recentes de um usuário.

    Consulta a tabela Auditoria por registros de auditoria pertencentes ao usuário,
    ordenados por data de criação (mais recente primeiro).

    Args:
        user_id: O ID do usuário (chave primária).
        limit: Número máximo de registros a retornar (padrão: 50).

    Returns:
        list: Lista de registros de auditoria ordenados por data de criação decrescente.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Auditoria")

        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            Limit=limit,
            ScanIndexForward=False,  # Ordenar decrescente por audit_id (mais recente primeiro)
        )

        registros = response.get("Items", [])
        logger.info(f"Recuperados {len(registros)} registros de auditoria para o usuário {user_id}")

        return registros

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao listar registros de auditoria: {str(e)}")
        return []


def obter_auditoria_transacao(user_id: str, transacao_id: str) -> list:
    """
    Recuperar todos os registros de auditoria para uma transação específica.

    Consulta a tabela Auditoria usando o GSI TransacaoIndex para encontrar todas
    as entradas de auditoria relacionadas a uma transação específica.

    Args:
        user_id: O ID do usuário (chave primária).
        transacao_id: O ID da transação para recuperar o histórico de auditoria.

    Returns:
        list: Lista de registros de auditoria da transação, lista vazia se não existirem.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Auditoria")

        response = table.query(
            IndexName="transacao_id-index",
            KeyConditionExpression=Key("user_id").eq(user_id) & Key("transacao_id").eq(transacao_id),
        )

        registros = response.get("Items", [])
        logger.info(
            f"Recuperados {len(registros)} registros de auditoria para a transação {transacao_id}"
        )

        return registros

    except ClientError as e:
        logger.error(
            f"Erro DynamoDB ao recuperar histórico de auditoria da transação: {str(e)}"
        )
        return []


def verificar_integridade_cadeia(user_id: str) -> dict:
    """
    Verificar a integridade da cadeia de auditoria de um usuário.

    Valida que todos os registros de auditoria possuem hashes corretos e que a cadeia
    de transações está íntegra. Retorna status detalhado de integridade.

    Args:
        user_id: O ID do usuário a verificar.

    Returns:
        dict: Resultado da verificação de integridade com:
            - "integra": bool indicando integridade geral da cadeia
            - "detalhes": dict com verificações realizadas e problemas encontrados
            - "total_registros": int total de registros de auditoria verificados
            - "registros_com_erro": lista de audit IDs com divergências de hash
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Auditoria")

        # Consultar todos os registros de auditoria do usuário
        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )

        registros = response.get("Items", [])

        # Verificar o hash de cada registro
        registros_com_erro = []
        for registro in registros:
            # Preparar dados para verificação de hash
            dados_hash_input = {
                "transacao_id": registro.get("transacao_id"),
                "acao": registro.get("acao"),
                "dados_anteriores": registro.get("dados_anteriores"),
                "dados_novos": registro.get("dados_novos"),
                "timestamp": registro.get("criado_em"),
            }

            actual_hash = registro.get("hash", "")

            if not _verify_audit_hash(dados_hash_input, actual_hash):
                registros_com_erro.append(
                    {
                        "audit_id": registro.get("audit_id"),
                        "criado_em": registro.get("criado_em"),
                        "motivo": "hash_invalido",
                    }
                )

        # Determinar integridade geral
        integra = len(registros_com_erro) == 0

        resultado = {
            "integra": integra,
            "mensagem": (
                "Cadeia de auditoria íntegra. Todos os registros verificados com sucesso."
                if integra
                else "ATENÇÃO: adulteração detectada. Um ou mais registros possuem hash inválido."
            ),
            "total_registros": len(registros),
            "registros_com_erro": registros_com_erro,
        }

        logger.info(
            f"Verificação de integridade da cadeia de auditoria para o usuário {user_id}: "
            f"integra={integra}, total={len(registros)}, erros={len(registros_com_erro)}"
        )

        return resultado

    except ClientError as e:
        logger.error(f"Erro DynamoDB ao verificar cadeia de auditoria: {str(e)}")
        return {
            "integra": False,
            "mensagem": "Erro ao verificar integridade da cadeia de auditoria.",
            "total_registros": 0,
            "registros_com_erro": [],
        }
