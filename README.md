# Ledger Financeiro

API REST de gerenciamento financeiro pessoal com **sistema de auditoria criptográfica** — o foco principal do projeto.

Cada transação gera um registro de auditoria protegido por **HMAC-SHA256**. Periodicamente, uma **Merkle Tree** é construída sobre toda a cadeia de auditoria e seu hash raiz é persistido como snapshot. Qualquer adulteração retroativa — seja de valor, tipo ou qualquer campo — é detectada na próxima verificação do snapshot, pois a raiz da árvore muda.

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Framework | FastAPI + Uvicorn |
| Banco de dados | AWS DynamoDB (local via Docker) |
| Autenticação | JWT (PyJWT) + bcrypt |
| Auditoria | HMAC-SHA256 + Merkle Tree |
| Cotações | API BCB/PTAX (Banco Central) |
| Testes | pytest + pytest-cov + moto (mock DynamoDB) |
| Containerização | Docker + Docker Compose |

## Como funciona a auditoria

Este é o núcleo do projeto. São três camadas trabalhando juntas:

### 1. HMAC-SHA256 por registro

Cada vez que uma transação é criada ou deletada, um registro de auditoria é gerado contendo os dados da operação. O HMAC é calculado sobre o conteúdo do registro usando uma chave secreta (`HMAC_SECRET`):

```
hmac = HMAC-SHA256(chave_secreta, dados_do_registro)
```

Isso garante que ninguém pode modificar um registro de auditoria sem ter a chave — e mesmo quem tem a chave precisaria recalcular e substituir o hash, o que é detectado pela camada seguinte.

### 2. Hash chaining (encadeamento)

Cada registro de auditoria referencia o hash do registro anterior, formando uma cadeia:

```
hash_N = HMAC(chave, dados_N + hash_{N-1})
```

Alterar qualquer registro quebra todos os elos subsequentes da cadeia. O endpoint `/transacoes/auditoria/verificar-integridade` percorre a cadeia inteira e detecta qualquer inconsistência.

### 3. Merkle Tree + Snapshots

Periodicamente (ou sob demanda), uma Merkle Tree é construída sobre todos os registros de auditoria do usuário. O hash raiz da árvore é salvo como snapshot.

```
Registros de auditoria → folhas da árvore
          ┌────────────────────┐
          │    Merkle Root     │  ← salvo no snapshot
          ├─────────┬──────────┤
          │  H(AB)  │  H(CD)   │
          ├──┬──────┼──┬───────┤
          │H(A)│H(B)│H(C)│H(D) │  ← folhas = hashes dos registros
          └───┴────┴───┴───────┘
```

Ao verificar um snapshot, a árvore é reconstruída a partir dos registros atuais e a raiz é comparada com a raiz salva. Se qualquer registro foi adulterado, adicionado ou removido diretamente no banco, as raízes divergem — fraude detectada.

### Estrutura de um registro de auditoria

```json
{
  "audit_id": "aud_abc123",
  "user_id": "usr_xyz",
  "transacao_id": "txn_001",
  "acao": "criar",
  "dados_novos": {
    "valor": 100.00,
    "tipo": "deposito"
  },
  "hash": "e3b0c44298fc1c149afb...",
  "criado_em": "2026-03-25T14:30:00Z"
}
```

## Estrutura do projeto

```
ledger-financeiro/
├── app/
│   ├── main.py                         # Aplicação FastAPI e inicialização
│   ├── config.py                       # Configurações via variáveis de ambiente
│   ├── database/
│   │   ├── conexao.py                  # Conexão com DynamoDB
│   │   └── tabelas.py                  # Criação das tabelas
│   ├── middleware/
│   │   └── autenticacao.py             # Validação JWT e extração do usuário atual
│   ├── models/
│   │   ├── usuarios.py
│   │   ├── contas.py
│   │   ├── transacoes.py
│   │   ├── categorias.py
│   │   ├── orcamentos.py
│   │   ├── auditoria.py
│   │   └── snapshots.py
│   ├── schemas/                        # Schemas Pydantic de entrada/saída
│   │   └── (espelha models/)
│   ├── routers/
│   │   ├── usuarios.py                 # Registro, login, perfil
│   │   ├── contas.py                   # Contas bancárias
│   │   ├── transacoes.py               # Transações + trilha de auditoria
│   │   ├── categorias.py               # Categorias de gastos
│   │   ├── orcamentos.py               # Orçamentos por categoria
│   │   ├── cotacoes.py                 # Cotações de moedas via BCB/PTAX
│   │   ├── relatorios.py               # Relatórios financeiros
│   │   └── snapshots.py                # Snapshots Merkle Tree
│   ├── services/
│   │   ├── usuarios_service.py
│   │   ├── contas_service.py
│   │   ├── transacoes_service.py       # Hash chaining na criação de transações
│   │   ├── auditoria_service.py        # HMAC-SHA256 + verificação de integridade
│   │   ├── snapshot_service.py         # Merkle Tree + snapshots periódicos
│   │   ├── categorias_service.py
│   │   ├── orcamentos_service.py
│   │   ├── cotacoes_service.py         # Integração BCB/PTAX
│   │   └── relatorios_service.py
│   └── utils/
│       ├── merkle.py                   # Implementação da Merkle Tree
│       ├── seguranca.py                # JWT e bcrypt
│       └── validacoes.py               # Validadores de dados
├── tests/
│   ├── conftest.py                     # Fixtures (mock DynamoDB, cliente, auth)
│   ├── test_auditoria.py
│   ├── test_merkle.py
│   ├── test_snapshots.py
│   ├── test_transacoes.py
│   ├── test_contas.py
│   ├── test_usuarios.py
│   ├── test_relatorios.py
│   └── test_integracao.py              # Testes ponta a ponta incluindo detecção de fraude
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Instalação

### Com Docker (recomendado)

```bash
git clone <url-do-repositorio>
cd ledger-financeiro

cp .env.example .env
# Edite o .env com suas chaves secretas

docker-compose up --build
```

A API ficará disponível em `http://localhost:8000`
O DynamoDB Local ficará disponível em `http://localhost:8001`
A documentação interativa em `http://localhost:8000/docs`

### Sem Docker

```bash
pip install -r requirements.txt

# Em um terminal separado, sobe o DynamoDB Local
docker run -p 8001:8000 amazon/dynamodb-local

# Sobe a API
uvicorn app.main:app --reload --port 8000
```

## Variáveis de ambiente

| Variável | Descrição |
|----------|-----------|
| `DYNAMODB_ENDPOINT` | URL do DynamoDB (ex: `http://localhost:8001`) |
| `DYNAMODB_REGION` | Região AWS (ex: `us-east-1`) |
| `AWS_ACCESS_KEY_ID` | Chave de acesso AWS (pode ser fake no local) |
| `AWS_SECRET_ACCESS_KEY` | Chave secreta AWS (pode ser fake no local) |
| `JWT_SECRET` | Chave para assinar tokens JWT |
| `JWT_ALGORITHM` | Algoritmo JWT (padrão: `HS256`) |
| `TOKEN_EXPIRE_MINUTES` | Expiração do token em minutos (padrão: `30`) |
| `HMAC_SECRET` | Chave secreta para HMAC-SHA256 da auditoria |
| `BC_API_URL` | URL da API BCB/PTAX para cotações |
| `SNAPSHOT_INTERVAL_HOURS` | Intervalo de snapshots automáticos (padrão: `24`) |

## Endpoints

### Usuários

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/usuarios/registrar` | Registrar novo usuário | Não |
| POST | `/usuarios/login` | Autenticar e obter token JWT | Não |
| GET | `/usuarios/perfil` | Obter perfil do usuário logado | Sim |
| PUT | `/usuarios/perfil` | Atualizar perfil | Sim |

### Contas

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/contas` | Criar conta bancária | Sim |
| GET | `/contas` | Listar contas do usuário | Sim |
| GET | `/contas/{conta_id}` | Obter detalhes de uma conta | Sim |
| PUT | `/contas/{conta_id}` | Atualizar conta | Sim |
| DELETE | `/contas/{conta_id}` | Deletar conta | Sim |

### Transações

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/transacoes` | Criar transação (gera auditoria HMAC automaticamente) | Sim |
| GET | `/transacoes` | Listar transações (filtros: conta, categoria, período) | Sim |
| GET | `/transacoes/{transacao_id}` | Obter transação específica | Sim |
| DELETE | `/transacoes/{transacao_id}` | Deletar transação (soft delete + auditoria) | Sim |

### Auditoria

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/transacoes/auditoria/` | Listar toda a trilha de auditoria do usuário | Sim |
| GET | `/transacoes/auditoria/verificar-integridade` | Verificar HMAC de todos os registros da cadeia | Sim |
| GET | `/transacoes/auditoria/{transacao_id}` | Trilha de auditoria de uma transação específica | Sim |

### Snapshots (Merkle Tree)

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/snapshots/` | Criar snapshot da cadeia de auditoria agora | Sim |
| GET | `/snapshots/` | Listar snapshots recentes | Sim |
| GET | `/snapshots/{snapshot_id}` | Obter snapshot específico | Sim |
| POST | `/snapshots/{snapshot_id}/verificar` | Verificar integridade — compara raiz Merkle atual com a salva | Sim |

### Categorias e Orçamentos

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| POST | `/categorias` | Criar categoria | Sim |
| GET | `/categorias` | Listar categorias | Sim |
| PUT | `/categorias/{categoria_id}` | Atualizar categoria | Sim |
| DELETE | `/categorias/{categoria_id}` | Deletar categoria | Sim |
| POST | `/orcamentos` | Criar orçamento mensal por categoria | Sim |
| GET | `/orcamentos` | Listar orçamentos | Sim |

### Relatórios

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/relatorios/extrato` | Extrato de transações (filtro por conta e período) | Sim |
| GET | `/relatorios/gastos-por-categoria` | Soma de gastos agrupada por categoria | Sim |
| GET | `/relatorios/saldo` | Saldo total consolidado de todas as contas | Sim |
| GET | `/relatorios/resumo` | Resumo financeiro com receitas, despesas e saldo líquido | Sim |

### Cotações

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/cotacoes/dolar` | Cotação atual do USD via BCB/PTAX | Não |
| GET | `/cotacoes/euro` | Cotação atual do EUR via BCB/PTAX | Não |
| GET | `/cotacoes/historico?moeda=USD` | Histórico de cotações de uma moeda | Não |

## Exemplos de uso

### Registrar e autenticar

```bash
# Registrar
curl -X POST http://localhost:8000/usuarios/registrar \
  -H "Content-Type: application/json" \
  -d '{"email": "joao@example.com", "nome": "João Silva", "senha": "Senha123!"}'

# Login — retorna o JWT
curl -X POST http://localhost:8000/usuarios/login \
  -F "username=joao@example.com" \
  -F "password=Senha123!"
```

```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Criar conta e transação

```bash
export TOKEN="eyJ0eXAiOiJKV1QiLCJhbGc..."

# Criar conta
curl -X POST http://localhost:8000/contas \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"nome": "Conta Corrente", "tipo": "corrente", "saldo_inicial": 2000.00}'

# Criar transação (gera auditoria HMAC automaticamente)
curl -X POST http://localhost:8000/transacoes \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conta_id": "cnt_abc123",
    "categoria_id": "cat_xyz",
    "tipo": "deposito",
    "valor": 3000.00,
    "descricao": "Salário mensal",
    "data": "2026-03-25"
  }'
```

### Gastos por categoria

```bash
curl -X GET http://localhost:8000/relatorios/gastos-por-categoria \
  -H "Authorization: Bearer $TOKEN"
```

```json
[
  {
    "categoria_id": "uuid-da-categoria",
    "categoria": "Alimentação",
    "total": 470.00,
    "percentual": 100.0,
    "quantidade": 2
  }
]
```

### Cotações (sem autenticação)

```bash
curl http://localhost:8000/cotacoes/dolar
curl http://localhost:8000/cotacoes/euro
curl "http://localhost:8000/cotacoes/historico?moeda=USD"
```

```json
{
  "moeda": "USD",
  "compra": 5.78,
  "venda": 5.79,
  "data": "2026-03-25T13:00:00",
  "fonte": "BCB PTAX"
}
```

> O campo `fonte` indica a origem dos dados: `"BCB PTAX"` quando a API do Banco Central respondeu com sucesso, ou `"fallback"` quando a API está indisponível (taxas de referência são usadas automaticamente).

### Verificar integridade da cadeia HMAC

```bash
curl -X GET http://localhost:8000/transacoes/auditoria/verificar-integridade \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "integra": true,
  "total_registros": 12,
  "registros_com_erro": []
}
```

### Criar e verificar snapshot Merkle

```bash
# Criar snapshot
curl -X POST http://localhost:8000/snapshots/ \
  -H "Authorization: Bearer $TOKEN"

# Resposta
{
  "snapshot_id": "snap_001",
  "merkle_root": "a3f5c2d1...",
  "total_registros": 12,
  "criado_em": "2026-03-25T15:00:00Z"
}

# Verificar snapshot (detecta adulterações posteriores à criação)
curl -X POST http://localhost:8000/snapshots/snap_001/verificar \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "valido": false,
  "merkle_root_snapshot": "a3f5c2d1...",
  "merkle_root_atual":    "9b4e1f22...",
  "total_registros_atual": 13,
  "mensagem": "Divergência detectada — cadeia de auditoria alterada após o snapshot."
}
```

## Testes

```bash
# Executar todos os testes
pytest

# Com cobertura de código
pytest --cov=app tests/

# Saída detalhada
pytest -v

# Apenas testes de auditoria e segurança
pytest tests/test_auditoria.py tests/test_merkle.py tests/test_snapshots.py tests/test_integracao.py -v
```

Os testes usam `moto` para mockar o DynamoDB localmente — não é necessário nenhum serviço rodando para executar a suíte.

## Licença

MIT
