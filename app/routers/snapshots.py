"""
Snapshot router para snapshots da cadeia de auditoria baseados em Merkle Tree.

Endpoints:
    POST   /snapshots/                    - Criar um novo snapshot imediatamente
    GET    /snapshots/                    - Listar snapshots recentes
    GET    /snapshots/{snapshot_id}       - Obter um snapshot específico
    POST   /snapshots/{snapshot_id}/verificar  - Verificar integridade do snapshot
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.autenticacao import obter_usuario_atual
from app.services import snapshot_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/snapshots",
    tags=["Snapshots"],
)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Criar snapshot da cadeia de auditoria",
    description=(
        "Cria um snapshot imediato da cadeia de auditoria do usuário autenticado, "
        "construindo uma Merkle Tree sobre todos os registros de auditoria existentes "
        "e armazenando o hash raiz para verificações futuras."
    ),
)
async def criar_snapshot(
    usuario_atual: Dict[str, Any] = Depends(obter_usuario_atual),
) -> dict:
    """Criar um snapshot Merkle Tree da cadeia de auditoria atual."""
    user_id = usuario_atual["user_id"]
    try:
        snapshot = snapshot_service.criar_snapshot(user_id)
        return {
            "mensagem": "Snapshot criado com sucesso.",
            "snapshot_id": snapshot["snapshot_id"],
            "merkle_root": snapshot["merkle_root"],
            "total_registros": snapshot["total_registros"],
            "criado_em": snapshot["criado_em"],
        }
    except Exception as exc:
        logger.error("Erro ao criar snapshot para usuário %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar snapshot.",
        )


@router.get(
    "/",
    summary="Listar snapshots",
    description="Retorna os snapshots mais recentes da cadeia de auditoria do usuário.",
)
async def listar_snapshots(
    limit: int = 20,
    usuario_atual: Dict[str, Any] = Depends(obter_usuario_atual),
) -> List[dict]:
    """Listar snapshots recentes do usuário autenticado."""
    user_id = usuario_atual["user_id"]
    try:
        return snapshot_service.listar_snapshots(user_id, limit=limit)
    except Exception as exc:
        logger.error("Erro ao listar snapshots para usuário %s: %s", user_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao listar snapshots.",
        )


@router.get(
    "/{snapshot_id}",
    summary="Obter snapshot específico",
    description="Retorna os detalhes de um snapshot pelo seu identificador.",
)
async def obter_snapshot(
    snapshot_id: str,
    usuario_atual: Dict[str, Any] = Depends(obter_usuario_atual),
) -> dict:
    """Obter um snapshot específico pelo ID."""
    user_id = usuario_atual["user_id"]
    try:
        snapshot = snapshot_service.obter_snapshot(user_id, snapshot_id)
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Snapshot '{snapshot_id}' não encontrado.",
            )
        return snapshot
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao obter snapshot %s: %s", snapshot_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao obter snapshot.",
        )


@router.post(
    "/{snapshot_id}/verificar",
    summary="Verificar integridade do snapshot",
    description=(
        "Reconstrói a Merkle Tree a partir dos registros de auditoria atuais e compara "
        "o hash raiz com o valor armazenado no snapshot. Uma divergência indica possível "
        "adulteração da cadeia de auditoria após o momento do snapshot."
    ),
)
async def verificar_snapshot(
    snapshot_id: str,
    usuario_atual: Dict[str, Any] = Depends(obter_usuario_atual),
) -> dict:
    """Verificar um snapshot comparando com os registros de auditoria atuais."""
    user_id = usuario_atual["user_id"]
    try:
        resultado = snapshot_service.verificar_snapshot(user_id, snapshot_id)
        if not resultado.get("valido") and "não encontrado" in resultado.get("mensagem", ""):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=resultado["mensagem"],
            )
        return resultado
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Erro ao verificar snapshot %s: %s", snapshot_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao verificar snapshot.",
        )
