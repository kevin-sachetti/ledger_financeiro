"""
Relatorios router - gerencia relatórios financeiros e análises.

Endpoints:
    GET /extrato - Gerar extrato da conta
    GET /gastos-por-categoria - Obter gastos por categoria
    GET /saldo - Obter saldo total das contas
    GET /resumo - Obter resumo financeiro
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, status

from app.middleware.autenticacao import obter_usuario_atual
from app.schemas.relatorios import (
    ExtratoResposta,
    GastoCategoriaResposta,
    SaldoResposta,
    ResumoResposta,
)
from app.services import relatorios_service as relatorios_svc

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get("/extrato", response_model=ExtratoResposta)
def obter_extrato(
    usuario_atual: dict = Depends(obter_usuario_atual),
    conta_id: str | None = Query(None, description="Filter by specific account"),
    data_inicio: date | None = Query(None, description="Filter from start date"),
    data_fim: date | None = Query(None, description="Filter to end date"),
) -> dict:
    """
    Gerar um extrato de conta para transações.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência
        conta_id: ID da conta específica (opcional)
        data_inicio: Filtro de data de início (inclusivo, opcional)
        data_fim: Filtro de data de fim (inclusivo, opcional)

    Returns:
        ExtratoResposta: Extrato da conta com transações e resumo
    """
    extrato = relatorios_svc.gerar_extrato(
        user_id=usuario_atual["user_id"],
        conta_id=conta_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    return extrato


@router.get("/gastos-por-categoria", response_model=list[GastoCategoriaResposta])
def obter_gastos_por_categoria(
    usuario_atual: dict = Depends(obter_usuario_atual),
    mes: int = Query(None, ge=1, le=12, description="Month (1-12)"),
    ano: int = Query(None, ge=2000, description="Year"),
) -> list:
    """
    Obter detalhamento de gastos por categoria.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência
        mes: Filtro opcional de mês (1-12)
        ano: Filtro opcional de ano

    Returns:
        list[GastoCategoriaResposta]: Lista de categorias com valores gastos
    """
    gastos = relatorios_svc.gastos_por_categoria(
        user_id=usuario_atual["user_id"],
        mes=mes,
        ano=ano,
    )

    return gastos


@router.get("/saldo", response_model=SaldoResposta)
def obter_saldo_total(
    usuario_atual: dict = Depends(obter_usuario_atual),
) -> dict:
    """
    Obter saldo total de todas as contas.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência

    Returns:
        SaldoResposta: Saldo total e detalhamento por conta
    """
    saldo = relatorios_svc.obter_saldo_total(usuario_atual["user_id"])
    return saldo


@router.get("/resumo", response_model=ResumoResposta)
def obter_resumo_financeiro(
    usuario_atual: dict = Depends(obter_usuario_atual),
    mes: int = Query(None, ge=1, le=12, description="Month (1-12)"),
    ano: int = Query(None, ge=2000, description="Year"),
) -> dict:
    """
    Obter resumo financeiro completo.

    Args:
        usuario_atual: Usuário autenticado atual via injeção de dependência
        mes: Filtro opcional de mês (1-12)
        ano: Filtro opcional de ano

    Returns:
        ResumoResposta: Resumo com receitas, despesas, saldo e insights
    """
    resumo = relatorios_svc.resumo_financeiro(
        user_id=usuario_atual["user_id"],
        mes=mes,
        ano=ano,
    )

    return resumo
