import { FormEvent, useState } from "react";

import { userApi } from "../api/resources";
import type { Loan } from "../api/types";
import { Pagination } from "../components/Pagination";
import { Panel } from "../components/Panel";
import { EmptyState, Notice, formatDate } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatLoanStatus } from "../utils/formatters";

export function UsersPage() {
  const [page, setPage] = useState(0);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loans, setLoans] = useState<Loan[]>([]);
  const [saving, setSaving] = useState(false);
  const [loadingLoans, setLoadingLoans] = useState(false);
  const [selectedUserName, setSelectedUserName] = useState<string | null>(null);
  const users = useAsync(() => userApi.list(page), [page], "load");

  async function createUser(event: FormEvent) {
    event.preventDefault();
    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setError("Informe o nome do usuário.");
      return;
    }

    if (!trimmedEmail) {
      setError("Informe o email do usuário.");
      return;
    }

    setError(null);
    setMessage(null);
    setSaving(true);
    try {
      await userApi.create({ name: trimmedName, email: trimmedEmail });
      setName("");
      setEmail("");
      setMessage("Usuário criado com sucesso.");
      users.reload();
    } catch (err) {
      setError(errorMessage(err, "createUser"));
    } finally {
      setSaving(false);
    }
  }

  async function loadLoans(userId: number, userName: string) {
    setError(null);
    setMessage(null);
    setSelectedUserName(userName);
    setLoadingLoans(true);
    try {
      const response = await userApi.loans(userId);
      setLoans(response.items);
    } catch (err) {
      setError(errorMessage(err, "loadUserLoans"));
    } finally {
      setLoadingLoans(false);
    }
  }

  return (
    <div className="page two-columns-grid users-layout">
      <div className="users-side-column">
        <Panel title="Cadastrar usuário">
          <form className="form-grid" onSubmit={createUser}>
            {message ? <Notice tone="success">{message}</Notice> : null}
            {error ? <Notice tone="error">{error}</Notice> : null}
            <label>
              Nome
              <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Nome completo" required />
            </label>
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="usuario@email.com" required />
            </label>
            <button className="primary" disabled={saving}>
              {saving ? "Criando..." : "Criar usuário"}
            </button>
          </form>
        </Panel>

        <Panel title={selectedUserName ? `Empréstimos de ${selectedUserName}` : "Empréstimos do usuário"}>
          {loadingLoans ? (
            <EmptyState title="Carregando empréstimos..." />
          ) : loans.length ? (
            <table>
              <thead>
                <tr>
                  <th>Livro</th>
                  <th>Status</th>
                  <th>Vencimento</th>
                </tr>
              </thead>
              <tbody>
                {loans.map((loan) => (
                  <tr key={loan.id}>
                    <td>{loan.book?.title ?? loan.book_id}</td>
                    <td>{formatLoanStatus(loan.status)}</td>
                    <td>{formatDate(loan.expected_return_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState
              title={selectedUserName ? "Nenhum empréstimo encontrado" : "Selecione um usuário"}
              detail={selectedUserName ? "Esse usuário ainda não possui empréstimos registrados." : "A lista de empréstimos aparece aqui."}
            />
          )}
        </Panel>
      </div>

      <Panel title="Usuários">
        {users.error ? <Notice tone="error">{users.error}</Notice> : null}
        {users.loading ? <EmptyState title="Carregando usuários..." detail="Buscando cadastros disponíveis." /> : null}
        {users.data?.items.length ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nome</th>
                  <th>Email</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {users.data.items.map((user) => (
                  <tr key={user.id}>
                    <td>{user.id}</td>
                    <td>{user.name}</td>
                    <td>{user.email}</td>
                    <td>
                      <button type="button" onClick={() => loadLoans(user.id, user.name)} disabled={loadingLoans}>
                        Empréstimos
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pagination page={page} total={users.data.total} onChange={setPage} />
          </>
        ) : (
          !users.loading && <EmptyState title="Nenhum usuário encontrado" detail="Quando houver leitores cadastrados, eles aparecerão aqui." />
        )}
      </Panel>

    </div>
  );
}
