"""
Camada de serviço para relatórios financeiros e análises.

Fornece funções para extratos de conta, análise por categoria,
resumos de saldo e visões gerais financeiras abrangentes.
"""

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from app.database.conexao import get_dynamodb_connection

logger = logging.getLogger(__name__)


def gerar_extrato(
    user_id: str,
    conta_id: str | None = None,
    data_inicio=None,
    data_fim=None,
) -> dict:
    """Gera um extrato de conta com estatísticas resumidas."""
    try:
        db = get_dynamodb_connection()
        transacoes_table = db.Table("Transacoes")

        # Consulta transações do usuário
        response = transacoes_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        transacoes = response.get("Items", [])

        # Filtra deletadas
        transacoes = [t for t in transacoes if not t.get("deletada", False)]

        # Filtra por conta se especificada
        if conta_id:
            transacoes = [t for t in transacoes if t.get("conta_id") == conta_id]

        # Aplica filtros de intervalo de datas
        data_inicio_str = str(data_inicio) if data_inicio else None
        data_fim_str = str(data_fim) if data_fim else None

        if data_inicio_str or data_fim_str:
            filtered = []
            for t in transacoes:
                data = t.get("data_transacao", t.get("data", t.get("criado_em", "")))
                if data_inicio_str and str(data) < data_inicio_str:
                    continue
                if data_fim_str and str(data) > data_fim_str:
                    continue
                filtered.append(t)
            transacoes = filtered

        # Calcula resumo - deposito = receita, saque = despesa
        total_receitas = Decimal("0")
        total_despesas = Decimal("0")

        for t in transacoes:
            valor = t.get("valor", Decimal("0"))
            if isinstance(valor, (int, float)):
                valor = Decimal(str(valor))
            tipo = t.get("tipo", "")

            if tipo == "deposito":
                total_receitas += valor
            elif tipo == "saque":
                total_despesas += valor

        return {
            "transacoes": transacoes,
            "total_receitas": float(total_receitas),
            "total_despesas": float(total_despesas),
            "saldo_liquido": float(total_receitas - total_despesas),
            "periodo": {
                "data_inicio": data_inicio_str or "N/A",
                "data_fim": data_fim_str or "N/A",
            },
            "total_transacoes": len(transacoes),
        }

    except ClientError as e:
        logger.error(f"DynamoDB error generating statement: {e}")
        return {
            "transacoes": [],
            "total_receitas": 0.0,
            "total_despesas": 0.0,
            "saldo_liquido": 0.0,
            "periodo": {"data_inicio": "N/A", "data_fim": "N/A"},
            "total_transacoes": 0,
        }


def gastos_por_categoria(
    user_id: str, mes: int | None = None, ano: int | None = None
) -> list:
    """Gera análise de gastos agrupados por categoria."""
    try:
        db = get_dynamodb_connection()
        transacoes_table = db.Table("Transacoes")

        response = transacoes_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        transacoes = response.get("Items", [])

        # Filtra deletadas
        transacoes = [t for t in transacoes if not t.get("deletada", False)]

        # Filtra por período
        if mes or ano:
            filtered = []
            for t in transacoes:
                data_str = t.get("data_transacao", t.get("data", t.get("criado_em", "")))
                if not data_str:
                    continue
                try:
                    data = datetime.fromisoformat(str(data_str).split("T")[0])
                    if mes and data.month != mes:
                        continue
                    if ano and data.year != ano:
                        continue
                    filtered.append(t)
                except ValueError:
                    continue
            transacoes = filtered

        # Agrupa por categoria - saques são despesas
        categorias = defaultdict(lambda: {"total": Decimal("0"), "quantidade": 0})

        for t in transacoes:
            if t.get("tipo") == "saque":
                cat_id = t.get("categoria_id", "sem_categoria")
                valor = t.get("valor", Decimal("0"))
                if isinstance(valor, (int, float)):
                    valor = Decimal(str(valor))
                categorias[cat_id]["total"] += valor
                categorias[cat_id]["quantidade"] += 1

        total_geral = sum(c["total"] for c in categorias.values())

        # Busca nomes das categorias no DynamoDB
        categorias_table = db.Table("Categorias")
        nomes_categorias = {}
        for cat_id in categorias:
            try:
                resp = categorias_table.get_item(
                    Key={"user_id": user_id, "categoria_id": cat_id}
                )
                item = resp.get("Item")
                nomes_categorias[cat_id] = item["nome"] if item else cat_id
            except Exception:
                nomes_categorias[cat_id] = cat_id

        resultado = []
        for cat_id, data in categorias.items():
            pct = float(data["total"] / total_geral * 100) if total_geral > 0 else 0
            resultado.append({
                "categoria_id": cat_id,
                "categoria": nomes_categorias.get(cat_id, cat_id),
                "total": float(data["total"]),
                "percentual": round(pct, 2),
                "quantidade": data["quantidade"],
            })

        resultado.sort(key=lambda x: x["total"], reverse=True)
        return resultado

    except ClientError as e:
        logger.error(f"DynamoDB error analyzing spending: {e}")
        return []


def obter_saldo_total(user_id: str) -> dict:
    """Obtém saldo total de todas as contas."""
    try:
        db = get_dynamodb_connection()
        contas_table = db.Table("Contas")

        response = contas_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        contas = response.get("Items", [])
        contas = [c for c in contas if c.get("ativa", True)]

        saldos_por_moeda = defaultdict(Decimal)
        saldos_por_conta = {}

        for conta in contas:
            moeda = conta.get("moeda", "BRL")
            saldo = conta.get("saldo", Decimal("0"))
            if isinstance(saldo, (int, float)):
                saldo = Decimal(str(saldo))
            saldos_por_moeda[moeda] += saldo
            saldos_por_conta[conta.get("conta_id", "")] = {
                "nome": conta.get("nome", ""),
                "saldo": float(saldo),
                "moeda": moeda,
            }

        total = sum(float(v) for v in saldos_por_moeda.values())

        return {
            "saldo_total": total,
            "saldos_por_moeda": {k: float(v) for k, v in saldos_por_moeda.items()},
            "saldos_por_conta": saldos_por_conta,
        }

    except ClientError as e:
        logger.error(f"DynamoDB error retrieving balance: {e}")
        return {
            "saldo_total": 0.0,
            "saldos_por_moeda": {},
            "saldos_por_conta": {},
        }


def resumo_financeiro(
    user_id: str, mes: int | None = None, ano: int | None = None
) -> dict:
    """Gera resumo financeiro abrangente."""
    try:
        db = get_dynamodb_connection()
        transacoes_table = db.Table("Transacoes")

        response = transacoes_table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
        )
        transacoes = response.get("Items", [])
        transacoes = [t for t in transacoes if not t.get("deletada", False)]

        # Filtra por período
        periodo_str = "Todos os períodos"
        if mes and ano:
            periodo_str = f"{mes:02d}/{ano}"
            filtered = []
            for t in transacoes:
                data_str = t.get("data_transacao", t.get("data", t.get("criado_em", "")))
                if not data_str:
                    continue
                try:
                    data = datetime.fromisoformat(str(data_str).split("T")[0])
                    if data.month != mes or data.year != ano:
                        continue
                    filtered.append(t)
                except ValueError:
                    continue
            transacoes = filtered

        receitas = Decimal("0")
        despesas = Decimal("0")
        cat_despesas = defaultdict(Decimal)

        for t in transacoes:
            valor = t.get("valor", Decimal("0"))
            if isinstance(valor, (int, float)):
                valor = Decimal(str(valor))
            tipo = t.get("tipo", "")

            if tipo == "deposito":
                receitas += valor
            elif tipo == "saque":
                despesas += valor
                cat_id = t.get("categoria_id", "sem_categoria")
                cat_despesas[cat_id] += valor

        saldo = receitas - despesas
        saldo_info = obter_saldo_total(user_id)

        return {
            "receitas": float(receitas),
            "despesas": float(despesas),
            "saldo": float(saldo),
            "categorias_despesas": {k: float(v) for k, v in cat_despesas.items()},
            "contas": saldo_info.get("saldos_por_conta", {}),
            "periodo": {"descricao": periodo_str},
        }

    except ClientError as e:
        logger.error(f"DynamoDB error generating summary: {e}")
        return {
            "receitas": 0.0,
            "despesas": 0.0,
            "saldo": 0.0,
            "categorias_despesas": {},
            "contas": {},
            "periodo": {"descricao": "N/A"},
        }
