# Candidato

- **Nome:** Mateus Jorge Martins Goncalves
- **LinkedIn:** https://www.linkedin.com/in/mateusjorge28186/

# Sistema de Gerenciamento de Biblioteca Digital

## Overview

- API REST para biblioteca digital com **usuários, contas, catálogo, solicitações, empréstimos, devoluções, multas e renovações**.
- Foco em backend: **consistência transacional, controle de concorrência, autorização por perfis e regras de negócio centralizadas**.
- Arquitetura em camadas: **controller -> service -> repository**, com domínio separado de infraestrutura.
- Redis usado de forma pragmática para **cache, locks distribuídos e rate limiting**.
- Inclui testes automatizados, logs estruturados, métricas operacionais, notificações de vencimento e frontend demonstrativo.

## TL;DR

- **Stack:** Python 3.12, FastAPI, PostgreSQL, SQLAlchemy, Pydantic, Redis, Alembic, Pytest, Docker Compose, React/Vite.
- **Features principais:** autenticação JWT, RBAC (`admin`, `librarian`, `reader`), catálogo, empréstimos, solicitações, multas, renovações e notificações.
- **Diferenciais técnicos:** Redis locks, `SELECT FOR UPDATE`, transações, cache com invalidação, rate limiting por identidade, métricas e logs estruturados.
- **Setup local:** `make start` sobe API, PostgreSQL e Redis; Swagger em `http://localhost:8000/docs`.
- **Frontend:** console simples para demonstrar a API em funcionamento, sem pretensão de ser produto final.

## Destaques Técnicos

- **Controle de concorrência:** criação de empréstimos usa locks Redis por usuário/livro e bloqueio pessimista no banco com `SELECT FOR UPDATE`.
- **Consistência transacional:** criação, devolução e renovação alteram `Loan`, `Book` e `LoanRequest` de forma coordenada.
- **Arquitetura em camadas:** controllers finos, services com regra de negócio e repositories isolando queries.
- **Separação de domínio:** `User` representa o leitor da biblioteca; `Account` representa credencial, perfil e autenticação.
- **Fluxo de aprovação:** `LoanRequest` modela solicitações pendentes, aprovadas e rejeitadas; `Loan` só representa empréstimo efetivo.
- **Proteção contra abuso:** rate limiting com Redis por conta autenticada ou IP anônimo.
- **Cache com invalidação:** consultas frequentes de livros/autores usam TTL curto e invalidação em mudanças relevantes.
- **Observabilidade:** logs estruturados em JSON, health check, métricas operacionais e exportação CSV.

## Conexão com Cenários Reais

Embora o domínio seja uma biblioteca, o projeto modela problemas comuns em sistemas financeiros e operacionais:

- **Consistência:** evitar estados parciais, como livro indisponível sem empréstimo correspondente.
- **Concorrência:** impedir que duas requisições simultâneas emprestem o mesmo exemplar ou ultrapassem limites de usuário.
- **Rastreabilidade:** registrar eventos do fluxo de empréstimos para auditoria operacional.
- **Autorização:** separar ações de staff e leitor, validando permissões no backend.
- **Proteção contra abuso:** aplicar rate limit em rotas sensíveis como login, bootstrap e criação de recursos.
- **Degradação controlada:** se Redis falhar, cache/rate limit/locks degradam com log, sem derrubar imediatamente a API local do case.

## Índice

- [Como Rodar Localmente](#como-rodar-localmente)
- [Como Rodar os Testes](#como-rodar-os-testes)
- [Arquitetura](#arquitetura)
- [Modelo de Domínio](#modelo-de-domínio)
- [Regras e Fluxos de Empréstimo](#regras-e-fluxos-de-empréstimo)
- [Segurança, Autorização e Rate Limiting](#segurança-autorização-e-rate-limiting)
- [Consistência, Cache e Concorrência](#consistência-cache-e-concorrência)
- [Observabilidade](#observabilidade)
- [Notificações de Vencimento](#notificações-de-vencimento)
- [Banco de Dados e Migrations](#banco-de-dados-e-migrations)
- [Frontend Demonstrativo](#frontend-demonstrativo)
- [Endpoints Principais](#endpoints-principais)
- [Exemplos de Uso](#exemplos-de-uso)
- [Postman](#postman)
- [Padrão de Código](#padrão-de-código)
- [Decisões Arquiteturais e Trade-offs](#decisões-arquiteturais-e-trade-offs)
- [Melhorias Futuras](#melhorias-futuras)

## Como Rodar Localmente

### Pré-requisitos

- Docker
- Docker Compose
- Python 3.12 ou superior, caso rode fora do container
- Node.js `^20.19.0` ou `>=22.12.0` e npm 10+, caso rode o frontend

### Variáveis de Ambiente

Crie um `.env` a partir de `.env-example`.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/library
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/library_test
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT_ENABLED=true
LOG_PRETTY_JSON=true
CORS_ORIGINS=http://localhost:5173
DUE_LOAN_NOTIFICATIONS_ENABLED=false
DUE_LOAN_NOTIFICATION_INTERVAL_SECONDS=3600
DUE_LOAN_NOTIFICATION_DAYS_AHEAD=1
DUE_LOAN_WEBHOOK_URL=
```

### Subir API, Banco e Redis

```bash
make start
```

O container da API aplica as migrations antes de iniciar.

```text
API:     http://localhost:8000
Swagger: http://localhost:8000/docs
```

### Subir Apenas Banco e Redis

```bash
make db
```

### Rodar API Localmente com Virtualenv

```bash
make local
```

Se as dependências já estiverem instaladas:

```bash
make local-soft
```

Aplicar migrations:

```bash
make migrate
```

Criar nova migration:

```bash
make revision m="descricao_da_migration"
```

### Dados de Exemplo

```bash
make seed
```

O seed é idempotente e cria:

- conta `admin`;
- conta `librarian`;
- usuário da biblioteca;
- conta `reader` vinculada ao usuário;
- autores e livros disponíveis.

Credenciais locais:

| Perfil | Email | Senha |
| --- | --- | --- |
| `admin` | `admin@example.com` | `12345678` |
| `librarian` | `librarian@example.com` | `12345678` |
| `reader` | `reader-account@example.com` | `12345678` |

### Parar Containers

```bash
make stop
```

## Como Rodar os Testes

Suba o banco de teste e Redis:

```bash
make test_db
```

Execute a suíte:

```bash
pytest
```

Ou via Makefile:

```bash
make test
```

Cobertura:

```bash
make coverage
```

Lint e testes:

```bash
make check
```

### QA Manual

Também foi executado um roteiro manual cobrindo autenticação, autorização, usuários, catálogo, empréstimos, solicitações, métricas, health check, cache, rate limit e concorrência.

Relatório: [docs/manual-qa-report.md](docs/manual-qa-report.md).

## Arquitetura

O projeto usa arquitetura em camadas para separar entrada HTTP, regras de negócio e persistência.

```text
Request -> Controller -> Service -> Repository -> Database
                    \-> Schemas
                    \-> Core infrastructure
```

| Camada | Responsabilidade |
| --- | --- |
| `controllers` | Rotas FastAPI, dependências, autorização e tradução de exceções para HTTP. |
| `services` | Regras de negócio, transações, validações e orquestração. |
| `repositories` | Acesso a dados via SQLAlchemy. |
| `models` | Entidades ORM e relacionamentos. |
| `schemas` | Contratos Pydantic de entrada e saída. |
| `core` | Banco, segurança, cache, rate limit e logging. |

### Visão da API

```mermaid
flowchart TD
    Client[Cliente / Postman / Swagger / Frontend] --> API[FastAPI App]

    API --> Auth[JWT Auth]
    API --> RateLimit[Rate limiting]
    RateLimit --> Redis[(Redis)]

    API --> Controllers[Controllers]
    Controllers --> Schemas[Schemas Pydantic]
    Controllers --> Services[Services]

    Services --> Repositories[Repositories]
    Services --> Cache[Cache e locks]
    Cache --> Redis

    Repositories --> DB[(PostgreSQL)]
    Services --> Logs[Logs JSON]
```

### Fluxo em Camadas

```mermaid
flowchart LR
    Request[HTTP Request] --> Controller[Controller]
    Controller --> Service[Service]
    Service --> Repository[Repository]
    Repository --> Database[(PostgreSQL)]
    Service --> Redis[(Redis)]
    Controller --> Response[HTTP Response]
```

### Estrutura de Pastas

```text
app/
  controllers/     # Rotas HTTP por domínio
  core/            # Banco, JWT, Redis, rate limit e logging
  models/          # Modelos SQLAlchemy
  repositories/    # Queries e persistência
  schemas/         # Schemas Pydantic
  services/        # Regras de negócio
  dependencies.py  # Dependências FastAPI compartilhadas
  server.py        # Criação da app e routers
frontend/          # React/Vite demonstrativo
tests/             # Testes unitários, funcionais e integração
alembic/           # Migrations
docker-compose.yml # API, PostgreSQL, Redis e banco de teste
Makefile           # Comandos auxiliares
```

### SOLID de Forma Pragmática

| Princípio | Aplicação no projeto |
| --- | --- |
| Single Responsibility | Controllers, services, repositories, schemas e core têm responsabilidades separadas. |
| Open/Closed | Regras centralizadas facilitam evolução, embora novos tipos de solicitação ainda alterem o service principal. |
| Liskov | Pouco aplicável, sem hierarquias relevantes. |
| Interface Segregation | Separação por módulos e camadas sem interfaces artificiais. |
| Dependency Inversion | Parcial. Services usam repositories concretos por simplicidade do case; em produção poderia evoluir para ports/adapters. |

Trade-off: manter clareza e baixa complexidade para um tech case, sem criar arquitetura enterprise desnecessária.

## Modelo de Domínio

```mermaid
erDiagram
    USERS ||--o{ LOANS : has
    AUTHORS ||--o{ BOOKS : writes
    BOOKS ||--o{ LOANS : borrowed_in

    USERS ||--o| ACCOUNTS : linked_to

    ACCOUNTS ||--o{ LOAN_REQUESTS : requester
    ACCOUNTS ||--o{ LOAN_REQUESTS : reviewer
    USERS ||--o{ LOAN_REQUESTS : requests
    BOOKS ||--o{ LOAN_REQUESTS : requested_book
    LOANS ||--o{ LOAN_REQUESTS : requested_action
    LOANS ||--o{ LOAN_OPERATION_METRICS : observed_in
    LOAN_REQUESTS ||--o{ LOAN_OPERATION_METRICS : observed_in

    USERS {
        int id PK
        string name
        string email
        boolean is_active
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    ACCOUNTS {
        int id PK
        string name
        string email
        string password_hash
        string role
        int user_id FK
        boolean is_active
        datetime created_at
        datetime deleted_at
    }

    AUTHORS {
        int id PK
        string name
        datetime created_at
        datetime deleted_at
    }

    BOOKS {
        int id PK
        string isbn
        string title
        int author_id FK
        date published_date
        boolean is_available
        datetime created_at
        datetime deleted_at
    }

    LOANS {
        int id PK
        int user_id FK
        int book_id FK
        datetime loan_date
        datetime expected_return_date
        datetime actual_return_date
        float fine_value
        string status
        int renewal_count
    }

    LOAN_REQUESTS {
        int id PK
        string request_type
        string status
        int requester_account_id FK
        int reviewer_account_id FK
        int user_id FK
        int book_id FK
        int loan_id FK
        string rejection_reason
        datetime created_at
        datetime reviewed_at
    }
```

### Separações Importantes

- **`User` vs `Account`:** `User` é o leitor da biblioteca; `Account` é credencial, autenticação e autorização.
- **`reader` vs `user`:** o enunciado usa "user", mas a role pública é `reader` para não conflitar com a entidade `User`.
- **`LoanRequest` vs `Loan`:** solicitação é intenção pendente; empréstimo é operação efetivada.
- **`Book` e ISBN:** múltiplos exemplares podem compartilhar ISBN; disponibilidade é por exemplar, não por título.

### Catálogo e Histórico

A API não expõe endpoint público para alterar `isbn`, `title`, `author_id` ou `published_date` depois do cadastro. A decisão evita ambiguidade histórica: um empréstimo antigo não deveria passar a apontar para um livro com outro ISBN ou título. Para correção operacional, o fluxo previsto é remover logicamente e cadastrar novo registro.

## Regras e Fluxos de Empréstimo

### Regras de Negócio

- Prazo padrão: **14 dias**.
- Multa por atraso: **R$ 2,00 por dia completo**.
- Dias parciais não arredondam para cima.
- Máximo de **3 empréstimos ativos por usuário**.
- Livro indisponível não pode ser emprestado.
- Aprovação de empréstimo marca o livro como indisponível.
- Devolução marca o empréstimo como devolvido e libera o livro.
- Renovação é permitida apenas uma vez, para empréstimo ativo e não atrasado.
- Solicitações pendentes duplicadas para a mesma operação são bloqueadas.
- `reader` solicita; `admin` e `librarian` aprovam, rejeitam e executam operações diretas.

### Estados

| Entidade | Status | Significado |
| --- | --- | --- |
| `LoanRequest` | `pending` | Solicitação criada e aguardando staff. |
| `LoanRequest` | `approved` | Solicitação aprovada; a operação de domínio foi concluída. |
| `LoanRequest` | `rejected` | Solicitação rejeitada sem alterar livro/empréstimo. |
| `Loan` | `active` | Empréstimo efetivo ainda não devolvido. |
| `Loan` | `returned` | Empréstimo devolvido, com multa registrada quando houver. |

### Fluxos

```text
reader -> POST /loan-requests/ -> LoanRequest pending
staff  -> POST /loan-requests/{id}/approve -> Loan active
staff  -> POST /loan-requests/{id}/reject -> LoanRequest rejected
staff  -> PUT /loans/{id}/return -> Loan returned
reader -> POST /return-requests/ -> staff approve -> Loan returned
reader -> POST /renewal-requests/ -> staff approve -> due date + 14 days
```

### Sequência Principal

```mermaid
sequenceDiagram
    actor Reader as reader
    participant API as FastAPI
    participant RequestService as LoanRequestService
    participant LoanService as LoanService
    participant DB as PostgreSQL
    actor Staff as admin/librarian

    Reader->>API: POST /loan-requests/
    API->>RequestService: create_loan_request(book_id)
    RequestService->>DB: cria LoanRequest pending

    Staff->>API: POST /loan-requests/{id}/approve
    API->>RequestService: approve_loan_request(id)
    RequestService->>LoanService: create_loan(user_id, book_id)
    LoanService->>DB: valida usuário, livro, limite e disponibilidade
    LoanService->>DB: cria Loan active
    LoanService->>DB: marca Book indisponível
    RequestService->>DB: marca LoanRequest approved
```

## Segurança, Autorização e Rate Limiting

### Autenticação

A autenticação usa JWT Bearer Token.

```http
Authorization: Bearer <access_token>
```

Fluxo:

1. `POST /auth/bootstrap` cria o primeiro administrador.
2. `POST /auth/login` autentica e retorna JWT.
3. Endpoints protegidos validam token e permissões no backend.

O login retorna o token no body por simplicidade do case e para facilitar Swagger/cURL. Em produção, especialmente em aplicações web, uma alternativa mais segura seria avaliar cookies `HttpOnly`, `Secure` e `SameSite`.

O `account` retornado no login expõe apenas `id`, `name`, `email` e `role`. Campos internos como `user_id`, status e datas de auditoria não são enviados nessa resposta.

`GET /auth/me` ainda retorna `user_id` porque o frontend atual usa esse vínculo para montar "Meu Espaço". Evolução recomendada: criar `GET /me/loans` ou `GET /auth/me/loans`, resolvendo o vínculo no backend a partir do token. Depois disso, `/auth/me` poderia usar o mesmo formato mínimo do login.

### Roles

| Role | Responsabilidade |
| --- | --- |
| `admin` | Gerencia contas, usuários, autores, livros e operações de empréstimo. |
| `librarian` | Gerencia usuários, autores, livros e operações de empréstimo. |
| `reader` | Solicita empréstimos, devoluções e renovações. |

### Rate Limiting

O rate limiting usa Redis e protege rotas sensíveis: login, bootstrap, criação de contas, criação de livros, autores, usuários e solicitações.

A chave considera:

- `account:{id}` quando há JWT válido;
- IP quando não há token válido;
- método HTTP e rota.

Quando excede o limite, retorna `429 Too Many Requests` com `Retry-After`.

Trade-off consciente: a implementação usa **fixed window**. É simples e suficiente para o case, mas pode permitir bursts em bordas de janela. Em produção, evoluiria para sliding window, token bucket ou script Lua atômico no Redis.

Se Redis ficar indisponível, a API registra o problema e permite a requisição. Isso é **fail-open**: preserva disponibilidade local, mas reduz temporariamente proteção contra abuso.

## Consistência, Cache e Concorrência

### Atomicidade no Fluxo de Empréstimos

Criação e devolução de empréstimos são operações transacionais:

- valida usuário;
- valida limite de 3 empréstimos ativos;
- valida existência e disponibilidade do livro;
- cria ou altera `Loan`;
- altera disponibilidade de `Book`;
- registra métrica de domínio.

Se qualquer etapa falhar, a transação é revertida e o estado não fica parcialmente atualizado.

### Controle de Concorrência

O fluxo de criação usa duas proteções complementares:

- **locks Redis por usuário e livro:** reduzem concorrência entre requisições simultâneas;
- **`SELECT FOR UPDATE`:** bloqueio pessimista ao buscar registros críticos no banco.

Isso evita cenários como:

- duas requisições emprestarem o mesmo exemplar;
- um usuário ultrapassar o limite de 3 empréstimos ativos;
- aprovação de solicitação avançar sem a operação de domínio ter sido concluída.

### Cache com Redis

Consultas cacheadas:

- listagem de livros;
- detalhe de livro;
- contagem de exemplares disponíveis por ISBN;
- exemplares disponíveis por ISBN;
- listagem de autores.

O TTL dos caches de livros é curto: **60 segundos**. A ideia é ganhar desempenho em leituras frequentes sem criar uma política complexa demais.

Invalidação ocorre quando:

- livro é criado/removido;
- empréstimo altera disponibilidade;
- operações relevantes afetam contagem/listagem.

Se Redis estiver indisponível, a API registra log e consulta o banco diretamente. Cache é otimização, não fonte de verdade.

## Observabilidade

### Logging

Logs estruturados em JSON via `app/core/logging.py`.

Eventos com contexto adicional:

- autenticação;
- criação/devolução/renovação de empréstimo;
- aprovação/rejeição de solicitações;
- cache;
- rate limiting;
- notificações.

Campos sensíveis como senha e token são mascarados quando aparecem no payload de log.

### Health Check

```text
GET /health
```

Resposta esperada:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

Quando o banco falha, `status` passa para `degraded`. Para Redis, a resposta pode ser `ok`, `unavailable` ou `disabled`.

### Métricas Operacionais

Métricas simples de domínio são gravadas no PostgreSQL para rastrear o fluxo de empréstimos sem exigir Prometheus/Grafana no setup local.

Eventos registrados:

- solicitação criada;
- solicitação aprovada;
- solicitação rejeitada;
- empréstimo criado;
- empréstimo devolvido;
- empréstimo renovado.

Endpoints restritos a `admin` e `librarian`:

```text
GET /metrics/loans
GET /metrics/loans/export.csv
```

Exemplo:

```json
{
  "total_loans": 10,
  "active_loans": 3,
  "overdue_loans": 1,
  "returned_loans": 7,
  "total_fine_value": 12.0,
  "events_by_operation": {
    "loan_created": 10,
    "loan_returned": 7,
    "loan_renewed": 2
  }
}
```

O registro de métricas é **best effort**: se falhar, a operação principal não é desfeita.

## Notificações de Vencimento

A API possui notificações para empréstimos ativos que vencem em uma janela configurável.

Endpoint manual, restrito a staff:

```text
POST /notifications/due-loans/send?days_ahead=1&channel=all
```

Parâmetros:

- `days_ahead`: `0` a `30`, padrão `1`;
- `channel`: `email`, `webhook` ou `all`.

Características:

- email é fake no case: a mensagem é montada e registrada, sem SMTP;
- webhook faz `POST` HTTP real para `DUE_LOAN_WEBHOOK_URL`;
- histórico em `loan_due_notifications` evita reenvios duplicados por empréstimo/canal/data;
- scheduler automático pode ser ligado por env;
- scheduler usa lock Redis para evitar duplicidade com múltiplos processos/réplicas.

Configuração:

```env
DUE_LOAN_NOTIFICATIONS_ENABLED=false
DUE_LOAN_NOTIFICATION_INTERVAL_SECONDS=3600
DUE_LOAN_NOTIFICATION_DAYS_AHEAD=1
DUE_LOAN_WEBHOOK_URL=https://example.com/webhook
```

O scheduler fica desligado por padrão. Trade-off: notificações automáticas podem duplicar mensagens, consumir recursos do processo web ou ocultar falhas se não forem protegidas. Em produção, a evolução natural seria fila assíncrona, retries com backoff, DLQ, provedor SMTP real, webhook assinado e alertas.

## Banco de Dados e Migrations

O schema é versionado com Alembic. A aplicação não executa `Base.metadata.create_all` em runtime.

Migration inicial:

```text
alembic/versions/0001_initial_schema.py
```

Ela cria tabelas, relacionamentos e índices importantes:

- email ativo único em `users`;
- empréstimo ativo único por usuário/livro;
- índices de solicitações pendentes;
- índices de leitura operacional em métricas.

No Docker Compose, a API executa `alembic upgrade head` antes de iniciar. Nos testes, as fixtures usam `Base.metadata.create_all/drop_all` para manter a suíte rápida e isolada.

Em produção, migrations exigiriam validação incremental, backup, rollback e execução controlada sobre dados existentes.

## Frontend Demonstrativo

O frontend em React/Vite implementa uma console operacional simples:

- login;
- dashboard;
- catálogo;
- usuários;
- empréstimos;
- solicitações;
- métricas;
- notificações.

Ele existe principalmente para mostrar a API em fluxos reais e facilitar avaliação manual. Alguns pontos de UX, responsividade e acabamento ainda poderiam evoluir em um produto final. A prioridade do case continuou sendo backend: regras de negócio, consistência, segurança básica, testes e organização.

Instalar Node.js 22 com nvm, caso ainda não tenha uma versão compatível:

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
nvm install 22
nvm use 22
node --version
npm --version
```

Rodar:

```bash
cp frontend/.env.example frontend/.env
make frontend-install
make frontend
```

```text
http://localhost:5173
```

Configuração:

```env
# frontend/.env
VITE_API_URL=http://localhost:8000

# .env da API, caso altere a origem do frontend
CORS_ORIGINS=http://localhost:5173
```

Em uma máquina recém-clonada, rode a API antes do frontend com `make start` ou, em terminais separados, `make db` seguido de `make local`. O alvo `make frontend-install` usa `npm ci` para instalar exatamente as versões do `frontend/package-lock.json`; se o Node estiver abaixo de `20.19.0`, o Vite pode falhar ao instalar ou iniciar.

## Endpoints Principais

### Autenticação

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/auth/bootstrap` | Cria o primeiro administrador. |
| `POST` | `/auth/login` | Autentica uma conta e retorna JWT. |
| `GET` | `/auth/me` | Retorna a conta autenticada. |

### Contas

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/accounts/` | Cria conta. Requer `admin`. |
| `GET` | `/accounts/` | Lista contas. Requer `admin`. |
| `DELETE` | `/accounts/{account_id}` | Desativa conta. Requer `admin`. |

### Usuários

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/users/` | Cria usuário. Requer `admin` ou `librarian`. |
| `GET` | `/users/` | Lista usuários. |
| `GET` | `/users/{user_id}` | Busca usuário por ID. |
| `PUT` | `/users/{user_id}` | Atualiza usuário. Requer staff. |
| `DELETE` | `/users/{user_id}` | Remove usuário logicamente. Requer staff. |
| `GET` | `/users/{user_id}/loans` | Lista empréstimos de um usuário. |

### Autores

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/authors/` | Cria autor. Requer staff. |
| `GET` | `/authors/` | Lista autores. |
| `GET` | `/authors/{author_id}` | Busca autor por ID. |

### Livros

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/books/` | Cria livro vinculado a autor. Requer staff. |
| `GET` | `/books/` | Lista livros. |
| `GET` | `/books/{book_id}` | Busca livro por ID. |
| `DELETE` | `/books/{book_id}` | Remove livro logicamente. Requer staff. |
| `GET` | `/books/count/{isbn}` | Conta exemplares disponíveis por ISBN. |
| `GET` | `/books/exemplars/{isbn}` | Lista exemplares disponíveis por ISBN. |

### Empréstimos

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/loans/` | Cria empréstimo direto. Requer staff. |
| `GET` | `/loans/` | Lista empréstimos com filtros opcionais. |
| `GET` | `/loans/active` | Lista empréstimos ativos. |
| `GET` | `/loans/overdue` | Lista empréstimos atrasados. |
| `GET` | `/loans/{loan_id}` | Busca empréstimo por ID. |
| `PUT` | `/loans/{loan_id}/return` | Processa devolução direta. Requer staff. |

Filtros de `GET /loans/`:

| Query param | Descrição |
| --- | --- |
| `status` | `active` ou `returned`. |
| `user_id` | Filtra por usuário. |
| `overdue` | Quando `true`, retorna ativos vencidos. |
| `skip` / `limit` | Paginação. |

### Solicitações

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/loan-requests/` | Solicita empréstimo. Requer `reader`. |
| `GET` | `/loan-requests/` | Lista solicitações. Requer staff. |
| `POST` | `/loan-requests/{request_id}/approve` | Aprova solicitação. Requer staff. |
| `POST` | `/loan-requests/{request_id}/reject` | Rejeita solicitação. Requer staff. |
| `POST` | `/return-requests/` | Solicita devolução. Requer `reader`. |
| `POST` | `/renewal-requests/` | Solicita renovação. Requer `reader`. |

### Métricas

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/metrics/loans` | Resumo operacional de empréstimos. Requer staff. |
| `GET` | `/metrics/loans/export.csv` | Exporta eventos operacionais em CSV. Requer staff. |

### Notificações

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/notifications/due-loans/send` | Dispara notificações de vencimento por email fake, webhook ou ambos. Requer staff. |

## Exemplos de Uso

### 1. Bootstrap do Administrador

```bash
curl -X POST http://localhost:8000/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin",
    "email": "admin@example.com",
    "password": "12345678"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "12345678"
  }'
```

```bash
export TOKEN="<access_token>"
```

### 3. Criar Usuário e Conta Reader

```bash
curl -X POST http://localhost:8000/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reader",
    "email": "reader@example.com"
  }'
```

```bash
curl -X POST http://localhost:8000/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reader Account",
    "email": "reader-account@example.com",
    "password": "12345678",
    "role": "reader",
    "user_id": 1
  }'
```

### 4. Criar Autor e Livro

```bash
curl -X POST http://localhost:8000/authors/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Machado de Assis"}'
```

```bash
curl -X POST http://localhost:8000/books/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "isbn": "1234567890",
    "author_id": 1,
    "title": "Dom Casmurro",
    "published_date": "1899-01-01"
  }'
```

### 5. Solicitar e Aprovar Empréstimo

```bash
curl -X POST http://localhost:8000/loan-requests/ \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"book_id": 1}'
```

```bash
curl -X POST http://localhost:8000/loan-requests/1/approve \
  -H "Authorization: Bearer $TOKEN"
```

### 6. Devolver, Consultar e Exportar

```bash
curl -X PUT http://localhost:8000/loans/1/return \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl http://localhost:8000/loans/active?skip=0\&limit=100 \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl http://localhost:8000/loans/overdue?skip=0\&limit=100 \
  -H "Authorization: Bearer $TOKEN"
```

```bash
curl http://localhost:8000/metrics/loans/export.csv \
  -H "Authorization: Bearer $TOKEN" \
  -o loan_operation_metrics.csv
```

### 7. Notificações de Vencimento

```bash
curl -X POST "http://localhost:8000/notifications/due-loans/send?days_ahead=1&channel=all" \
  -H "Authorization: Bearer $TOKEN"
```

### 8. Health Check

```bash
curl http://localhost:8000/health
```

## Postman

Collection:

```text
docs/library-api.postman_collection.json
```

```text
docs/Library API.postman_collection.json
```


Ela cobre o fluxo principal de avaliação manual: bootstrap, login, criação de usuário/conta reader, autor, livro, solicitação, aprovação, ativos, devolução e histórico por usuário.

## Padrão de Código

O projeto usa Ruff como formatter e linter.

```bash
make lint
make format
make lint-fix
```

## Decisões Arquiteturais e Trade-offs

- **Camadas explícitas:** melhoram leitura, testes e manutenção.
- **`Account` separado de `User`:** separa autenticação de dados do leitor.
- **Role `reader`:** evita confusão entre papel de acesso e entidade `User`.
- **Alembic para schema:** migrations versionadas; `create_all` fica restrito aos testes.
- **Cache com TTL curto:** melhora leitura sem complexidade alta de invalidação.
- **Locks Redis + `SELECT FOR UPDATE`:** reduzem risco de corrida em empréstimos.
- **Catálogo sem update bibliográfico:** preserva histórico de empréstimos.
- **Métricas no banco:** observabilidade local sem infraestrutura extra.
- **Rate limiting fail-open:** preserva disponibilidade local se Redis falhar, aceitando perda temporária de proteção.
- **Email fake:** suficiente para demonstrar fluxo sem depender de SMTP externo.
- **Frontend demonstrativo:** ajuda avaliação manual, mas não é o foco técnico principal.

## Melhorias Futuras

- Criar endpoint `GET /me/loans` para remover `user_id` de `/auth/me`.
- Evoluir rate limiting para sliding window/token bucket com operação Redis atômica.
- Exportar métricas para Prometheus/Grafana com dashboards e alertas.
- Migrar notificações para fila assíncrona com retry, DLQ e provedor SMTP real.
- Expandir testes de autorização e concorrência sob carga.
- Padronizar completamente a nomenclatura pública entre `reader` e `user`, se desejado.
