"""
Camada de serviço para gerenciamento de snapshots de Árvore Merkle.

Fornece funções para:
- Criar snapshots sob demanda ou agendados da cadeia de auditoria.
- Verificar um snapshot anterior contra os registros de auditoria atuais.
- Listar e recuperar snapshots do DynamoDB.
- Executar um agendador em segundo plano que cria snapshots periodicamente.
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.config import settings
from app.database.conexao import get_dynamodb_connection
from app.utils.merkle import construir_arvore_auditoria, MerkleTree

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Funções auxiliares internas
# ---------------------------------------------------------------------------

def _sanitize_for_dynamodb(obj):
    """Converte recursivamente floats para Decimal para compatibilidade com DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _sanitize_for_dynamodb(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_for_dynamodb(i) for i in obj]
    return obj


def _buscar_todos_registros_auditoria(user_id: str) -> List[dict]:
    """
    Busca todos os registros de auditoria de um usuário no DynamoDB.

    Lida com paginação do DynamoDB para garantir que nenhum registro seja perdido.

    Args:
        user_id: Usuário alvo.

    Returns:
        Lista de dicts de registros de auditoria ordenados por audit_id (chave de ordenação).
    """
    db = get_dynamodb_connection()
    table = db.Table("Auditoria")
    registros: List[dict] = []

    kwargs = {"KeyConditionExpression": Key("user_id").eq(user_id)}
    while True:
        response = table.query(**kwargs)
        registros.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return registros


# ---------------------------------------------------------------------------
# API Pública
# ---------------------------------------------------------------------------

def criar_snapshot(user_id: str) -> dict:
    """
    Cria um snapshot de Árvore Merkle da cadeia de auditoria atual de um usuário.

    Etapas:
    1. Busca todos os registros de auditoria no DynamoDB.
    2. Constrói uma Árvore Merkle sobre os registros.
    3. Persiste o snapshot (hash raiz + metadados) na tabela Snapshots.

    Args:
        user_id: Usuário cujos registros de auditoria serão capturados no snapshot.

    Returns:
        dict: O registro do snapshot persistido.

    Raises:
        Exception: Se qualquer operação no DynamoDB falhar.
    """
    try:
        # 1. Busca todos os registros de auditoria
        registros = _buscar_todos_registros_auditoria(user_id)

        # 2. Constrói Árvore Merkle
        arvore: MerkleTree = construir_arvore_auditoria(registros)
        merkle_root = arvore.hash_raiz or ""
        audit_ids = [r.get("audit_id", "") for r in registros]

        # 3. Persiste snapshot
        db = get_dynamodb_connection()
        table = db.Table("Snapshots")

        snapshot_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        registro = _sanitize_for_dynamodb({
            "user_id": user_id,
            "snapshot_id": snapshot_id,
            "merkle_root": merkle_root,
            "total_registros": len(registros),
            "audit_ids": audit_ids,
            "criado_em": now,
            "intervalo_horas": settings.SNAPSHOT_INTERVAL_HOURS,
            "status": "ok",
            "detalhes": {
                "profundidade_arvore": arvore.profundidade,
                "total_folhas": len(arvore.folhas),
            },
        })

        table.put_item(Item=registro)
        logger.info(
            "Snapshot criado: %s para usuário %s | root=%s | registros=%d",
            snapshot_id,
            user_id,
            merkle_root,
            len(registros),
        )

        return registro

    except ClientError as e:
        logger.error("Erro DynamoDB ao criar snapshot: %s", str(e))
        raise


def verificar_snapshot(user_id: str, snapshot_id: str) -> dict:
    """
    Verifica um snapshot armazenado anteriormente contra os registros de auditoria atuais.

    Reconstrói a Árvore Merkle a partir dos dados de auditoria atuais e compara
    seu hash raiz com o hash raiz armazenado no snapshot. Uma divergência indica que
    registros de auditoria foram adicionados, removidos ou adulterados desde o snapshot.

    Args:
        user_id: Usuário cujo snapshot será verificado.
        snapshot_id: Identificador do snapshot a ser verificado.

    Returns:
        dict com chaves:
            - "valido" (bool): True se os registros atuais correspondem ao snapshot.
            - "snapshot_id" (str)
            - "merkle_root_snapshot" (str): Hash raiz armazenado no snapshot.
            - "merkle_root_atual" (str): Hash raiz calculado dos registros atuais.
            - "total_registros_snapshot" (int)
            - "total_registros_atual" (int)
            - "mensagem" (str): Resultado legível por humanos.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Snapshots")

        # Busca o snapshot armazenado
        response = table.get_item(
            Key={"user_id": user_id, "snapshot_id": snapshot_id}
        )
        snapshot = response.get("Item")
        if not snapshot:
            return {
                "valido": False,
                "snapshot_id": snapshot_id,
                "mensagem": "Snapshot não encontrado.",
            }

        merkle_root_armazenado = snapshot.get("merkle_root", "")
        total_snapshot = int(snapshot.get("total_registros", 0))

        # Reconstrói Árvore Merkle dos registros atuais
        registros_atuais = _buscar_todos_registros_auditoria(user_id)
        arvore_atual: MerkleTree = construir_arvore_auditoria(registros_atuais)
        merkle_root_atual = arvore_atual.hash_raiz or ""

        import hmac as _hmac
        valido = _hmac.compare_digest(merkle_root_armazenado, merkle_root_atual)

        mensagem = (
            "Cadeia de auditoria íntegra: o hash Merkle confere com o snapshot."
            if valido
            else "ATENÇÃO: o hash Merkle diverge do snapshot — possível adulteração detectada!"
        )

        logger.info(
            "Verificação de snapshot %s para usuário %s: valido=%s",
            snapshot_id,
            user_id,
            valido,
        )

        return {
            "valido": valido,
            "snapshot_id": snapshot_id,
            "merkle_root_snapshot": merkle_root_armazenado,
            "merkle_root_atual": merkle_root_atual,
            "total_registros_snapshot": total_snapshot,
            "total_registros_atual": len(registros_atuais),
            "mensagem": mensagem,
        }

    except ClientError as e:
        logger.error("Erro DynamoDB ao verificar snapshot: %s", str(e))
        raise


def listar_snapshots(user_id: str, limit: int = 20) -> List[dict]:
    """
    Lista os snapshots mais recentes de um usuário.

    Args:
        user_id: Usuário alvo.
        limit: Número máximo de snapshots a retornar (padrão 20).

    Returns:
        Lista de dicts de snapshot ordenados por data de criação decrescente.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Snapshots")

        response = table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            Limit=limit,
            ScanIndexForward=False,
        )
        snapshots = response.get("Items", [])
        logger.info(
            "Listados %d snapshots para usuário %s", len(snapshots), user_id
        )
        return snapshots

    except ClientError as e:
        logger.error("Erro DynamoDB ao listar snapshots: %s", str(e))
        return []


def obter_snapshot(user_id: str, snapshot_id: str) -> Optional[dict]:
    """
    Recupera um único snapshot pelo ID.

    Args:
        user_id: Proprietário do snapshot.
        snapshot_id: Identificador do snapshot.

    Returns:
        Dict do snapshot ou None se não encontrado.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Snapshots")
        response = table.get_item(
            Key={"user_id": user_id, "snapshot_id": snapshot_id}
        )
        return response.get("Item")
    except ClientError as e:
        logger.error("Erro DynamoDB ao obter snapshot: %s", str(e))
        return None


# ---------------------------------------------------------------------------
# Agendador em segundo plano
# ---------------------------------------------------------------------------

async def _loop_snapshots_periodicos(user_ids_fn, intervalo_horas: int) -> None:
    """
    Loop assíncrono em segundo plano que cria snapshots em intervalos regulares.

    Args:
        user_ids_fn: Callable sem argumentos que retorna uma lista de IDs de usuários ativos.
        intervalo_horas: Horas entre cada execução de snapshot.
    """
    intervalo_segundos = intervalo_horas * 3600
    logger.info(
        "Scheduler de snapshots iniciado (intervalo: %dh)", intervalo_horas
    )

    while True:
        await asyncio.sleep(intervalo_segundos)
        logger.info("Iniciando ciclo de snapshots periódicos...")

        try:
            user_ids = user_ids_fn()
        except Exception as exc:
            logger.error("Falha ao obter lista de usuários para snapshot: %s", exc)
            continue

        for uid in user_ids:
            try:
                snap = criar_snapshot(uid)
                logger.info(
                    "Snapshot periódico criado para usuário %s | root=%s",
                    uid,
                    snap.get("merkle_root", ""),
                )
            except Exception as exc:
                logger.error(
                    "Falha ao criar snapshot periódico para usuário %s: %s", uid, exc
                )


def _listar_todos_usuarios() -> List[str]:
    """
    Recupera todos os IDs de usuários ativos do DynamoDB para o job periódico de snapshot.

    Returns:
        Lista de strings user_id.
    """
    try:
        db = get_dynamodb_connection()
        table = db.Table("Usuarios")
        response = table.scan(ProjectionExpression="user_id")
        return [item["user_id"] for item in response.get("Items", [])]
    except Exception as exc:
        logger.error("Erro ao listar usuários para snapshot: %s", exc)
        return []


def iniciar_scheduler_snapshots() -> asyncio.Task:
    """
    Inicia a task em segundo plano de snapshots periódicos.

    Deve ser chamada uma vez durante a inicialização da aplicação (dentro do contexto lifespan).

    Returns:
        asyncio.Task para o loop em segundo plano em execução.
    """
    intervalo = settings.SNAPSHOT_INTERVAL_HOURS
    task = asyncio.create_task(
        _loop_snapshots_periodicos(_listar_todos_usuarios, intervalo)
    )
    logger.info(
        "Task de snapshots periódicos agendada (cada %dh)", intervalo
    )
    return task
