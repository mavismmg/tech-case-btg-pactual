import { Link } from "react-router-dom";

import type { Account } from "../api/types";
import { metricsApi } from "../api/resources";
import { Panel, Stat } from "../components/Panel";
import { Badge, Notice } from "../components/Status";
import { useAsync } from "../hooks";
import { formatCurrency, formatOperation, formatRole } from "../utils/formatters";

export function Dashboard({ account }: { account: Account }) {
  const isStaff = account.role === "admin" || account.role === "librarian";
  const metrics = useAsync(() => (isStaff ? metricsApi.loans() : Promise.resolve(null)), [isStaff]);

  return (
    <div className="page">
      <div className="page-title">
        <span className="eyebrow">Visão geral</span>
        <h1>Operação da biblioteca</h1>
      </div>

      {isStaff ? (
        <Panel title="Resumo de empréstimos">
          {metrics.error ? <Notice tone="error">{metrics.error}</Notice> : null}
          <div className="stats-grid">
            <Stat label="Empréstimos registrados" value={metrics.data?.total_loans ?? 0} />
            <Stat label="Em andamento" value={metrics.data?.active_loans ?? 0} />
            <Stat label="Atrasados" value={metrics.data?.overdue_loans ?? 0} />
            <Stat label="Multas em aberto" value={formatCurrency(metrics.data?.total_fine_value)} />
          </div>
          <div className="event-list">
            {Object.entries(metrics.data?.events_by_operation ?? {}).map(([operation, total]) => (
              <div key={operation}>
                <Badge>{formatOperation(operation)}</Badge>
                <strong>{total}</strong>
              </div>
            ))}
          </div>
        </Panel>
      ) : (
        <Panel title="Meu acesso">
          <div className="stats-grid compact">
            <Stat label="Perfil" value={formatRole(account.role)} />
            <Stat label="Conta" value="Ativa" detail={account.email} />
          </div>
          <p className="muted">Use o catálogo para solicitar livros e acompanhe seus pedidos no Meu Espaço.</p>
        </Panel>
      )}

      <div className="quick-actions">
        <Link to="/catalog">Catálogo</Link>
        {isStaff ? <Link to="/loans">Empréstimos</Link> : <Link to="/reader">Meu Espaço</Link>}
        {isStaff ? <Link to="/notifications">Notificações</Link> : null}
      </div>
    </div>
  );
}
