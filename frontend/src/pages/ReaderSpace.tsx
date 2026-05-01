import { FormEvent, useState } from "react";

import { loanApi, requestApi } from "../api/resources";
import { Panel } from "../components/Panel";
import { EmptyState, Notice, formatDate } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatLoanStatus } from "../utils/formatters";

export function ReaderSpace({ userId }: { userId: number | null }) {
  const [loanId, setLoanId] = useState("");
  const [action, setAction] = useState<"return" | "renewal">("return");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const loans = useAsync(() => (userId ? loanApi.list(0, { user_id: userId }) : Promise.resolve({ items: [], total: 0, skip: 0, limit: 10 })), [userId], "load");

  function parsePositiveId(value: string) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0 ? number : null;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const parsedLoanId = parsePositiveId(loanId);
    if (!parsedLoanId) {
      setError("Informe um ID de empréstimo válido.");
      return;
    }

    setError(null);
    setMessage(null);
    setSending(true);
    try {
      if (action === "return") {
        await requestApi.createReturn(parsedLoanId);
        setMessage("Solicitação de devolução enviada para análise.");
      } else {
        await requestApi.createRenewal(parsedLoanId);
        setMessage("Solicitação de renovação enviada para análise.");
      }
      setLoanId("");
    } catch (err) {
      setError(errorMessage(err, "requestAction"));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page two-columns-grid">
      <Panel title="Meus empréstimos">
        {loans.error ? <Notice tone="error">{loans.error}</Notice> : null}
        {loans.loading ? (
          <EmptyState title="Carregando seus empréstimos..." />
        ) : loans.data?.items.length ? (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Livro</th>
                <th>Status</th>
                <th>Vencimento</th>
              </tr>
            </thead>
            <tbody>
              {loans.data.items.map((loan) => (
                <tr key={loan.id}>
                  <td>{loan.id}</td>
                  <td>{loan.book?.title ?? loan.book_id}</td>
                  <td>{formatLoanStatus(loan.status)}</td>
                  <td>{formatDate(loan.expected_return_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="Nenhum empréstimo encontrado" detail="Quando você tiver empréstimos, eles aparecerão aqui." />
        )}
      </Panel>

      <Panel title="Solicitar ação">
        <form className="form-grid" onSubmit={submit}>
          {message ? <Notice tone="success">{message}</Notice> : null}
          {error ? <Notice tone="error">{error}</Notice> : null}
          <label>
            Empréstimo
            <input value={loanId} onChange={(event) => setLoanId(event.target.value)} inputMode="numeric" placeholder="ID do empréstimo" required />
          </label>
          <label>
            Ação
            <select value={action} onChange={(event) => setAction(event.target.value as "return" | "renewal")}>
              <option value="return">Devolução</option>
              <option value="renewal">Renovação</option>
            </select>
          </label>
          <button className="primary" disabled={sending}>
            {sending ? "Enviando..." : "Solicitar"}
          </button>
        </form>
      </Panel>
    </div>
  );
}
