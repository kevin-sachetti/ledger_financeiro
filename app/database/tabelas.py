"""
Módulo de criação e gerenciamento de tabelas DynamoDB.

Define todas as tabelas para a aplicação de gestão financeira incluindo:
- Usuarios: Gerenciamento de contas de usuário
- Contas: Contas bancárias
- Transacoes: Transações financeiras
- Categorias: Categorias de transações
- Orcamentos: Planejamento orçamentário
- Auditoria: Trilha de auditoria de transações

Cada tabela é criada com esquemas de chave, índices e atributos apropriados.
"""

import logging
from typing import Any, Optional

from app.database.conexao import get_dynamodb_connection

logger = logging.getLogger(__name__)


class TabelasDynamoDB:
    """
    Gerenciador para criação e configuração de tabelas DynamoDB.

    Fornece métodos para criar todas as tabelas necessárias com
    esquemas de chave, índices e configurações de cobrança adequados.
    """

    def __init__(self) -> None:
        """Inicializa o gerenciador de tabelas com a conexão DynamoDB."""
        self.dynamodb: Any = get_dynamodb_connection()

    def criar_tabela_usuarios(self) -> bool:
        """
        Cria a tabela Usuarios para gerenciamento de contas de usuário.

        Estrutura da Tabela:
            - PK: user_id (String)
            - GSI: email (para consultas baseadas em email)
            - Atributos: email, nome, cpf, data_criacao, ativo

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Usuarios",
                KeySchema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "email", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "email-index",
                        "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Usuarios' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Usuarios' já existe")
            return False

    def criar_tabela_contas(self) -> bool:
        """
        Cria a tabela Contas para gerenciamento de contas bancárias.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: conta_id (String)
            - Atributos: tipo, saldo, banco, agencia, numero, titular, ativa

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Contas",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "conta_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "conta_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Contas' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Contas' já existe")
            return False

    def criar_tabela_transacoes(self) -> bool:
        """
        Cria a tabela Transacoes para rastreamento de transações financeiras.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: transacao_id (String)
            - GSI: conta_id (para filtragem por conta)
            - GSI: categoria_id (para filtragem por categoria)
            - Atributos: tipo, valor, descricao, data, conta_id, categoria_id

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Transacoes",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "transacao_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "transacao_id", "AttributeType": "S"},
                    {"AttributeName": "conta_id", "AttributeType": "S"},
                    {"AttributeName": "categoria_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "conta_id-index",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "conta_id", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    },
                    {
                        "IndexName": "categoria_id-index",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "categoria_id", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    },
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Transacoes' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Transacoes' já existe")
            return False

    def criar_tabela_categorias(self) -> bool:
        """
        Cria a tabela Categorias para gerenciamento de categorias de transações.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: categoria_id (String)
            - Atributos: nome, descricao, cor, tipo, ativa

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Categorias",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "categoria_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "categoria_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Categorias' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Categorias' já existe")
            return False

    def criar_tabela_orcamentos(self) -> bool:
        """
        Cria a tabela Orcamentos para gerenciamento de orçamentos.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: orcamento_id (String)
            - Atributos: categoria_id, valor_limite, periodo, data_inicio, data_fim, ativo

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Orcamentos",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "orcamento_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "orcamento_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Orcamentos' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Orcamentos' já existe")
            return False

    def criar_tabela_auditoria(self) -> bool:
        """
        Cria a tabela Auditoria para trilha de auditoria de transações.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: audit_id (String)
            - GSI: transacao_id (para rastreamento de transações específicas)
            - Atributos: transacao_id, tipo_operacao, dados_anteriores, dados_novos, data_mudanca, ip_usuario

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Auditoria",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "audit_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "audit_id", "AttributeType": "S"},
                    {"AttributeName": "transacao_id", "AttributeType": "S"},
                ],
                GlobalSecondaryIndexes=[
                    {
                        "IndexName": "transacao_id-index",
                        "KeySchema": [
                            {"AttributeName": "user_id", "KeyType": "HASH"},
                            {"AttributeName": "transacao_id", "KeyType": "RANGE"},
                        ],
                        "Projection": {"ProjectionType": "ALL"},
                        "ProvisionedThroughput": {
                            "ReadCapacityUnits": 5,
                            "WriteCapacityUnits": 5,
                        },
                    }
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Auditoria' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Auditoria' já existe")
            return False

    def criar_tabela_snapshots(self) -> bool:
        """
        Cria a tabela Snapshots para snapshots da cadeia de auditoria com Árvore de Merkle.

        Estrutura da Tabela:
            - PK: user_id (String)
            - SK: snapshot_id (String)
            - Atributos: merkle_root, total_registros, audit_ids,
                          criado_em, intervalo_horas, status, detalhes

        Returns:
            bool: True se a tabela foi criada com sucesso, False se já existe
        """
        try:
            table = self.dynamodb.create_table(
                TableName="Snapshots",
                KeySchema=[
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "snapshot_id", "KeyType": "RANGE"},
                ],
                AttributeDefinitions=[
                    {"AttributeName": "user_id", "AttributeType": "S"},
                    {"AttributeName": "snapshot_id", "AttributeType": "S"},
                ],
                BillingMode="PAY_PER_REQUEST",
            )
            table.wait_until_exists()
            print("Tabela 'Snapshots' criada com sucesso")
            return True
        except self.dynamodb.meta.client.exceptions.ResourceInUseException:
            print("Tabela 'Snapshots' já existe")
            return False

    def criar_todas_tabelas(self) -> bool:
        """
        Cria todas as tabelas DynamoDB necessárias.

        Tenta criar todas as tabelas e retorna o status de sucesso.
        Se as tabelas já existirem, elas são ignoradas.

        Returns:
            bool: True se todas as tabelas foram criadas ou já existem com sucesso
        """
        print("Iniciando criação de tabelas DynamoDB...")

        tables_created = [
            self.criar_tabela_usuarios(),
            self.criar_tabela_contas(),
            self.criar_tabela_transacoes(),
            self.criar_tabela_categorias(),
            self.criar_tabela_orcamentos(),
            self.criar_tabela_auditoria(),
            self.criar_tabela_snapshots(),
        ]

        print("Processo de criação de tabelas concluído")
        return all(tables_created) or any(tables_created)


def inicializar_banco_dados() -> Optional[bool]:
    """
    Inicializa todas as tabelas do banco de dados.

    Função de conveniência para criar todas as tabelas DynamoDB necessárias.
    Chamada durante a inicialização da aplicação.

    Returns:
        Optional[bool]: True se bem-sucedido, False caso contrário
    """
    try:
        tabelas = TabelasDynamoDB()
        return tabelas.criar_todas_tabelas()
    except Exception as e:
        print(f"Erro ao inicializar banco de dados: {str(e)}")
        return False
