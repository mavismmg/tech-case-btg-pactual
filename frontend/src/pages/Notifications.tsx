import { FormEvent, useState } from "react";

import { notificationApi } from "../api/resources";
import type { NotificationResponse } from "../api/types";
import { Panel } from "../components/Panel";
import { Badge, EmptyState, Notice } from "../components/Status";
import { errorMessage } from "../hooks";
import { formatDeliveryStatus, formatNotificationChannel } from "../utils/formatters";

export function NotificationsPage() {
  const [daysAhead, setDaysAhead] = useState(1);
  const [channel, setChannel] = useState("all");
  const [result, setResult] = useState<NotificationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (daysAhead < 0 || daysAhead > 30) {
      setError("Informe uma quantidade de dias entre 0 e 30.");
      return;
    }

    setError(null);
    setMessage(null);
    setSending(true);
    try {
      const response = await notificationApi.send(daysAhead, channel);
      setResult(response);
      setMessage("Notificações processadas com sucesso.");
    } catch (err) {
      setError(errorMessage(err, "notifications"));
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="page two-columns-grid">
      <Panel title="Enviar lembretes de devolução">
        <form className="form-grid" onSubmit={submit}>
          {message ? <Notice tone="success">{message}</Notice> : null}
          {error ? <Notice tone="error">{error}</Notice> : null}
          <label>
            Vencem em até
            <input
              type="number"
              min={0}
              max={30}
              value={daysAhead}
              onChange={(event) => setDaysAhead(Number(event.target.value))}
            />
            <span className="field-help">Quantidade de dias a considerar. Use 0 para vencimentos de hoje.</span>
          </label>
          <label>
            Canal de envio
            <select value={channel} onChange={(event) => setChannel(event.target.value)}>
              <option value="all">Todos os canais</option>
              <option value="email">Somente email</option>
              <option value="webhook">Canal interno</option>
            </select>
          </label>
          <button className="primary" disabled={sending}>
            {sending ? "Enviando..." : "Enviar notificações"}
          </button>
        </form>
      </Panel>

      <Panel title="Resultado do envio">
        {result ? (
          <>
            <div className="stats-grid compact">
              <div className="stat">
                <span>Empréstimos encontrados</span>
                <strong>{result.total_due_loans}</strong>
              </div>
              <div className="stat">
                <span>Mensagens enviadas</span>
                <strong>{result.sent_email_count + result.sent_webhook_count}</strong>
              </div>
              <div className="stat">
                <span>Já enviados</span>
                <strong>{result.skipped_count}</strong>
              </div>
              <div className="stat">
                <span>Falhas</span>
                <strong>{result.failed_count}</strong>
              </div>
            </div>
            <div className="delivery-list">
              {result.deliveries.map((delivery, index) => (
                <div key={`${delivery.loan_id}-${delivery.channel}-${index}`}>
                  <Badge tone={delivery.status === "sent" && !delivery.skipped ? "good" : delivery.skipped ? "warn" : "bad"}>
                    {formatNotificationChannel(delivery.channel)}
                  </Badge>
                  <span>Empréstimo #{delivery.loan_id}</span>
                  <Badge tone={delivery.status === "sent" && !delivery.skipped ? "good" : delivery.skipped ? "warn" : "bad"}>
                    {formatDeliveryStatus(delivery.status, delivery.skipped)}
                  </Badge>
                  {delivery.error_message ? <small>Falha no envio. Tente novamente em instantes.</small> : null}
                </div>
              ))}
            </div>
          </>
        ) : (
          <EmptyState title="Nenhum lembrete enviado ainda" detail="Envie lembretes para visualizar o resultado aqui." />
        )}
      </Panel>
    </div>
  );
}
