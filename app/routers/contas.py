"""
Contas router - gerencia contas bancárias.

Endpoints:
    POST / - Criar uma nova conta
    GET / - Listar todas as contas do usuário
    GET /{conta_id} - Obter detalhes de uma conta específica
    PUT /{conta_id} - Atualizar informações da conta
    DELETE /{conta_id} - Deletar uma conta
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.contas import ContaCreate, ContaUpdate, ContaResponse
from app.services import contas_service

router = APIRouter(prefix="/contas", tags=["Contas"])


@router.post("/", response_model=ContaResponse, status_code=status.HTTP_201_CREATED)
def criar_conta(
    conta_dados: ContaCreate,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Criar uma nova conta bancária.

    Args:
        conta_dados: Dados da conta (nome, tipo, saldo_inicial)
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        ContaResponse: Dados da conta criada com conta_id

    Raises:
        HTTPException: 400 se os dados da conta forem inválidos
    """
    nova_conta = contas_service.criar_conta(
        user_id=usuario_atual["user_id"],
        dados=conta_dados,
    )

    return nova_conta


@router.get("/", response_model=list[ContaResponse])
def listar_contas_endpoint(usuario_atual: dict = Depends(obter_usuario_atual)) -> list:
    """
    Listar todas as contas do usuário atual.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        list[ContaResponse]: Lista de contas do usuário
    """
    contas = contas_service.listar_contas(usuario_atual["user_id"])
    return contas


@router.get("/{conta_id}", response_model=ContaResponse)
def obter_conta_endpoint(
    conta_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Obter detalhes de uma conta específica.

    Args:
        conta_id: ID da conta
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        ContaResponse: Detalhes da conta

    Raises:
        HTTPException: 404 se a conta não for encontrada ou não pertencer ao usuário
    """
    conta = contas_service.obter_conta(
        user_id=usuario_atual["user_id"],
        conta_id=conta_id,
    )

    if not conta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada",
        )

    return conta


@router.put("/{conta_id}", response_model=ContaResponse)
def atualizar_conta_endpoint(
    conta_id: str,
    conta_dados: ContaUpdate,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Atualizar informações da conta.

    Args:
        conta_id: ID da conta
        conta_dados: Dados atualizados da conta
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        ContaResponse: Dados da conta atualizada

    Raises:
        HTTPException: 404 se a conta não for encontrada ou não pertencer ao usuário
    """
    conta_atualizada = contas_service.atualizar_conta(
        user_id=usuario_atual["user_id"],
        conta_id=conta_id,
        dados=conta_dados,
    )

    if not conta_atualizada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada",
        )

    return conta_atualizada


@router.delete("/{conta_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_conta_endpoint(
    conta_id: str,
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> None:
    """
    Deletar uma conta.

    Args:
        conta_id: ID da conta
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        None

    Raises:
        HTTPException: 404 se a conta não for encontrada ou não pertencer ao usuário
    """
    sucesso = contas_service.deletar_conta(
        user_id=usuario_atual["user_id"],
        conta_id=conta_id,
    )

    if not sucesso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conta não encontrada",
        )
