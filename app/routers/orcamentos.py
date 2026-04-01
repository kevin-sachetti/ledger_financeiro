"""
Orcamentos router - gerencia orçamentos.

Endpoints:
    POST / - Criar um novo orçamento
    GET / - Listar todos os orçamentos do usuário atual
    GET /status - Obter status de orçamento vs gastos reais
    DELETE /{orcamento_id} - Deletar um orçamento
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.orcamentos import (
    OrcamentoCreate,
    OrcamentoResponse,
    OrcamentoStatus,
)
from app.services.orcamentos_service import OrcamentosService

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos"])
orcamentos_service = OrcamentosService()


@router.post("/", response_model=OrcamentoResponse, status_code=status.HTTP_201_CREATED)
def criar_orcamento(
    orcamento_dados: OrcamentoCreate,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Criar um novo orçamento.

    Args:
        orcamento_dados: Dados do orçamento (categoria_id, mes, ano, valor_limite)
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        OrcamentoResponse: Dados do orçamento criado com orcamento_id

    Raises:
        HTTPException: 400 se os dados do orçamento forem inválidos
        HTTPException: 404 se categoria_id não for encontrada
    """
    novo_orcamento = orcamentos_service.criar_orcamento(
        user_id=usuario_atual["user_id"],
        dados=orcamento_dados.model_dump(),
    )

    return novo_orcamento


@router.get("/", response_model=list[OrcamentoResponse])
def listar_orcamentos(
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> list:
    """
    Listar todos os orçamentos do usuário atual.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        list[OrcamentoResponse]: Lista de orçamentos
    """
    orcamentos = orcamentos_service.listar_orcamentos(usuario_atual["user_id"])
    return orcamentos


@router.get("/status", response_model=list[OrcamentoStatus])
def obter_status_orcamentos(
    usuario_atual: dict = Depends(obter_usuario_atual),
    mes: int = Query(None, ge=1, le=12, description="Month (1-12)"),
    ano: int = Query(None, ge=2000, description="Year"),
) -> list:
    """
    Obter status de orçamento vs gastos reais.

    Compara limites de orçamento com transações reais em um determinado mês/ano.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência
        mes: Filtro opcional de mês (1-12), usa o mês atual se não fornecido
        ano: Filtro opcional de ano, usa o ano atual se não fornecido

    Returns:
        list[OrcamentoStatus]: Lista de entradas de status do orçamento com:
            - orcamento_id
            - categoria_id
            - categoria_nome
            - mes, ano
            - valor_limite
            - valor_gasto
            - percentual_usado
            - status (ok/alerta/excedido)
    """
    status_orcamentos = orcamentos_service.obter_status_orcamentos(
        user_id=usuario_atual["user_id"],
        mes=mes,
        ano=ano,
    )

    return status_orcamentos


@router.delete("/{orcamento_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_orcamento(
    orcamento_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> None:
    """
    Deletar um orçamento.

    Args:
        orcamento_id: ID do orçamento
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        None

    Raises:
        HTTPException: 404 se o orçamento não for encontrado ou não pertencer ao usuário
    """
    sucesso = orcamentos_service.deletar_orcamento(
        user_id=usuario_atual["user_id"],
        orcamento_id=orcamento_id,
    )

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Orçamento não encontrado",
        )
