import { useState } from "react";

import { requestApi } from "../api/resources";
import { Panel } from "../components/Panel";
import { Badge, EmptyState, Notice, formatDate } from "../components/Status";
import { errorMessage, useAsync } from "../hooks";
import { formatRequestStatus, formatRequestType } from "../utils/formatters";

export function RequestsPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState<{ id: number; action: "approve" | "reject" } | null>(null);
  const requests = useAsync(() => requestApi.list(0), [], "load");

  async function approve(id: number) {
    setError(null);
    setMessage(null);
    setProcessing({ id, action: "approve" });
    try {
      await requestApi.approve(id);
      setMessage("Solicitação aprovada com sucesso.");
      requests.reload();
    } catch (err) {
      setError(errorMessage(err, "approveRequest"));
    } finally {
      setProcessing(null);
    }
  }

  async function reject(id: number) {
    const reason = window.prompt("Motivo da rejeição");
    if (!reason) return;
    setError(null);
    setMessage(null);
    setProcessing({ id, action: "reject" });
    try {
      await requestApi.reject(id, reason);
      setMessage("Solicitação rejeitada com sucesso.");
      requests.reload();
    } catch (err) {
      setError(errorMessage(err, "rejectRequest"));
    } finally {
      setProcessing(null);
    }
  }

  return (
    <div className="page">
      {message ? <Notice tone="success">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <Panel title="Solicitações">
        {requests.error ? <Notice tone="error">{requests.error}</Notice> : null}
        {requests.loading ? (
          <EmptyState title="Carregando solicitações..." />
        ) : requests.data?.items.length ? (
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Usuário</th>
                <th>Livro/Empréstimo</th>
                <th>Criada em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {requests.data.items.map((request) => (
                <tr key={request.id}>
                  <td>{request.id}</td>
                  <td>{formatRequestType(request.request_type)}</td>
                  <td>
                    <Badge tone={request.status === "pending" ? "warn" : request.status === "approved" ? "good" : "bad"}>
                      {formatRequestStatus(request.status)}
                    </Badge>
                  </td>
                  <td>{request.user_id}</td>
                  <td>{request.book_id ?? request.loan_id}</td>
                  <td>{formatDate(request.created_at)}</td>
                  <td>
                    {request.status === "pending" ? (
                      <div className="button-row">
                        <button onClick={() => approve(request.id)} disabled={processing?.id === request.id}>
                          {processing?.id === request.id && processing.action === "approve" ? "Aprovando..." : "Aprovar"}
                        </button>
                        <button onClick={() => reject(request.id)} disabled={processing?.id === request.id}>
                          {processing?.id === request.id && processing.action === "reject" ? "Rejeitando..." : "Rejeitar"}
                        </button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <EmptyState title="Nenhuma solicitação encontrada" detail="Novos pedidos de leitores aparecerão aqui." />
        )}
      </Panel>
    </div>
  );
}
