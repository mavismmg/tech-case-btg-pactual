# Sistema de Gerenciamento de Biblioteca Digital

API REST para gerenciamento de uma biblioteca digital. A aplicação cobre o cadastro de usuários, contas de acesso, autores e livros, além do fluxo de empréstimos com solicitação, aprovação, devolução, multa por atraso e renovação.

O projeto foi mantido simples de rodar localmente com Docker Compose, mas sem abrir mão de alguns cuidados esperados em uma API backend: autenticação JWT, autorização por perfis, cache com Redis, rate limiting, validações com Pydantic, separação em camadas e testes automatizados.

## Índice

- [Contexto do Desafio](#contexto-do-desafio)
- [Funcionalidades Implementadas](#funcionalidades-implementadas)
- [Tecnologias Utilizadas](#tecnologias-utilizadas)
- [Arquitetura](#arquitetura)
- [Aplicação de SOLID](#aplicação-de-solid)
- [Modelo de Domínio](#modelo-de-domínio)
- [Regras de Negócio Implementadas](#regras-de-negócio-implementadas)
- [Estados do Fluxo de Empréstimo](#estados-do-fluxo-de-empréstimo)
- [Fluxo de Empréstimo](#fluxo-de-empréstimo)
- [Atomicidade no Fluxo de Empréstimos](#atomicidade-no-fluxo-de-empréstimos)
- [Autenticação e Autorização](#autenticação-e-autorização)
- [Cache com Redis](#cache-com-redis)
- [Rate Limiting](#rate-limiting)
- [Tratamento de Erros](#tratamento-de-erros)
- [Logging](#logging)
- [Health Check](#health-check)
- [Métricas Operacionais](#métricas-operacionais)
- [Banco de Dados e Inicialização](#banco-de-dados-e-inicialização)
- [Como Rodar Localmente](#como-rodar-localmente)
- [Como Rodar os Testes](#como-rodar-os-testes)
- [Padrão de Código](#padrão-de-código)
- [Endpoints Principais](#endpoints-principais)
- [Exemplos de Uso](#exemplos-de-uso)
- [Collection Postman](#collection-postman)
- [Decisões Arquiteturais e Trade-offs](#decisões-arquiteturais-e-trade-offs)
- [Melhorias Futuras](#melhorias-futuras)

## Contexto do Desafio

Este projeto foi desenvolvido para o tech case de uma API REST de biblioteca digital. O desafio avalia arquitetura em camadas, boas práticas em Python, validações, tratamento de erros, organização de código, testes e iniciativa técnica.

No desenho atual, o domínio foi dividido em:

- usuários da biblioteca;
- contas de acesso e permissões;
- autores;
- livros vinculados a autores;
- solicitações de empréstimo, devolução e renovação;
- empréstimos ativos, atrasados e devolvidos.

## Funcionalidades Implementadas

- Cadastro, listagem, busca, atualização e remoção lógica de usuários.
- Cadastro e listagem de autores.
- Cadastro, listagem e busca de livros vinculados a autores.
- Verificação de exemplares disponíveis por ISBN.
- Autenticação com JWT Bearer.
- Bootstrap do primeiro administrador.
- Criação e desativação de contas por administrador.
- Autorização por roles: `admin`, `librarian` e `reader`.
- Empréstimo direto por `admin` ou `librarian`.
- Solicitação de empréstimo por conta `reader/user`.
- Aprovação e rejeição de solicitações por `admin` ou `librarian`.
- Solicitação de devolução e renovação por `reader/user`.
- Processamento de devolução com cálculo automático de multa.
- Renovação de empréstimo ativo uma vez, quando não está atrasado.
- Listagem de empréstimos ativos e atrasados.
- Limite de 3 empréstimos ativos por usuário.
- Paginação em listagens principais com `skip` e `limit`.
- Cache Redis para consultas frequentes.
- Rate limiting por rota e identidade do cliente.
- Logging estruturado em JSON.
- Health check com verificação básica de banco e Redis.
- Métricas operacionais de empréstimos registradas no PostgreSQL.
- Testes unitários e funcionais com Pytest.
- Collection Postman para avaliação manual da API.
- Documentação automática via Swagger/OpenAPI do FastAPI.

## Tecnologias Utilizadas

| Tecnologia | Uso no projeto | Motivo da escolha |
| --- | --- | --- |
| Python | Linguagem principal | Ecossistema maduro para APIs e testes. |
| FastAPI | Framework HTTP | Facilita a criação de endpoints, validações e documentação OpenAPI. |
| PostgreSQL | Banco relacional | Boa escolha para regras que dependem de consistência, como empréstimos. |
| SQLAlchemy | ORM | Mantém as queries isoladas nos repositories e ajuda no controle transacional. |
| Pydantic | Schemas e validações | Define contratos claros de entrada e saída. |
| Redis | Cache, rate limit e locks | Usado para acelerar consultas e reduzir riscos em operações concorrentes. |
| Docker Compose | Ambiente local | Sobe API, banco e Redis com poucos comandos. |
| Pytest | Testes | Cobre regras de negócio, autenticação, cache, rate limit e fluxos HTTP. |
| JWT | Autenticação | Protege os endpoints sem manter sessão no servidor. |

## Arquitetura

O projeto segue uma arquitetura em camadas. A ideia principal é deixar o controller fino, concentrar regra de negócio nos services e isolar acesso a dados nos repositories.

```text
Request -> Controller -> Service -> Repository -> Database
                    \-> Schemas
                    \-> Core infrastructure
```

Responsabilidades principais:

| Camada | Responsabilidade |
| --- | --- |
| `controllers` | Entrada HTTP, dependências FastAPI, autorização e tradução de exceções para status HTTP. |
| `services` | Regras de negócio, validações de domínio, transações e orquestração de operações. |
| `repositories` | Acesso ao banco via SQLAlchemy. |
| `models` | Entidades ORM e relacionamentos. |
| `schemas` | Contratos Pydantic de entrada e saída. |
| `core` | Infraestrutura: banco, segurança, cache, rate limit e logging. |

### Visão da API

```mermaid
flowchart TD
    Client[Cliente / Postman / Swagger] --> API[FastAPI App]

    API --> Auth[Autenticação JWT]
    API --> RateLimit[Rate limiting]
    RateLimit --> Redis[(Redis)]

    API --> Controllers[Controllers / Routers]
    Controllers --> Schemas[Schemas Pydantic]
    Controllers --> Services[Services]

    Services --> Repositories[Repositories]
    Services --> Cache[Cache e locks]
    Cache --> Redis

    Repositories --> DB[(PostgreSQL)]
    Services --> Logs[Logs estruturados JSON]
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
  core/            # Configuração de banco, JWT, Redis, rate limit e logging
  models/          # Modelos SQLAlchemy
  repositories/    # Queries e persistência
  schemas/         # Schemas Pydantic
  services/        # Regras de negócio
  dependencies.py  # Dependências compartilhadas do FastAPI
  server.py        # Criação da aplicação e inclusão de routers
tests/             # Testes unitários e funcionais
docker-compose.yml # PostgreSQL, Redis, banco de teste e API
Dockerfile         # Imagem da API
Makefile           # Comandos auxiliares
requirements.txt   # Dependências Python
```

## Aplicação de SOLID

O projeto aplica SOLID de forma pragmática, principalmente pela separação em camadas. A proposta não foi criar uma arquitetura enterprise com interfaces para tudo, mas manter responsabilidades claras e facilitar evolução/testes.

| Princípio | Como aparece no projeto |
| --- | --- |
| Single Responsibility | Controllers tratam HTTP, services concentram regras de negócio, repositories acessam o banco, schemas definem contratos e `core` concentra infraestrutura. |
| Open/Closed | Parcialmente atendido. As regras estão centralizadas nos services, mas novos tipos de fluxo em `LoanRequest` ainda exigiriam alterar o service principal. |
| Liskov Substitution | Pouco aplicável, pois o projeto não usa hierarquias de classes relevantes. Não há sinais de violação. |
| Interface Segregation | Aplicado de forma simples pela separação dos módulos por domínio e camada, sem contratos artificiais. |
| Dependency Inversion | Parcialmente atendido. Services usam repositories concretos; para o tamanho do case isso reduz complexidade, mas em produção poderia evoluir para injeção de dependências/ports. |

O principal trade-off foi manter uma arquitetura compreensível e objetiva para o escopo do desafio, evitando abstrações prematuras.

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
        datetime updated_at
        datetime deleted_at
    }

    AUTHORS {
        int id PK
        string name
        datetime created_at
        datetime updated_at
        datetime deleted_at
    }

    BOOKS {
        int id PK
        string isbn
        int author_id FK
        string title
        date published_date
        boolean is_available
        datetime created_at
        datetime updated_at
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

    LOAN_OPERATION_METRICS {
        int id PK
        string operation
        int loan_id FK
        int loan_request_id FK
        int user_id FK
        int book_id FK
        int account_id FK
        int reviewer_account_id FK
        float fine_value
        datetime created_at
    }
```

| Entidade | Descrição |
| --- | --- |
| `User` | Pessoa usuária da biblioteca. Possui dados cadastrais e relacionamento com empréstimos. |
| `Account` | Conta autenticável, com email, senha criptografada, role e vínculo opcional com `User`. |
| `Author` | Autor de livros. |
| `Book` | Exemplar de livro, vinculado a um autor e identificado por ISBN. |
| `Loan` | Empréstimo ativo ou devolvido, com prazo, data de devolução, multa e contador de renovação. |
| `LoanRequest` | Solicitação de empréstimo, devolução ou renovação, revisada por staff. |
| `LoanOperationMetric` | Registro operacional de eventos relevantes do ciclo de empréstimos. |

### Nota sobre `Book`, ISBN e atualização de catálogo

No projeto, `Book` representa um exemplar físico/digital do acervo. O `isbn` é o identificador bibliográfico do livro, usado no mercado editorial para identificar uma edição específica de uma obra. Em termos práticos, ele ajuda a agrupar exemplares do mesmo livro e permite consultar disponibilidade por ISBN.

Por esse motivo, a API não expõe um endpoint público para alterar `isbn`, `title`, `author_id` ou `published_date` depois que o livro foi cadastrado. Se esses dados fossem editados livremente, o histórico poderia ficar ambíguo: por exemplo, um empréstimo antigo poderia passar a apontar para um livro com outro ISBN ou outro título.

Para preservar rastreabilidade, o catálogo segue uma abordagem mais conservadora:

- dados bibliográficos são definidos na criação do livro;
- remoção usa soft delete, mantendo o registro histórico no banco;
- `is_available` é alterado pelo próprio fluxo de empréstimo/devolução, não por update manual do catálogo.

### Nota sobre `User`, `Account` e `reader`

O enunciado usa "usuário" para representar a pessoa que utiliza a biblioteca. No projeto, essa ideia foi separada em duas partes:

- `User`: entidade de domínio, com os dados do leitor da biblioteca.
- `Account`: entidade de autenticação, com email, senha, status e role.
- `reader`: role da conta que representa o usuário comum do enunciado.

Essa separação evita misturar dados de biblioteca com credenciais de acesso. Ela também permite que contas administrativas, como `admin` e `librarian`, existam sem vínculo obrigatório com um leitor.

Por isso, quando a documentação menciona `reader/user`, está se referindo ao usuário comum do case. No código, o nome técnico dessa role é `reader`.

## Regras de Negócio Implementadas

- O prazo padrão de empréstimo é de 14 dias.
- A multa por atraso é de R$ 2,00 por dia completo.
- Dias parciais de atraso não são arredondados para cima. Ex.: 14 dias e 2 horas de atraso cobram 14 dias.
- Um usuário pode ter no máximo 3 empréstimos ativos.
- Um livro indisponível não pode ser emprestado.
- Um empréstimo aprovado marca o livro como indisponível.
- Uma devolução marca o empréstimo como devolvido e libera o livro.
- A multa é calculada na devolução com base na diferença entre a data atual e `expected_return_date`.
- Um `reader/user` pode solicitar empréstimo, devolução ou renovação.
- Apenas `admin` ou `librarian` pode aprovar/rejeitar solicitações e processar devoluções diretamente.
- A renovação só é permitida para empréstimos ativos, não atrasados e com limite de uma renovação.
- Solicitações pendentes duplicadas para a mesma operação são bloqueadas.

## Estados do Fluxo de Empréstimo

O fluxo separa a solicitação do empréstimo efetivo. Por isso, existem dois conjuntos de estados:

| Entidade | Status | Significado |
| --- | --- | --- |
| `LoanRequest` | `pending` | Solicitação criada pelo `reader/user`, aguardando análise do staff. |
| `LoanRequest` | `approved` | Solicitação aprovada por `admin` ou `librarian`. Quando a solicitação é de empréstimo, um `Loan` ativo é criado. |
| `LoanRequest` | `rejected` | Solicitação rejeitada por `admin` ou `librarian`, sem alterar o estado do livro/empréstimo. |
| `Loan` | `active` | Empréstimo efetivamente criado e ainda não devolvido. O livro permanece indisponível. |
| `Loan` | `returned` | Empréstimo devolvido. A data real de devolução e a multa, quando houver, ficam registradas. |

Na prática, `pending`, `approved` e `rejected` pertencem ao fluxo de aprovação (`LoanRequest`). O empréstimo em si (`Loan`) só nasce após aprovação ou criação direta por staff, e seus estados atuais são `active` e `returned`.

## Fluxo de Empréstimo

### Solicitação

```text
reader/user -> POST /loan-requests/ -> LoanRequest pending
```

O usuário comum autenticado solicita o empréstimo de um livro. A aplicação valida se a conta é `reader`, se está vinculada a um `User`, se o livro existe e se não há uma solicitação pendente duplicada.

### Aprovação

```text
admin/librarian -> POST /loan-requests/{id}/approve -> Loan active
```

Ao aprovar uma solicitação de empréstimo, o serviço cria um `Loan`, define o prazo de devolução em 14 dias, altera o livro para indisponível e marca a solicitação como aprovada.

### Rejeição

```text
admin/librarian -> POST /loan-requests/{id}/reject -> LoanRequest rejected
```

Uma solicitação pendente pode ser rejeitada por staff com uma justificativa. Nesse caso, nenhum empréstimo é criado e a disponibilidade do livro não é alterada.

### Devolução

```text
admin/librarian -> PUT /loans/{id}/return -> Loan returned
reader/user -> POST /return-requests/ -> staff approve -> Loan returned
```

Na devolução, a aplicação calcula eventual multa, preenche `actual_return_date`, altera o status para `returned` e torna o livro disponível novamente.

### Renovação

```text
reader/user -> POST /renewal-requests/ -> staff approve -> due date + 14 days
```

A renovação também passa por solicitação e aprovação. Quando aprovada, estende o prazo por mais 14 dias e incrementa `renewal_count`.

### Sequência Principal

```mermaid
sequenceDiagram
    actor Reader as reader/user
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

## Atomicidade no Fluxo de Empréstimos

As operações mais sensíveis do projeto estão no fluxo de empréstimos. Por isso, `loan_service` e `loan_request_service` concentram as regras que precisam acontecer de forma consistente.

No `loan_service`, a criação de um empréstimo e a devolução são tratadas como operações transacionais. A criação valida o usuário, confere o limite de 3 empréstimos ativos, valida se o livro existe, verifica a disponibilidade e só então cria o `Loan` e marca o `Book` como indisponível. Se qualquer etapa falhar, a transação é revertida e o estado do livro/empréstimo não fica parcialmente atualizado.

Na devolução, a mesma ideia é aplicada: o serviço busca o empréstimo, valida se ele ainda está ativo, calcula a multa, preenche a data real de devolução, altera o status para `returned` e libera o livro. Essas mudanças são confirmadas juntas; em caso de erro, o rollback evita inconsistência entre `Loan` e `Book`.

Também há uma preocupação com concorrência no momento de criar empréstimos. O serviço usa locks no Redis por usuário e por livro para reduzir o risco de duas requisições simultâneas emprestarem o mesmo exemplar ou ultrapassarem o limite de empréstimos ativos do usuário. Além disso, o repositório utiliza bloqueio pessimista com `with_for_update` ao buscar registros críticos.

O `loan_request_service` orquestra o fluxo de aprovação. Quando um `admin` ou `librarian` aprova uma solicitação, ele delega a criação/devolução/renovação para `loan_service`. Assim, a solicitação só é marcada como `approved` depois que a operação de domínio foi concluída com sucesso. Se a regra de negócio falhar, a solicitação não avança indevidamente e o erro é retornado para o controller.

## Autenticação e Autorização

A autenticação usa JWT Bearer Token.

Fluxo principal:

1. Criar o primeiro administrador com `POST /auth/bootstrap`.
2. Autenticar com `POST /auth/login`.
3. Enviar o token nos endpoints protegidos:

```http
Authorization: Bearer <access_token>
```

Roles:

| Role | Responsabilidade |
| --- | --- |
| `admin` | Gerencia contas, usuários, autores, livros e operações de empréstimo. |
| `librarian` | Gerencia usuários, autores, livros e operações de empréstimo. |
| `reader/user` | Usuário comum do case. Solicita empréstimos, devoluções e renovações. No código, esta role é `reader`. |

## Cache com Redis

O Redis é usado para cache de consultas frequentes e apoio a locks no fluxo de empréstimos.

Consultas cacheadas:

- listagem de livros;
- detalhe de livro;
- contagem de exemplares disponíveis por ISBN;
- exemplares disponíveis por ISBN;
- listagem de autores.

O TTL usado nos caches de livros é curto, de 60 segundos. Foi uma escolha simples para ganhar desempenho em leituras frequentes sem criar uma estratégia complexa de invalidação. Quando um livro é criado ou um empréstimo muda a disponibilidade de um exemplar, os caches relacionados são invalidados.

Se o Redis estiver indisponível, a API registra o evento em log e segue consultando o banco. A ideia aqui é não derrubar o fluxo principal da biblioteca por falha em uma camada auxiliar.

## Rate Limiting

O rate limiting usa Redis e foi aplicado em operações mais sensíveis, como login, bootstrap, criação de contas, criação de livros, autores, usuários e solicitações.

A chave considera:

- `account:{id}` quando o token JWT é válido;
- IP do cliente quando não há token válido;
- método HTTP e rota.

Quando o limite é excedido, a API retorna `429 Too Many Requests` com header `Retry-After`.

A implementação usa uma janela fixa por chave Redis, iniciada no primeiro request daquela chave. Isso significa que, quando a janela está perto de expirar, o cliente pode receber `429` com um `Retry-After` baixo e voltar a consumir o limite após a expiração.

Esse modelo é simples e suficiente para o escopo do case, mas tem o trade-off comum de fixed window: pode permitir bursts em bordas de janela. Em produção, uma evolução natural seria usar sliding window, token bucket ou um script Lua no Redis para combinar incremento e expiração de forma totalmente atômica.

Se o Redis estiver indisponível, a aplicação registra o problema e permite a requisição. É um trade-off consciente: em um case local, preferi manter a API disponível em vez de bloquear a operação por indisponibilidade do Redis.

## Tratamento de Erros

As regras de domínio são modeladas com exceções customizadas nos services, por exemplo:

- usuário não encontrado;
- livro não encontrado;
- livro indisponível;
- limite de empréstimos excedido;
- solicitação duplicada;
- empréstimo já devolvido;
- credenciais inválidas;
- permissão insuficiente.

Os controllers traduzem essas exceções para respostas HTTP apropriadas, como `401`, `403`, `404`, `409` e `422`.

## Logging

Os logs são estruturados em JSON por meio de `app/core/logging.py`.

Os logs incluem campos adicionais em operações críticas, como:

- criação de empréstimo;
- devolução;
- aprovação/rejeição de solicitações;
- autenticação;
- cache;
- rate limiting.

Campos sensíveis como senha e token são mascarados quando presentes no payload de log.

## Health Check

A API expõe um endpoint simples de observabilidade:

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

Quando o banco não responde, `status` passa para `degraded`. Para Redis, o retorno pode ser `ok`, `unavailable` ou `disabled`, já que a aplicação continua funcionando sem cache/rate limit em modo degradado.

## Métricas Operacionais

Além do health check, a aplicação registra métricas simples de domínio no PostgreSQL para acompanhar ações importantes do fluxo de empréstimos. A ideia é dar visibilidade operacional sem adicionar infraestrutura extra ao case.

Eventos registrados:

- solicitação de empréstimo/devolução/renovação criada;
- solicitação aprovada;
- solicitação rejeitada;
- empréstimo criado;
- empréstimo devolvido;
- empréstimo renovado.

O endpoint de leitura é restrito a `admin` e `librarian`:

```text
GET /metrics/loans
```

Exemplo de resposta:

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

O registro dessas métricas é best effort: se a gravação da métrica falhar, a aplicação registra um warning, mas não desfaz uma operação de empréstimo já concluída. Em produção, uma evolução natural seria exportar esses sinais para Prometheus/Grafana ou outra solução de observabilidade.

## Banco de Dados e Inicialização

O schema do banco é versionado com Alembic. Em runtime, a aplicação não executa `Base.metadata.create_all`; as tabelas, índices e constraints são criados por migrations.

A migration inicial está em:

```text
alembic/versions/0001_initial_schema.py
```

Ela cria o schema atual completo, incluindo os índices parciais usados nas regras de domínio:

- email ativo único em `users`;
- empréstimo ativo único por usuário/livro em `loans`;
- índices de solicitações pendentes em `loan_requests`;
- índices de leitura operacional em `loan_operation_metrics`.

Para rodar migrations manualmente:

```bash
make migrate
```

No Docker Compose, a API executa `alembic upgrade head` antes de iniciar o Uvicorn. Os testes continuam usando `Base.metadata.create_all/drop_all` nas fixtures para manter a suíte rápida e isolada.

Para facilitar a reprodução, o fluxo local foi pensado para um banco novo, criado a partir das migrations. Isso evita passos manuais. Em um ambiente de producao, a estratégia seria diferente: as migrations seriam planejadas de forma incremental, com validação de compatibilidade, backup, rollback e execução controlada sobre dados existentes.

## Como Rodar Localmente

### Pré-requisitos

- Docker
- Docker Compose
- Python 3.12 ou superior, caso deseje rodar fora do container

### Variáveis de Ambiente

Crie um `.env` com base em `.env-example`.

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/library
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5433/library_test
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT_ENABLED=true
LOG_PRETTY_JSON=true
```

### Subir API, Banco e Redis

```bash
make start
```

O container da API aplica as migrations antes de iniciar o servidor.

A API ficará disponível em:

```text
http://localhost:8000
```

Documentação Swagger/OpenAPI:

```text
http://localhost:8000/docs
```

### Subir Apenas Banco e Redis

```bash
make db
```

### Rodar API Localmente com Virtualenv

```bash
make local
```

Esse comando cria o ambiente virtual, instala as dependências, aplica as migrations e inicia o Uvicorn.

Caso as dependências já estejam instaladas:

```bash
make local-soft
```

Também é possível aplicar apenas as migrations:

```bash
make migrate
```

Para criar uma nova migration depois de alterar models:

```bash
make revision m="descricao_da_migration"
```

### Dados de Exemplo

As migrations criam apenas estrutura de banco. Para facilitar testes manuais em ambiente local, existe um seed opcional:

```bash
make seed
```

Esse comando aplica as migrations e cria dados mínimos de demonstração de forma idempotente:

- conta `admin`;
- conta `librarian`;
- usuário da biblioteca;
- conta `reader` vinculada ao usuário;
- autores;
- livros disponíveis para empréstimo.

Credenciais locais criadas pelo seed:

| Perfil | Email | Senha |
| --- | --- | --- |
| `admin` | `admin@example.com` | `strong-password` |
| `librarian` | `librarian@example.com` | `strong-password` |
| `reader` | `reader-account@example.com` | `strong-password` |

O seed não faz parte das migrations e não é executado automaticamente. A ideia é manter schema e dados de desenvolvimento separados.

### Parar Containers

```bash
make stop
```

## Como Rodar os Testes

Suba o banco de teste e Redis:

```bash
make test_db
```

Execute os testes:

```bash
pytest
```

Os testes usam `TEST_DATABASE_URL` e recriam as tabelas durante a execução das fixtures.

## Padrão de Código

O projeto usa Ruff como formatter e linter. A ideia é ter um padrão simples, parecido com Prettier.

Para verificar lint:

```bash
make lint
```

Para aplicar formatação:

```bash
make format
```

Para rodar lint e testes juntos:

```bash
make check
```

Antes de entregar ou abrir uma contribuição, o fluxo recomendado é rodar `make lint` e `venv/bin/pytest`. Se o objetivo for aplicar correções automáticas seguras de lint, use:

```bash
make lint-fix
```

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
| `PUT` | `/users/{user_id}` | Atualiza usuário. Requer `admin` ou `librarian`. |
| `DELETE` | `/users/{user_id}` | Remove usuário logicamente. Requer `admin` ou `librarian`. |
| `GET` | `/users/{user_id}/loans` | Lista empréstimos de um usuário. |

### Autores

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/authors/` | Cria autor. Requer `admin` ou `librarian`. |
| `GET` | `/authors/` | Lista autores. |
| `GET` | `/authors/{author_id}` | Busca autor por ID. |

### Livros

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/books/` | Cria livro vinculado a autor. Requer `admin` ou `librarian`. |
| `GET` | `/books/` | Lista livros. |
| `GET` | `/books/{book_id}` | Busca livro por ID. |
| `DELETE` | `/books/{book_id}` | Remove livro logicamente. Requer `admin` ou `librarian`. |
| `GET` | `/books/count/{isbn}` | Conta exemplares disponíveis por ISBN. |
| `GET` | `/books/exemplars/{isbn}` | Lista exemplares disponíveis por ISBN. |

### Empréstimos

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/loans/` | Cria empréstimo direto. Requer `admin` ou `librarian`. |
| `GET` | `/loans/` | Lista empréstimos com filtros opcionais `status`, `user_id` e `overdue`. |
| `GET` | `/loans/active` | Lista empréstimos ativos. |
| `GET` | `/loans/overdue` | Lista empréstimos atrasados. |
| `GET` | `/loans/{loan_id}` | Busca empréstimo por ID. |
| `PUT` | `/loans/{loan_id}/return` | Processa devolução direta. Requer `admin` ou `librarian`. |

Filtros disponíveis em `GET /loans/`:

| Query param | Descrição |
| --- | --- |
| `status` | Filtra por `active` ou `returned`. |
| `user_id` | Filtra por usuário. |
| `overdue` | Quando `true`, retorna empréstimos ativos com prazo vencido. |
| `skip` / `limit` | Paginação. |

### Solicitações

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `POST` | `/loan-requests/` | Solicita empréstimo. Requer conta `reader/user`. |
| `GET` | `/loan-requests/` | Lista solicitações. Requer `admin` ou `librarian`. |
| `POST` | `/loan-requests/{request_id}/approve` | Aprova solicitação. Requer `admin` ou `librarian`. |
| `POST` | `/loan-requests/{request_id}/reject` | Rejeita solicitação. Requer `admin` ou `librarian`. |
| `POST` | `/return-requests/` | Solicita devolução. Requer conta `reader/user`. |
| `POST` | `/renewal-requests/` | Solicita renovação. Requer conta `reader/user`. |

### Métricas

| Método | Endpoint | Descrição |
| --- | --- | --- |
| `GET` | `/metrics/loans` | Retorna resumo operacional de empréstimos. Requer `admin` ou `librarian`. |

## Exemplos de Uso

### 1. Bootstrap do Administrador

```bash
curl -X POST http://localhost:8000/auth/bootstrap \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Admin",
    "email": "admin@example.com",
    "password": "strong-password"
  }'
```

### 2. Login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "strong-password"
  }'
```

Use o `access_token` retornado nos próximos requests:

```bash
export TOKEN="<access_token>"
```

### 3. Criar Usuário da Biblioteca

```bash
curl -X POST http://localhost:8000/users/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reader",
    "email": "reader@example.com"
  }'
```

### 4. Criar Conta Reader/User Vinculada ao Usuário

```bash
curl -X POST http://localhost:8000/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Reader Account",
    "email": "reader-account@example.com",
    "password": "strong-password",
    "role": "reader",
    "user_id": 1
  }'
```

### 5. Criar Autor

```bash
curl -X POST http://localhost:8000/authors/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Machado de Assis"
  }'
```

### 6. Criar Livro

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

### 7. Solicitar Empréstimo

Autentique com a conta `reader` e use o token dela:

```bash
curl -X POST http://localhost:8000/loan-requests/ \
  -H "Authorization: Bearer $READER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "book_id": 1
  }'
```

### 8. Aprovar Solicitação

```bash
curl -X POST http://localhost:8000/loan-requests/1/approve \
  -H "Authorization: Bearer $TOKEN"
```

### 9. Processar Devolução Direta

```bash
curl -X PUT http://localhost:8000/loans/1/return \
  -H "Authorization: Bearer $TOKEN"
```

### 10. Consultar Empréstimos de um Usuário

```bash
curl http://localhost:8000/users/1/loans?skip=0\&limit=100 \
  -H "Authorization: Bearer $TOKEN"
```

### 11. Consultar Empréstimos Ativos

```bash
curl http://localhost:8000/loans/active?skip=0\&limit=100 \
  -H "Authorization: Bearer $TOKEN"
```

### 12. Consultar Empréstimos Atrasados

```bash
curl http://localhost:8000/loans/overdue?skip=0\&limit=100 \
  -H "Authorization: Bearer $TOKEN"
```

### 13. Health Check

```bash
curl http://localhost:8000/health
```

### 14. Consultar Métricas de Empréstimos

```bash
curl http://localhost:8000/metrics/loans \
  -H "Authorization: Bearer $TOKEN"
```

## Collection Postman

A collection Postman está disponível em:

```text
docs/library-api.postman_collection.json
```

Ela cobre o fluxo que eu usaria para avaliar rapidamente a API: bootstrap, login, criação de usuário/conta reader, autor, livro, solicitação de empréstimo, aprovação, listagem de ativos, devolução e histórico por usuário.

## Decisões Arquiteturais e Trade-offs

- **Camadas explícitas**: controllers, services e repositories deixam o fluxo mais fácil de revisar e testar.
- **`Account` separado de `User`**: separa credenciais de acesso dos dados do leitor da biblioteca.
- **Role `reader` para usuário comum**: no enunciado esse papel aparece como `user`; usei `reader` para não confundir a role com a entidade `User`.
- **Alembic para schema**: o banco da aplicação é criado por migrations versionadas; `create_all` fica restrito aos testes.
- **Cache com TTL curto**: melhora leituras frequentes sem exigir uma política pesada de invalidação.
- **Locks Redis no empréstimo**: reduzem o risco de concorrência ao tentar emprestar o mesmo livro ou atingir o limite de um usuário.
- **Catálogo sem update bibliográfico**: livros podem ser removidos logicamente, mas ISBN/título/autor não são editados por endpoint público para preservar histórico de empréstimos.
- **Métricas no banco**: deixam a avaliação local simples e dão visibilidade ao fluxo de empréstimos sem exigir Prometheus/Grafana no setup.
- **Rate limiting fail-open**: uma falha no Redis não derruba a API, mas reduz temporariamente a proteção contra abuso.
- **Exceções de domínio**: deixam as regras de negócio nos services e a tradução HTTP nos controllers.

## Melhorias Futuras

- Evoluir métricas para Prometheus/Grafana, com dashboards e alertas.
- Implementar notificações de vencimento por email ou webhook.
- Padronizar completamente a nomenclatura pública entre `reader` e `user`, se desejado.
- Expandir testes de integração para mais cenários de autorização e concorrência.
