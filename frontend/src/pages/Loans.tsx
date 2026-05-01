import { FormEvent, useState } from "react";

import { loanApi } from "../api/resources";
import { Panel } from "../components/Panel";
import { Badge, EmptyState, Notice, formatDate } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatCurrency } from "../utils/formatters";

export function LoansPage() {
  const [userId, setUserId] = useState("");
  const [bookId, setBookId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [returningLoanId, setReturningLoanId] = useState<number | null>(null);
  const active = useAsync(() => loanApi.active(), [], "load");
  const overdue = useAsync(() => loanApi.overdue(), [], "load");

  function parsePositiveId(value: string) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0 ? number : null;
  }

  async function createLoan(event: FormEvent) {
    event.preventDefault();
    const parsedUserId = parsePositiveId(userId);
    const parsedBookId = parsePositiveId(bookId);

    if (!parsedUserId) {
      setError("Informe um ID de usuário válido.");
      return;
    }

    if (!parsedBookId) {
      setError("Informe um ID de livro válido.");
      return;
    }

    setError(null);
    setMessage(null);
    setCreating(true);
    try {
      await loanApi.create(parsedUserId, parsedBookId);
      setMessage("Empréstimo criado com sucesso.");
      setUserId("");
      setBookId("");
      active.reload();
      overdue.reload();
    } catch (err) {
      setError(errorMessage(err, "createLoan"));
    } finally {
      setCreating(false);
    }
  }

  async function returnLoan(loanId: number) {
    setError(null);
    setMessage(null);
    setReturningLoanId(loanId);
    try {
      const loan = await loanApi.returnLoan(loanId);
      setMessage(`Devolução processada com sucesso. Multa: ${formatCurrency(loan.fine_value)}.`);
      active.reload();
      overdue.reload();
    } catch (err) {
      setError(errorMessage(err, "returnLoan"));
    } finally {
      setReturningLoanId(null);
    }
  }

  return (
    <div className="page">
      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Panel title="Novo empréstimo direto">
        <form className="inline-form" onSubmit={createLoan}>
          <label>
            Usuário
            <input value={userId} onChange={(event) => setUserId(event.target.value)} inputMode="numeric" placeholder="ID do usuário" required />
          </label>
          <label>
            Livro
            <input value={bookId} onChange={(event) => setBookId(event.target.value)} inputMode="numeric" placeholder="ID do livro" required />
          </label>
          <button className="primary" disabled={creating}>
            {creating ? "Emprestando..." : "Emprestar"}
          </button>
        </form>
      </Panel>

      <div className="two-columns-grid">
        <Panel title="Ativos">
          {active.error ? <Notice tone="error">{active.error}</Notice> : null}
          {active.loading ? (
            <EmptyState title="Carregando empréstimos..." />
          ) : active.data?.items.length ? (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Livro</th>
                  <th>Usuário</th>
                  <th>Vencimento</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {active.data.items.map((loan) => (
                  <tr key={loan.id}>
                    <td>{loan.id}</td>
                    <td>{loan.book?.title ?? loan.book_id}</td>
                    <td>{loan.user?.name ?? loan.user_id}</td>
                    <td>{formatDate(loan.expected_return_date)}</td>
                    <td>
                      <button onClick={() => returnLoan(loan.id)} disabled={returningLoanId === loan.id}>
                        {returningLoanId === loan.id ? "Devolvendo..." : "Devolver"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title="Sem empréstimos ativos" detail="Quando houver empréstimos em andamento, eles aparecerão aqui." />
          )}
        </Panel>

        <Panel title="Atrasados">
          {overdue.error ? <Notice tone="error">{overdue.error}</Notice> : null}
          {overdue.loading ? (
            <EmptyState title="Carregando atrasos..." />
          ) : overdue.data?.items.length ? (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Livro</th>
                  <th>Vencimento</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {overdue.data.items.map((loan) => (
                  <tr key={loan.id}>
                    <td>{loan.id}</td>
                    <td>{loan.book?.title ?? loan.book_id}</td>
                    <td>{formatDate(loan.expected_return_date)}</td>
                    <td>
                      <Badge tone="bad">Atrasado</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title="Sem atrasos" detail="Nenhum empréstimo está vencido no momento." />
          )}
        </Panel>
      </div>
    </div>
  );
}
