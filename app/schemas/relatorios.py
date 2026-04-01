"""Schemas de relatório para validação de requisição/resposta."""

from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal


class ExtratoResposta(BaseModel):
    """Schema para resposta de extrato de conta.

    Atributos:
        transacoes: Lista de transações no extrato.
        total_receitas: Valor total de receitas.
        total_despesas: Valor total de despesas.
        saldo_liquido: Saldo líquido (receitas - despesas).
        periodo: Intervalo de datas do extrato.
        total_transacoes: Número de transações.
    """

    transacoes: List[dict]
    total_receitas: float
    total_despesas: float
    saldo_liquido: float
    periodo: dict
    total_transacoes: int


class GastoCategoriaResposta(BaseModel):
    """Schema para resposta de gastos por categoria.

    Atributos:
        categoria_id: Identificador da categoria.
        categoria: Nome da categoria.
        total: Valor total de gastos.
        percentual: Percentual do total de gastos.
        quantidade: Número de transações.
    """

    categoria_id: str
    categoria: str
    total: float
    percentual: float
    quantidade: int


class SaldoResposta(BaseModel):
    """Schema para resposta de saldo de conta.

    Atributos:
        saldo_total: Saldo total de todas as contas.
        saldos_por_moeda: Detalhamento de saldo por moeda.
        saldos_por_conta: Detalhamento de saldo por conta.
    """

    saldo_total: float
    saldos_por_moeda: dict
    saldos_por_conta: dict


class ResumoResposta(BaseModel):
    """Schema para resposta de resumo financeiro.

    Atributos:
        receitas: Total de receitas.
        despesas: Total de despesas.
        saldo: Saldo líquido.
        categorias_despesas: Detalhamento de gastos por categoria.
        contas: Dados resumidos das contas.
        periodo: Período de tempo do resumo.
    """

    receitas: float
    despesas: float
    saldo: float
    categorias_despesas: dict
    contas: dict
    periodo: dict
