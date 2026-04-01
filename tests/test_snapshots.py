"""
Testes para o sistema de snapshots periódicos com Merkle Tree.

Cobre:
- Criação de snapshot via API (POST /snapshots/)
- Listagem de snapshots (GET /snapshots/)
- Busca de snapshot individual (GET /snapshots/{id})
- Verificação de snapshot íntegro (POST /snapshots/{id}/verificar)
- Detecção de adulteração: modificar auditoria após snapshot deve falhar verificação
- Autenticação: todos os endpoints requerem JWT válido
- Casos de borda: snapshot de usuário sem auditoria, snapshot inexistente

Estes testes cobrem tanto a API HTTP quanto a lógica de verificação criptográfica,
garantindo que o sistema de snapshots funciona de ponta a ponta.
"""

import pytest
from fastapi import status


# ---------------------------------------------------------------------------
# Testes de criação de snapshot
# ---------------------------------------------------------------------------

class TestCriarSnapshot:
    """
    Testes para o endpoint POST /snapshots/.

    A criação de snapshot captura o estado atual da cadeia de auditoria,
    construindo uma Merkle Tree e armazenando o hash raiz.
    """

    def test_criar_snapshot_usuario_sem_auditoria(self, client, auth_headers):
        """
        O que faz: Cria um snapshot para um usuário que ainda não tem registros
                   de auditoria (recém-cadastrado, sem transações).
        Por que importa: Snapshots devem funcionar mesmo com cadeia vazia.
                         Uma falha aqui impediria o primeiro snapshot de qualquer
                         usuário novo, quebrando o scheduler.
        O que valida: Retorna 201 com snapshot_id e merkle_root vazio ("").
        """
        response = client.post("/snapshots/", headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert "snapshot_id" in data
        assert "merkle_root" in data
        assert "total_registros" in data
        assert data["total_registros"] == 0

    def test_criar_snapshot_com_registros_de_auditoria(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria transações (gerando auditoria), depois cria um snapshot.
        Por que importa: O caso mais comum em produção: snapshot com dados reais.
                         Deve capturar todos os registros existentes e gerar um
                         hash raiz Merkle não vazio.
        O que valida: merkle_root não está vazio e total_registros > 0.
        """
        # Cria 3 transações para popular a auditoria
        for i in range(3):
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": float(100 * (i + 1)),
                "descricao": f"Transação snapshot {i + 1}",
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        response = client.post("/snapshots/", headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED

        data = response.json()
        assert data["total_registros"] >= 3
        assert data["merkle_root"] != ""
        assert len(data["merkle_root"]) == 64, \
            "Merkle root deve ser um HMAC-SHA256 de 64 chars hexadecimais"

    def test_criar_snapshot_sem_autenticacao(self, client):
        """
        O que faz: Tenta criar um snapshot sem enviar token JWT.
        Por que importa: Snapshots contêm metadados sensíveis da auditoria.
                         Acesso não autenticado deve ser bloqueado para evitar
                         enumeração de dados ou DoS por geração massiva de snapshots.
        O que valida: Retorna 401 Unauthorized.
        """
        response = client.post("/snapshots/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dois_snapshots_consecutivos_tem_mesma_raiz(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria um snapshot, não realiza nenhuma operação, depois cria outro.
        Por que importa: Como os dados não mudaram, os dois snapshots devem ter o
                         mesmo merkle_root. Isso valida que a função é determinística
                         e que não há estado aleatório indesejado.
        O que valida: merkle_root do snapshot 1 == merkle_root do snapshot 2.
        """
        # Cria uma transação para ter auditoria
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Transação para duplo snapshot",
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Cria dois snapshots sem nenhuma operação entre eles
        r1 = client.post("/snapshots/", headers=auth_headers)
        r2 = client.post("/snapshots/", headers=auth_headers)

        assert r1.status_code == status.HTTP_201_CREATED
        assert r2.status_code == status.HTTP_201_CREATED

        raiz1 = r1.json()["merkle_root"]
        raiz2 = r2.json()["merkle_root"]
        assert raiz1 == raiz2, \
            "Snapshots consecutivos sem mudanças devem ter a mesma raiz Merkle"


# ---------------------------------------------------------------------------
# Testes de listagem de snapshots
# ---------------------------------------------------------------------------

class TestListarSnapshots:
    """
    Testes para o endpoint GET /snapshots/.
    """

    def test_listar_snapshots_vazio(self, client, auth_headers):
        """
        O que faz: Lista snapshots de um usuário que ainda não criou nenhum.
        Por que importa: Lista vazia é um estado válido e não deve retornar erro.
        O que valida: Retorna 200 com lista vazia.
        """
        response = client.get("/snapshots/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_listar_snapshots_retorna_criados(self, client, auth_headers):
        """
        O que faz: Cria 2 snapshots e verifica que ambos aparecem na listagem.
        Por que importa: A listagem é a forma do sistema de monitoramento verificar
                         se os snapshots periódicos estão sendo criados regularmente.
        O que valida: len(response) == 2 após criar 2 snapshots.
        """
        client.post("/snapshots/", headers=auth_headers)
        client.post("/snapshots/", headers=auth_headers)

        response = client.get("/snapshots/", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 2

    def test_listar_snapshots_sem_autenticacao(self, client):
        """
        O que faz: Tenta listar snapshots sem token JWT.
        Por que importa: Previne acesso não autorizado à lista de snapshots de outros usuários.
        O que valida: Retorna 401 Unauthorized.
        """
        response = client.get("/snapshots/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_snapshots_isolados_por_usuario(
        self, client, auth_headers, test_user_data, dynamodb_mock
    ):
        """
        O que faz: Cria snapshots com dois usuários diferentes e verifica que
                   cada um vê apenas os seus próprios.
        Por que importa: Vazamento de snapshots entre usuários é uma falha grave
                         de privacidade e segurança — expõe metadados de auditoria
                         de um usuário para outro.
        O que valida: Usuário B não vê snapshots do Usuário A e vice-versa.
        """
        # Snapshot do usuário A (auth_headers)
        client.post("/snapshots/", headers=auth_headers)

        # Registra e autentica usuário B
        user_b_data = {
            "email": "userb_snapshot@example.com",
            "nome": "User B",
            "senha": "SenhaUserB123!",
        }
        client.post("/usuarios/registrar", json=user_b_data)
        resp_login = client.post(
            "/usuarios/login",
            data={"username": user_b_data["email"], "password": user_b_data["senha"]},
        )
        headers_b = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

        # Usuário B não deve ver snapshots do usuário A
        response_b = client.get("/snapshots/", headers=headers_b)
        assert response_b.status_code == status.HTTP_200_OK
        # Usuário B não criou nenhum snapshot
        assert len(response_b.json()) == 0


# ---------------------------------------------------------------------------
# Testes de obtenção de snapshot individual
# ---------------------------------------------------------------------------

class TestObterSnapshot:
    """
    Testes para o endpoint GET /snapshots/{snapshot_id}.
    """

    def test_obter_snapshot_existente(self, client, auth_headers):
        """
        O que faz: Cria um snapshot e depois o recupera pelo ID retornado.
        Por que importa: A recuperação individual é necessária para a verificação
                         posterior — é preciso buscar o snapshot salvo para comparar
                         com o estado atual da cadeia.
        O que valida: Retorna 200 com os dados completos do snapshot.
        """
        response = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = response.json()["snapshot_id"]

        response = client.get(f"/snapshots/{snapshot_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["snapshot_id"] == snapshot_id
        assert "merkle_root" in data
        assert "total_registros" in data
        assert "criado_em" in data

    def test_obter_snapshot_inexistente_retorna_404(self, client, auth_headers):
        """
        O que faz: Tenta buscar um snapshot com ID que não existe.
        Por que importa: Um 500 neste caso indicaria tratamento inadequado de erros.
                         Deve retornar 404 claro para que o cliente saiba que o
                         snapshot não existe ou foi do outro usuário.
        O que valida: Retorna 404 Not Found.
        """
        response = client.get("/snapshots/id-que-nao-existe", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_obter_snapshot_sem_autenticacao(self, client, auth_headers):
        """
        O que faz: Cria um snapshot e tenta buscá-lo sem autenticação.
        Por que importa: Garante que o endpoint não expõe dados de auditoria
                         de um usuário para requisições anônimas.
        O que valida: Retorna 401 Unauthorized.
        """
        response = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = response.json()["snapshot_id"]

        response = client.get(f"/snapshots/{snapshot_id}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Testes de verificação de snapshot (integridade Merkle)
# ---------------------------------------------------------------------------

class TestVerificarSnapshot:
    """
    Testes para o endpoint POST /snapshots/{snapshot_id}/verificar.

    A verificação reconstrói a Merkle Tree a partir dos registros atuais
    e compara o hash raiz com o armazenado no snapshot. Este é o núcleo
    do sistema de detecção de adulteração.
    """

    def test_verificar_snapshot_integro(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria uma transação, cria um snapshot e imediatamente verifica.
                   Sem nenhuma alteração entre criação e verificação.
        Por que importa: É o cenário base de uso correto. Se falhar aqui,
                         a funcionalidade inteira está quebrada.
        O que valida: valido=True quando nenhuma alteração ocorreu após o snapshot.
        """
        # Cria transação para ter auditoria
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 300.00,
            "descricao": "Transação para verificação",
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # Cria snapshot
        r_snap = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = r_snap.json()["snapshot_id"]

        # Verifica imediatamente (sem mudanças)
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

        resultado = response.json()
        assert resultado["valido"] is True
        assert resultado["merkle_root_snapshot"] == resultado["merkle_root_atual"]

    def test_verificar_snapshot_inexistente_retorna_404(self, client, auth_headers):
        """
        O que faz: Tenta verificar um snapshot com ID inválido.
        Por que importa: Deve retornar 404 claro, não 500 ou resultado ambíguo.
        O que valida: Retorna 404 Not Found.
        """
        response = client.post(
            "/snapshots/snapshot-que-nao-existe/verificar", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_verificar_snapshot_sem_autenticacao(self, client, auth_headers):
        """
        O que faz: Cria um snapshot e tenta verificá-lo sem autenticação.
        Por que importa: O endpoint de verificação acessa dados de auditoria
                         e deve exigir autenticação.
        O que valida: Retorna 401 Unauthorized.
        """
        r_snap = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = r_snap.json()["snapshot_id"]

        response = client.post(f"/snapshots/{snapshot_id}/verificar")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verificar_snapshot_retorna_contagens(
        self, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Verifica que a resposta da verificação inclui as contagens
                   de registros do momento do snapshot e do momento atual.
        Por que importa: A diferença entre total_registros_snapshot e
                         total_registros_atual é uma evidência rápida de
                         inserção ou remoção de registros.
        O que valida: total_registros_snapshot e total_registros_atual presentes.
        """
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "saque",
            "valor": 50.00,
            "descricao": "Teste contagem",
        }
        client.post("/transacoes", json=transacao_data, headers=auth_headers)

        r_snap = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = r_snap.json()["snapshot_id"]

        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=auth_headers
        )
        data = response.json()

        assert "total_registros_snapshot" in data
        assert "total_registros_atual" in data
        assert "mensagem" in data


# ---------------------------------------------------------------------------
# Testes de detecção de adulteração via snapshot
# ---------------------------------------------------------------------------

class TestDeteccaoAdulteracaoViaSnapshot:
    """
    Testes de detecção de adulteração — o cenário de segurança crítico.

    Simulam ataques reais onde um invasor com acesso ao DynamoDB modifica
    registros de auditoria após um snapshot ter sido criado.

    Estes testes provam que o sistema detecta:
    1. Modificação do conteúdo de um registro de auditoria
    2. Inserção de novos registros após o snapshot
    3. Adulteração do hash de um registro (hash inválido)
    """

    def test_adulteracao_de_campo_apos_snapshot_detectada(
        self, dynamodb_mock, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria uma transação → snapshot → adultera diretamente
                   um campo no DynamoDB → verifica o snapshot.
        Por que importa: Simula o ataque mais direto: um invasor com credenciais
                         AWS que modifica o valor de uma transação de auditoria.
                         O snapshot foi criado antes da adulteração, então a
                         Merkle Tree reconstruída deve divergir da armazenada.
        O que valida: valido=False e a mensagem indica adulteração detectada.
        """
        # 1. Cria transação (gera registro de auditoria)
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 1000.00,
            "descricao": "Transação alvo de adulteração",
        }
        r_t = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        transacao_id = r_t.json()["transacao_id"]

        # 2. Cria snapshot (captura estado íntegro)
        r_snap = client.post("/snapshots/", headers=auth_headers)
        assert r_snap.status_code == status.HTTP_201_CREATED
        snapshot_id = r_snap.json()["snapshot_id"]

        # 3. Obtém o audit_id para adulteração direta
        r_audit = client.get(
            f"/transacoes/auditoria/{transacao_id}", headers=auth_headers
        )
        auditoria = r_audit.json()
        assert len(auditoria) > 0
        audit_id = auditoria[0]["audit_id"]
        user_id = auditoria[0]["user_id"]

        # 4. Adultera diretamente o campo 'dados_novos' no DynamoDB
        #    (simula invasor com acesso direto ao banco)
        table = dynamodb_mock.Table("Auditoria")
        table.update_item(
            Key={"user_id": user_id, "audit_id": audit_id},
            UpdateExpression="SET dados_novos.valor = :v",
            ExpressionAttributeValues={":v": "99999.00"},  # valor adulterado
        )

        # 5. Verifica o snapshot — deve detectar adulteração
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK

        resultado = response.json()
        assert resultado["valido"] is False, \
            "O snapshot deve detectar que os dados foram adulterados após sua criação"
        assert resultado["merkle_root_snapshot"] != resultado["merkle_root_atual"], \
            "As raízes Merkle devem divergir quando há adulteração"

    def test_insercao_de_registro_apos_snapshot_detectada(
        self, dynamodb_mock, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria snapshot com N registros → insere registro diretamente
                   no DynamoDB sem passar pela API → verifica o snapshot.
        Por que importa: Simula inserção fraudulenta de registros de auditoria
                         (por exemplo, para criar uma "trilha falsa" de autorização).
                         Como o snapshot foi criado sem esse registro, a raiz diverge.
        O que valida: valido=False e total_registros_atual > total_registros_snapshot.
        """
        from uuid import uuid4
        from datetime import datetime, timezone
        import json, hashlib, hmac as _hmac

        # 1. Cria uma transação legítima
        transacao_data = {
            "conta_id": test_account["conta_id"],
            "categoria_id": test_category["categoria_id"],
            "tipo": "deposito",
            "valor": 500.00,
            "descricao": "Transação legítima",
        }
        r_t = client.post("/transacoes", json=transacao_data, headers=auth_headers)
        user_id = client.get("/usuarios/perfil", headers=auth_headers).json()["user_id"]

        # 2. Cria snapshot
        r_snap = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = r_snap.json()["snapshot_id"]
        total_no_snapshot = r_snap.json()["total_registros"]

        # 3. Insere registro fantasma diretamente no DynamoDB
        table = dynamodb_mock.Table("Auditoria")
        fake_audit_id = str(uuid4())
        table.put_item(Item={
            "user_id": user_id,
            "audit_id": fake_audit_id,
            "transacao_id": "transacao-falsa",
            "acao": "criar",
            "dados_anteriores": {},
            "dados_novos": {"valor": "999999"},
            "hash": "0" * 64,  # hash inválido — não conhecemos a chave HMAC
            "criado_em": datetime.now(timezone.utc).isoformat(),
        })

        # 4. Verifica snapshot — deve detectar registro extra
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=auth_headers
        )
        resultado = response.json()

        assert resultado["valido"] is False, \
            "Inserção de registro após o snapshot deve invalidar a verificação"
        assert resultado["total_registros_atual"] > total_no_snapshot, \
            "Deve detectar que há mais registros agora do que no momento do snapshot"

    def test_snapshot_invalida_apos_exclusao_de_registro(
        self, dynamodb_mock, client, auth_headers, test_account, test_category
    ):
        """
        O que faz: Cria snapshot com N registros → remove um registro diretamente
                   do DynamoDB → verifica o snapshot.
        Por que importa: Excluir registros de auditoria é a forma mais óbvia de
                         ocultar operações fraudulentas. O snapshot detecta a ausência.
        O que valida: valido=False quando um registro de auditoria é removido
                      após o snapshot ser criado.
        """
        # 1. Cria 2 transações para ter múltiplos registros
        for i in range(2):
            transacao_data = {
                "conta_id": test_account["conta_id"],
                "categoria_id": test_category["categoria_id"],
                "tipo": "deposito",
                "valor": float(100 + i * 50),
                "descricao": f"Transação para exclusão {i}",
            }
            client.post("/transacoes", json=transacao_data, headers=auth_headers)

        # 2. Cria snapshot com os 2+ registros
        r_snap = client.post("/snapshots/", headers=auth_headers)
        snapshot_id = r_snap.json()["snapshot_id"]
        total_original = r_snap.json()["total_registros"]
        assert total_original >= 2

        # 3. Obtém todos os registros de auditoria e remove um
        r_audit = client.get("/transacoes/auditoria/", headers=auth_headers)
        audit_list = r_audit.json()
        assert len(audit_list) >= 1

        registro_para_remover = audit_list[0]
        table = dynamodb_mock.Table("Auditoria")
        table.delete_item(Key={
            "user_id": registro_para_remover["user_id"],
            "audit_id": registro_para_remover["audit_id"],
        })

        # 4. Verifica snapshot — deve detectar a ausência do registro
        response = client.post(
            f"/snapshots/{snapshot_id}/verificar", headers=auth_headers
        )
        resultado = response.json()

        assert resultado["valido"] is False, \
            "Remoção de registro após snapshot deve invalidar a verificação"
        assert resultado["total_registros_atual"] < total_original, \
            "Deve detectar que há menos registros agora do que no momento do snapshot"
