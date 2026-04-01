"""
Serviço de orçamentos - lida com a lógica de negócios para orçamentos.

Funções:
    criar_orcamento - Criar um novo orçamento
    listar_orcamentos - Listar todos os orçamentos de um usuário
    obter_status_orcamentos - Obter comparação entre orçamento e gastos reais
    deletar_orcamento - Deletar um orçamento
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from app.database.conexao import get_dynamodb_connection

logger = logging.getLogger(__name__)


class OrcamentosService:
    """Serviço para gerenciamento de orçamentos."""

    def criar_orcamento(self, user_id: str, dados: dict) -> dict:
        """
        Cria um novo orçamento.

        Args:
            user_id: ID do usuário.
            dados: Dados do orçamento com 'categoria_id', 'mes', 'ano', 'valor_limite'.

        Returns:
            dict: Registro do orçamento criado.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Orcamentos")

            orcamento_id = str(uuid4())
            now = datetime.now(timezone.utc).isoformat()

            orcamento = {
                "user_id": user_id,
                "orcamento_id": orcamento_id,
                "categoria_id": dados["categoria_id"],
                "valor_limite": Decimal(str(dados["valor_limite"])),
                "mes": dados["mes"],
                "ano": dados["ano"],
                "criado_em": now,
                "atualizado_em": now,
            }

            table.put_item(Item=orcamento)
            logger.info(f"Budget created: {orcamento_id} for user {user_id}")

            return {
                **orcamento,
                "valor_limite": float(orcamento["valor_limite"]),
            }

        except ClientError as e:
            logger.error(f"DynamoDB error creating budget: {str(e)}")
            raise

    def listar_orcamentos(self, user_id: str) -> list:
        """
        Lista todos os orçamentos de um usuário.

        Args:
            user_id: ID do usuário.

        Returns:
            list: Lista de orçamentos pertencentes ao usuário.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Orcamentos")

            response = table.query(
                KeyConditionExpression=Key("user_id").eq(user_id)
            )

            items = response.get("Items", [])
            return [
                {**item, "valor_limite": float(item["valor_limite"])}
                for item in items
            ]

        except ClientError as e:
            logger.error(f"DynamoDB error listing budgets: {str(e)}")
            return []

    def obter_status_orcamentos(self, user_id: str, mes: int, ano: int) -> list:
        """
        Obtém comparação entre orçamento e gastos reais para um mês/ano.

        Args:
            user_id: ID do usuário.
            mes: Mês (1-12).
            ano: Ano.

        Returns:
            list: Lista de entradas OrcamentoStatus.
        """
        try:
            from datetime import date
            from app.database.conexao import get_dynamodb_connection
            from boto3.dynamodb.conditions import Key as DKey

            db = get_dynamodb_connection()
            orc_table = db.Table("Orcamentos")
            trans_table = db.Table("Transacoes")

            # Usa mês/ano atual se não fornecidos
            hoje = date.today()
            mes = mes or hoje.month
            ano = ano or hoje.year

            # Obtém todos os orçamentos do usuário
            orc_response = orc_table.query(
                KeyConditionExpression=DKey("user_id").eq(user_id)
            )
            todos_orcamentos = orc_response.get("Items", [])

            # Filtra para o mês/ano solicitado
            orcamentos = [
                o for o in todos_orcamentos
                if o.get("mes") == mes and o.get("ano") == ano
            ]

            if not orcamentos:
                return []

            # Constrói prefixo para filtragem por data: "2026-03"
            mes_str = str(mes).zfill(2)
            prefixo_data = f"{ano}-{mes_str}"

            # Obtém todas as transações do usuário naquele mês
            trans_response = trans_table.query(
                KeyConditionExpression=DKey("user_id").eq(user_id)
            )
            todas_transacoes = trans_response.get("Items", [])

            # Filtra: não deletada, é saque, dentro do mês
            transacoes_mes = [
                t for t in todas_transacoes
                if not t.get("deletada", False)
                and t.get("tipo") == "saque"
                and t.get("criado_em", "").startswith(prefixo_data)
            ]

            # Soma gastos por categoria
            gasto_por_categoria: dict = {}
            for t in transacoes_mes:
                cat_id = t.get("categoria_id")
                if cat_id:
                    valor = float(t.get("valor", 0))
                    gasto_por_categoria[cat_id] = gasto_por_categoria.get(cat_id, 0.0) + valor

            # Constrói lista de status
            resultado = []
            for orc in orcamentos:
                limite = float(orc["valor_limite"])
                cat_id = orc["categoria_id"]
                gasto = gasto_por_categoria.get(cat_id, 0.0)
                percentual = round((gasto / limite * 100), 2) if limite > 0 else 0.0

                resultado.append({
                    "orcamento": {
                        "orcamento_id": orc["orcamento_id"],
                        "user_id": orc["user_id"],
                        "categoria_id": cat_id,
                        "valor_limite": limite,
                        "mes": orc["mes"],
                        "ano": orc["ano"],
                        "criado_em": orc["criado_em"],
                        "atualizado_em": orc["atualizado_em"],
                    },
                    "valor_gasto": gasto,
                    "percentual_utilizado": min(percentual, 100.0),
                })

            return resultado

        except ClientError as e:
            logger.error(f"DynamoDB error getting budget status: {str(e)}")
            return []

    def deletar_orcamento(self, user_id: str, orcamento_id: str) -> bool:
        """
        Deleta um orçamento.

        Args:
            user_id: ID do usuário (para autorização).
            orcamento_id: ID do orçamento.

        Returns:
            bool: True se a deleção foi bem-sucedida, False se o orçamento não foi encontrado.
        """
        try:
            db = get_dynamodb_connection()
            table = db.Table("Orcamentos")

            response = table.get_item(
                Key={"user_id": user_id, "orcamento_id": orcamento_id}
            )

            if "Item" not in response:
                logger.warning(f"Budget not found: {orcamento_id}")
                return False

            table.delete_item(
                Key={"user_id": user_id, "orcamento_id": orcamento_id}
            )

            logger.info(f"Budget deleted: {orcamento_id} for user {user_id}")
            return True

        except ClientError as e:
            logger.error(f"DynamoDB error deleting budget: {str(e)}")
            raise
