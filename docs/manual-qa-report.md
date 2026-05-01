# Relatório de QA Manual

Este documento registra a execução dos testes manuais da API da biblioteca digital, incluindo a cobertura funcional, os cenários que passaram, as falhas encontradas inicialmente e a revalidação após os fixes.

## Ambiente e Preparação

Os testes foram executados em ambiente local com Docker Compose, usando a API, PostgreSQL e Redis.

Pré-condições validadas:

| Item | Resultado |
| --- | --- |
| Subir aplicação com PostgreSQL e Redis via Docker Compose | Passou |
| Rodar migrations | Passou |
| Rodar `scripts/seed_dev.py` | Passou |
| Login com `admin@example.com / 12345678` | Passou |
| Login com `librarian@example.com / 12345678` | Passou |
| Login com `reader-account@example.com / 12345678` | Passou |
| Obter tokens em `POST /auth/login` | Passou |
| Validar `GET /health` antes e depois da execução | Passou |

Resposta de health check antes e depois da bateria:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

## Como os Testes Foram Feitos

A execução foi manual, usando a API por Postman/Swagger e chamadas HTTP diretas quando necessário. Para cada cenário foram registrados:

- endpoint testado;
- payload ou query params;
- role/token utilizado (`admin`, `librarian`, `reader` ou sem autenticação);
- status HTTP esperado;
- resposta retornada;
- estado posterior relevante, como disponibilidade do livro, histórico de empréstimos, métricas e health check.

A validação não se limitou ao status HTTP. Nos fluxos críticos, também foi conferido se o estado do domínio ficou coerente: livro indisponível após empréstimo, livro disponível após devolução, limite de 3 empréstimos ativos, cálculo de multa, bloqueios por role e consistência entre listagens.

## Matriz de Cobertura

| Área | Endpoints/Comportamentos | Resultado final |
| --- | --- | --- |
| Autenticação e contas | `/auth/bootstrap`, `/auth/login`, `/auth/me`, `/accounts/`, tokens inválidos, roles e desativação de conta | Passou |
| Usuários | `/users/`, `/users/{id}`, `/users/{id}/loans`, criação, duplicidade, busca e histórico | Passou |
| Autores | `/authors/`, criação, duplicidade, listagem, busca e paginação | Passou após fixes |
| Livros e catálogo | `/books/`, `/books/{id}`, `/books/count/{isbn}`, `/books/exemplars/{isbn}`, disponibilidade e soft delete | Passou após fixes |
| Empréstimos | `/loans/`, `/loans/active`, `/loans/overdue`, `/loans/{id}`, `/loans/{id}/return` | Passou |
| Solicitações | `/loan-requests/`, `/return-requests/`, `/renewal-requests/`, approve/reject, duplicidade e ownership | Passou |
| Métricas e observabilidade | `/metrics/loans`, `/health` | Passou |
| Cache | disponibilidade por ISBN antes/depois de empréstimo e devolução | Passou após fixes |
| Rate limit | login, bootstrap, criação de recursos, listagens e operações de empréstimo | Passou |
| Concorrência | empréstimo simultâneo do mesmo livro e tentativa simultânea de ultrapassar limite por usuário | Passou |

## Resultado por Grupo

| Grupo | Resultado inicial | Resultado após fixes | Observações |
| --- | --- | --- | --- |
| Pré-condições | Passou | Passou | Ambiente, seed, tokens e health check estáveis. |
| Autenticação e autorização | Passou | Passou | `401`, `403`, `409` e `422` retornaram conforme o contrato esperado. |
| Validações de entrada | Falhou inicialmente | Passou após fixes | IDs negativos/zero/string e paginação inválida foram endurecidos para retornar `422`. |
| Catálogo e disponibilidade | Falhou inicialmente | Passou após fixes | ISBN inexistente agora retorna `404`; ISBN existente sem disponibilidade continua retornando `200` com zero/lista vazia. |
| Empréstimo direto por staff | Passou | Passou | Fluxo principal, limite de 3 ativos, livro indisponível e filtros consistentes. |
| Devolução e multa | Passou | Passou | Multa calculada por dia completo e devolução duplicada bloqueada. |
| Solicitações por reader | Passou | Passou | Livro existente retorna `201 pending`; livro inexistente retorna `404`; duplicidade e ownership bloqueados. |
| Renovação | Passou | Passou | Uma renovação permitida; segunda renovação, atraso e empréstimo retornado bloqueados. |
| Paginação, filtros e enums | Passou após fixes | Passou | Contrato `{items,total,skip,limit}` preservado e filtros inválidos retornam `422`. |
| Cache, rate limit e estabilidade | Passou | Passou | Redis opcional em modo degradado, rate limit com `429` e concorrência preservando consistência. |

## Falhas Encontradas Inicialmente

### Validação de IDs

Alguns endpoints aceitavam valores inválidos sem erro de validação:

| Cenário | Comportamento inicial | Comportamento final |
| --- | --- | --- |
| `GET /users/{user_id}/loans` com ID negativo ou zero | Retornava `200` em alguns casos | Retorna `422` |
| `/books/count/{isbn}` com valor inválido | Retornava `200` em alguns casos | Retorna `422` |
| `/books/exemplars/{isbn}` com valor inválido | Retornava `200` em alguns casos | Retorna `422` |
| IDs em paths de livros, autores, usuários, empréstimos e solicitações | Validação inconsistente | IDs não positivos retornam `422` |

### Paginação

Foram encontrados problemas em listagens paginadas:

| Cenário | Comportamento inicial | Comportamento final |
| --- | --- | --- |
| `skip=-1` em `/authors/` | Retornava `500 Internal Server Error` | Retorna `422` |
| `limit=-1` ou `limit=0` | Podia ser aceito dependendo da rota | Retorna `422` |
| `limit` muito alto | Aceito sem limite superior claro | Retorna `422` acima de `100` |

O contrato final adotado para paginação foi:

- `skip >= 0`;
- `1 <= limit <= 100`.

### ISBN Inexistente

Os endpoints por ISBN inicialmente não diferenciavam ISBN inexistente de ISBN existente sem exemplares disponíveis.

| Endpoint | Comportamento inicial | Comportamento final |
| --- | --- | --- |
| `GET /books/count/{isbn}` com ISBN inexistente | `200` com mensagem de zero exemplares | `404` |
| `GET /books/exemplars/{isbn}` com ISBN inexistente | `200` com `[]` | `404` |
| ISBN existente, mas todos os exemplares emprestados | Não ficava claramente separado de inexistente | `200`, `available_exemplars=0`, `is_available=false` e lista vazia em exemplars |

### Cache de Disponibilidade

Durante a revalidação automatizada foi identificado que um valor antigo em Redis poderia mascarar um ISBN que não existia mais no banco isolado de teste. O service passou a confirmar a existência ativa do ISBN antes de aceitar o cache de disponibilidade. Com isso:

- ISBN válido inexistente retorna `404` mesmo se houver cache residual;
- ISBN existente continua usando cache para contagem e listagem de exemplares disponíveis;
- empréstimo e devolução continuam invalidando os caches relacionados ao ISBN.

## Cobertura Detalhada

### 1. Autenticação e Autorização

| Cenário | Resultado |
| --- | --- |
| Acessar rotas protegidas sem token retorna `401` | Passou |
| Usar token inválido, expirado ou prefixo errado retorna `401` | Passou |
| `reader` tentando criar usuário, autor, livro, conta, empréstimo direto e acessar métricas retorna `403` | Passou |
| `librarian` tentando criar/listar/desativar contas retorna `403` | Passou |
| `admin` criando conta `reader` sem `user_id` retorna `422` | Passou |
| `admin` criando conta `admin/librarian` com `user_id` retorna `422` | Passou |
| Conta desativada não consegue login | Passou |
| `/auth/bootstrap` após existir conta retorna `409` | Passou |

### 2. Validações de Entrada

| Cenário | Resultado |
| --- | --- |
| Usuário com email inválido, nome vazio ou nome acima do limite retorna `422` | Passou |
| Usuário duplicado por email retorna `409` | Passou |
| Autor duplicado retorna `409` | Passou |
| Livro com `author_id` inexistente retorna erro de validação/relacionamento esperado | Passou |
| ISBN alfanumérico, curto, longo ou vazio retorna `422` | Passou |
| `published_date` futura retorna `422` | Passou |
| IDs negativos, zero ou string retornam `422` ou `404`, nunca `500` | Passou após fixes |
| `skip=-1`, `limit=-1`, `limit=0` e `limit>100` retornam `422` | Passou após fixes |

### 3. Catálogo e Disponibilidade

| Cenário | Resultado |
| --- | --- |
| Criar dois exemplares com mesmo ISBN e contar disponibilidade | Passou |
| Emprestar um exemplar decrementa disponibilidade | Passou |
| Livro emprestado fica `is_available=false` | Passou |
| `/books/exemplars/{isbn}` reflete exemplares disponíveis | Passou |
| Devolução incrementa disponibilidade | Passou |
| ISBN inexistente em count/exemplars retorna `404` | Passou após fixes |
| Deletar livro com empréstimo ativo retorna `409` | Passou |
| Deletar livro sem empréstimo ativo remove das listagens e impede novo empréstimo | Passou |

### 4. Empréstimo Direto por Staff

| Cenário | Resultado |
| --- | --- |
| `admin/librarian` cria empréstimo direto com `POST /loans/` | Passou |
| `expected_return_date` fica 14 dias após `loan_date` | Passou |
| Livro inexistente retorna `404` | Passou |
| Usuário inexistente retorna `404` | Passou |
| Livro indisponível retorna `409` | Passou |
| Quarto empréstimo ativo do mesmo usuário retorna `409` | Passou |
| Histórico por usuário e filtros de empréstimo retornam dados consistentes | Passou |
| `/loans/overdue` lista apenas ativos atrasados | Passou |

### 5. Devolução e Multa

| Cenário | Resultado |
| --- | --- |
| Devolução no prazo retorna multa `0` e libera livro | Passou |
| Devolução atrasada cobra R$ 2,00 por dia completo | Passou |
| Repetir devolução retorna `409` | Passou |
| Devolver empréstimo inexistente retorna `404` | Passou |
| Dias parciais de atraso não arredondam para cima | Passou |
| `/metrics/loans` registra devoluções e multas | Passou |

### 6. Solicitações por Reader

| Cenário | Resultado |
| --- | --- |
| `reader` cria `/loan-requests/` para livro existente e recebe `201 pending` | Passou |
| `reader` cria `/loan-requests/` para livro inexistente e recebe `404` | Passou |
| Solicitação duplicada pendente retorna `409` | Passou |
| Staff lista solicitações com filtros `status` e `type` | Passou |
| Reader tentando listar todas as solicitações retorna `403` | Passou |
| Staff aprova solicitação, cria empréstimo e indisponibiliza livro | Passou |
| Reaprovar ou rejeitar solicitação já revisada retorna `409` | Passou |
| Rejeição com motivo vazio retorna `422`; motivo válido marca `rejected` | Passou |
| Solicitar devolução/renovação de empréstimo de outro usuário retorna `409` | Passou |
| Solicitar devolução/renovação de empréstimo retornado retorna `409` | Passou |

### 7. Renovação

| Cenário | Resultado |
| --- | --- |
| Solicitar renovação de empréstimo ativo e aprovar soma 14 dias | Passou |
| `renewal_count` passa para `1` | Passou |
| Segunda renovação retorna `409` | Passou |
| Renovação de empréstimo atrasado retorna `409` | Passou |
| Renovação de empréstimo retornado retorna `409` | Passou |
| Renovação não altera disponibilidade do livro | Passou |

### 8. Paginação, Filtros e Enums

| Cenário | Resultado |
| --- | --- |
| Listagens retornam `{items,total,skip,limit}` | Passou |
| `skip=0&limit=5`, `skip=5&limit=5` e `skip` além do total funcionam | Passou |
| Filtros combinados de empréstimo por `status`, `user_id` e `overdue` funcionam | Passou |
| Enum inválido em `status` e `type` retorna `422` | Passou |

### 9. Cache, Rate Limit e Estabilidade

| Cenário | Resultado |
| --- | --- |
| `/books/count/{isbn}` não retorna disponibilidade velha após empréstimo/devolução | Passou |
| Rate limit em login/bootstrap retorna `429` ao exceder limite | Passou |
| Rate limit em criação de livro/autor/usuário retorna `429` ao exceder limite | Passou |
| Rate limit em criação/devolução de empréstimo retorna `429` ao exceder limite | Passou |
| Rate limit em listagem de livros/autores retorna `429` ao exceder limite | Passou |
| Após janela de rate limit, requisições voltam a ser aceitas | Passou |
| Redis indisponível aparece como `unavailable` ou `disabled` no health check | Passou |
| Operações principais continuam sem `500` quando Redis é opcional | Passou |
| Duas requisições simultâneas tentando emprestar o mesmo livro geram apenas um sucesso | Passou |
| Concorrência tentando criar quarto empréstimo não ultrapassa limite de 3 ativos | Passou |

## Evidência Automatizada Complementar

Após os fixes, a suíte automatizada também foi executada contra o banco de teste Docker:

```text
56 passed, 1 warning
```

Além disso, foram adicionados cenários automatizados para cobrir as regressões encontradas no QA manual:

- paginação inválida;
- IDs inválidos em path/query;
- ISBN inválido e ISBN inexistente;
- ISBN existente sem disponibilidade;
- criação de solicitação de empréstimo por `reader` para livro existente.

## Conclusão

A bateria manual cobriu o fluxo principal e os pontos de estabilidade mais sensíveis da API. As falhas encontradas ficaram concentradas em validações de borda e semântica de ISBN inexistente. Após os fixes, os cenários foram reexecutados e passaram, sem pendências abertas registradas neste relatório.
